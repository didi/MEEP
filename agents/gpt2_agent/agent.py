import os
import json
import sys
sys.path.append(os.path.join(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(__file__)))),
    "gui/backend/logger"))

from agents.agent import Agent
from agents.gpt2_agent.utils import get_action_beam, preprocess_context, detokenizer
from logger.logger import APICallEvent, AgentUtteranceEvent, WaitForUserEvent

import torch
from transformers import GPT2LMHeadModel, GPT2Tokenizer


class GPT2Agent(Agent):
    BEAM_SIZE = 5

    def __init__(self, agent_shared_state,
                 agent_model_path, interfaces, **kwargs):
        super().__init__(agent_shared_state, agent_model_path, interfaces)
        self.api_call_params = {
            'find_place': ('query', 'src latitude', 'src longitude'),
            'places_nearby': ('query', 'src latitude', 'src longitude'),
            'distance_matrix': ('src latitude', 'src longitude', 'dest latitude', 'dest longitude'),
            'start_driving': ('dest latitude', 'dest longitude'),
        }
        self.map_api_interface = self.interfaces[0]
        if not 'gpt2-model' in agent_shared_state:
            print("Loading model")
            agent_shared_state['gpt2-model'] = GPT2LMHeadModel.from_pretrained(
                agent_model_path)
            agent_shared_state['gpt2-tokenizer'] = GPT2Tokenizer.from_pretrained(
                agent_model_path)
            agent_shared_state['gpt2-device'] = torch.device(
                "cuda" if torch.cuda.is_available() else "cpu")
            agent_shared_state['gpt2-model'].to(
                agent_shared_state['gpt2-device'])
            print("Loaded model")
        self.model = agent_shared_state['gpt2-model']
        self.tokenizer = agent_shared_state['gpt2-tokenizer']
        self.device = agent_shared_state['gpt2-device']

        self.language = 'en'
        self.all_vars = {}

    def get_variables(self, variables):
        extracted_variables = []
        for v in variables:
            if isinstance(v['value'], list):
                extracted_variables += self.get_variables(v['value'])
            else:
                extracted_variables.append(
                    '{} = {}'.format(
                        v['full_name'], v['value']))
        return extracted_variables

    def make_context(self, events):
        context = []
        for v in self.initial_variables:
            context.append('source_{} = {}'.format(v, self.initial_variables[v]))
        for event in events:
            event = event.toJSON() if not isinstance(event, dict) else event
            if event['event_type'] == 'api_call':
                context.append(
                    ' '.join(('PREDICT: [ACTION] {}'.format(event['endpoint']), ' '.join(
                        ['[PARAM] {}'.format(p['value']) for p in event['params']])))
                )
                context += self.get_variables(event['variables'])
            elif event['event_type'] == 'user_utterance':
                context.append("User: {}".format(detokenizer.detokenize(
                    [v['value'] for v in event['variables']])))
            elif event['event_type'] == 'agent_utterance':
                # Strip off all debug messages in the agent utterance
                utterance_without_debug = event['utterance'][:event['utterance'].find(
                    '\nDEBUG')]
                context.append('PREDICT: [ACTION] {}'.format(
                    utterance_without_debug) + ' '.join(['[PARAM] {}'.format(p) for p in event['params']]))
        context.append("PREDICT:")
        context = preprocess_context(context)
        return '\n'.join(context)

    def format_params(self, action, params):
        return [
            {
                'param': self.api_call_params[action][i],
                'variable_name': "{}".format(self.all_vars.get(str(p), str(p))),
                'value': p
            }
            for i, p in enumerate(params[:len(self.api_call_params[action])])
        ]

    def api_call(self, api_call, params, alternate_events):
        if api_call == 'find_place':
            return self.map_api_interface.find_place(params, alternate_events)
        elif api_call == 'places_nearby':
            return self.map_api_interface.places_nearby(
                params, alternate_events)
        elif api_call == 'distance_matrix':
            return self.map_api_interface.distance_matrix(
                params, alternate_events)

    def candidate_action_to_alternate_event(self, action, params):
        if action == 'start_driving' or action in self.api_call_params:
            formatted_params = self.format_params(action, params)
            return APICallEvent(
                type(self.map_api_interface.provider).__name__,
                action, formatted_params,
                variables=[])  # Variables is empty because the candidate api is never executed
        elif action == 'wait_for_user':
            return WaitForUserEvent()
        else:
            while len(params) < action.count('{}'):
                params.append("[None]")
            utterance = action.format(*params)
            return AgentUtteranceEvent({
                'body': utterance,
                'template': action,
                'variables': params})

    def alternate_event_to_candidate_action(self, alternate_event):
        if alternate_event['event_type'] == 'api_call':
            return alternate_event['endpoint'], [x['value']
                                                 for x in alternate_event['params']]
        elif alternate_event['event_type'] == 'wait_for_user':
            return "wait_for_user", None
        elif alternate_event['event_type'] == 'agent_utterance':
            return alternate_event["template"], alternate_event["params"]
        else:
            assert False, "invalid event type %s" % alternate_event['event_type']

    def on_message(self, _unused_message, events):
        return self.on_message_with_alternate_events(events)

    def on_message_with_alternate_events(
            self, events, initial_alternate_events=None):
        response = []

        action = ''
        params = []
        start_driving = False
        first_loop = True
        while action != 'wait_for_user':
            context = self.make_context(events)
            if first_loop and initial_alternate_events:
                first_loop = False
                alternate_events = initial_alternate_events
                action, params = self.alternate_event_to_candidate_action(
                    alternate_events['events'][alternate_events['active_index']])
            else:
                candidate_actions = get_action_beam(
                    self.model, self.tokenizer, context,
                    self.device, beam_width=GPT2Agent.BEAM_SIZE)
                action, params = candidate_actions[0]
                alternate_events = {"active_index": 0,
                                    "failed_indexes": []}
                alternate_events["events"] = [self.candidate_action_to_alternate_event(action, params).toJSON()
                                              for action, params in candidate_actions]
                # Always add a wait_for_user alternate event
                if not any(isinstance(e, WaitForUserEvent)
                           for e in alternate_events["events"]):
                    alternate_events["events"].append(
                        WaitForUserEvent().toJSON())
            if action == 'start_driving':
                formatted_params = self.format_params(action, params)
                self.map_api_interface.start_driving(
                    formatted_params, alternate_events)
                start_driving = True
                response = []
                break
            if action in self.api_call_params:
                formatted_params = self.format_params(action, params)
                new_vars = self.api_call(
                    action, formatted_params, alternate_events)
                api_call_event = APICallEvent(
                    type(self.map_api_interface.provider).__name__,
                    action, formatted_params, new_vars['variables'])
                events += (api_call_event.toJSON(),)
                for var in new_vars['variables']:
                    if 'full_name' in var:
                        self.all_vars[str(var['value'])] = var['full_name']
                    else:
                        for inner_var in var['value']:
                            if 'full_name' in inner_var:
                                self.all_vars[str(
                                    inner_var['value'])] = inner_var['full_name']
            elif action == 'wait_for_user':
                break
            else:
                while len(params) < action.count('{}'):
                    params.append("[None]")
                utterance = action.format(*params)
                agent_utterance_event = AgentUtteranceEvent({
                    'body': utterance, 'template': action, 'variables': params})
                events += (agent_utterance_event.toJSON(),)
                response.append({
                    'body': utterance,
                    'template': action,
                    'variables': params,
                    'alternate_events': alternate_events
                })
        return response
