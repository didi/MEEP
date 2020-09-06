import copy
import json
from functools import lru_cache

import numpy as np
import torch
from transformers import GPT2Model, GPT2Tokenizer
from sentence_transformers import SentenceTransformer

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rl.utils import flatten_variables

class DialogState():
    def __init__(self, max_steps, max_utterances, max_variables, embed_dim, max_command_length, max_conversation_length, passenger_max_actions, driver_max_actions):
        self.max_steps = max_steps
        self.max_utterances = max_utterances
        self.max_variables = max_variables
        self.embed_dim = embed_dim
        self.max_command_length = max_command_length
        self.max_conversation_length = max_conversation_length
        self.passenger_max_actions = passenger_max_actions
        self.driver_max_actions = driver_max_actions

        self.reset()

    def reset(self):
        self.driver_utterance_variables = []
        self.passenger_utterance_variables = []
        self.api_result_variables = []
        self.source_variables = []
        self.passenger_destination_variables = []

        self.dialog_history = []
        self.api_call_count = 0
        self.steps = 0
        self.driver_last_utterance = 0
        self.passenger_last_utterance = 0

        self.passenger_partial_command = []
        self.driver_partial_command = []

    def update_state(self, state):
        self.dialog_history = list(map(lambda m: {'sender': 0 if m['sender'] == 'user' else 1, 'utterance': m['body']}, state['dialog_history']))
        self.driver_utterance_variables = flatten_variables(state['agent_utterance_variables'])
        self.passenger_utterance_variables = flatten_variables(state['user_utterance_variables'])
        self.api_result_variables = flatten_variables(state['request_variables'][1:])
        self.source_variables = flatten_variables(state['initial_variables'])
        self.passenger_destination_variables = flatten_variables(state['destination_variables'])

    @property
    def passenger_variables(self):
        return self.driver_utterance_variables + self.source_variables + self.passenger_destination_variables

    @property
    def driver_variables(self):
        return self.passenger_utterance_variables + self.api_result_variables + self.source_variables

    def make_driver_observation(self, valid_actions=None):
        variables = copy.deepcopy(self.driver_variables)[-self.max_variables:]
        dialog_history = copy.deepcopy(self.dialog_history)[-self.max_utterances:]
        partial_command = list(map(lambda c: "{} is {}".format(c['full_name'], c['value']) if type(c) is dict else c, self.driver_partial_command))[-self.max_command_length:]

        # Embed variables
        for i, variable in enumerate(variables):
            variables[i] = DialogState.embed("{} is {}".format(variable['full_name'], variable['value']))
        for utterance in dialog_history:
            utterance['utterance'] = DialogState.embed(utterance['utterance'])
        for i, command in enumerate(partial_command):
            partial_command[i] = DialogState.embed(command)

        return {
            'steps': min(self.max_steps - 1, self.steps - self.passenger_last_utterance),
            'variables': variables,
            'dialog_history': dialog_history,
            'partial_command': partial_command,
            'action_mask': np.array([float(x) for x in valid_actions]) if valid_actions is not None \
                             else [1.0]*self.driver_max_actions
        }

    def make_passenger_observation(self, valid_actions=None):
        variables = copy.deepcopy(self.passenger_variables)[-self.max_variables:]
        dialog_history = copy.deepcopy(self.dialog_history)[-self.max_utterances:]
        partial_command = list(map(lambda c: c['value'] if type(c) is dict else c, self.passenger_partial_command))[-self.max_command_length:]

        # Embed variables
        for i, variable in enumerate(variables):
            variables[i] = DialogState.embed("{} is {}".format(variable['full_name'], variable['value']))
        for utterance in dialog_history:
            utterance['utterance'] = DialogState.embed(utterance['utterance'])
        for i, command in enumerate(partial_command):
            partial_command[i] = DialogState.embed(command)

        return {
            'steps': min(self.max_steps - 1, self.steps - self.passenger_last_utterance),
            'variables': variables,
            'dialog_history': dialog_history,
            'partial_command': partial_command,
            'action_mask': np.array([float(x) for x in valid_actions]) if valid_actions is not None \
                             else [1.0]*self.passenger_max_actions
        }

    def is_done(self):
        return len(self.dialog_history) >= self.max_conversation_length or self.api_call_count >= self.max_conversation_length or self.steps >= self.max_steps

    sentence_embed_model = SentenceTransformer('bert-base-nli-mean-tokens')
    @lru_cache(maxsize=128)
    def embed(s):
        # return s
        embedding = DialogState.sentence_embed_model.encode(s)[0]
        return embedding

    def __str__(self):
        return json.dumps({
            'variables': {
                'driver_utterance_variables': self.driver_utterance_variables,
                'passenger_utterance_variables': self.passenger_utterance_variables,
                'api_result_variables': self.api_result_variables,
                'source_variables': self.source_variables,
                'passenger_destination_variables': self.passenger_destination_variables
            },
            'partial_commands': {
                'passenger_partial_command': self.passenger_partial_command,
                'driver_partial_command': self.driver_partial_command
            },
            'dialog_history': self.dialog_history,
        }, sort_keys=True, indent=4)

    def __eq__(self, other_state):
        return str(self) == str(other_state)
