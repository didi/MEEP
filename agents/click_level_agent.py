import re
from typing import Tuple

from agents.agent import Agent
from utils.utils import load_variable


# Constants and useful functions
WAIT_FOR_USER = 'action:wait_for_user'

def flatten_variables(variables):
    result = []
    for v in variables:
        if type(v['value']) == list:
            result.extend(flatten_variables(v['value']))
        else:
            result.append(v)
    return result


class Template():
    def __init__(self, template: str):
        self.slot_descriptions = re.findall(r'\{([^\}]*)\}', template) # list of slot descriptions
        self.n_slots = len(self.slot_descriptions)
        self.template = re.sub(r'\{[^\}]*\}', '{}', template) # looks like "it is {} minutes away"

    def fill_slots(self, slot_values: list) -> dict:
        '''Returns a single message'''
        if self.n_slots != len(slot_values):
            raise ValueError('Incorrect number of slot values')

        filled_template = {
            'body': self.template.format(*[v['value'] for v in slot_values]),
            'template': self.template,
            'variables': [v['full_name'] for v in slot_values],
            'sender': 'agent'
        }
        return filled_template


class API():
    def __init__(self, api):
        self.name = api['name']
        self.params = api['params']
        self.param_names = [param['name'] for param in self.params]
        self.function = api['function']
        self.endpoint = api['endpoint']

        self.n_slots = len(self.params)

    def call_api(self, slot_values: list) -> Tuple[dict, list]:
        '''Return a 2-tuple: a debugging message, and a list of new variables (None if request is unsuccessful)'''
        if self.n_slots != len(slot_values):
            raise ValueError('Incorrect number of slot values')

        request_params = [
            {'param': name, 'variable_name': var['full_name'], 'value': var['value']}
            for name, var in zip(self.param_names, slot_values)
        ]

        # Format debug information
        formatted_params = ' | '.join('{} = {}'.format(name, var['value']) for name, var in zip(self.param_names, slot_values))
        variable_names = [v['full_name'] for v in slot_values]

        new_variables = None

        # Make API call
        try:
            response = self.function(request_params)
            error_message = load_variable(response['variables'], 'error') # returns None if no error
        except Exception as e:
            # Catch Python errors
            error_message = e
            raise

        # Error handling
        if error_message:
            debug_message = {
                'body': 'DEBUG: Made an unsuccessful API call to {} with arguments {}. Received the error: {}.'.format(self.endpoint, formatted_params, str(error_message)),
                'template': 'DEBUG',
                'variables': variable_names,
                'sender': 'agent'
            }
        elif not response:
            # Empty responses are considered unsuccessful. This may change in the future,
            # so it's better to explicitly throw an error or return an error message
            debug_message = {
                'body': 'DEBUG: Made an unsuccessful API call to {} with arguments {}. Got an empty response.'.format(self.endpoint, formatted_params),
                'template': 'DEBUG',
                'variables': variable_names,
                'sender': 'agent'
            }
        else:
            # API call was successful
            debug_message = {
                'body': 'DEBUG: Made a successful API call to {} with arguments {}.'.format(self.endpoint, formatted_params),
                'template': 'DEBUG',
                'variables': [v['full_name'] for v in slot_values],
                'sender': 'agent',
            }
            new_variables = flatten_variables(response['variables'])

        return debug_message, new_variables

class ClickLevelAgent(Agent):
    '''
    Base class for agents to support out-of-the-box click-level predictions

    See initialization.json for examples of how variables are stored
    '''

    def __init__(self, agent_shared_state, agent_model_path,
                 interfaces, domain, **kwargs):
        super().__init__(agent_shared_state, agent_model_path, interfaces, domain, **kwargs)

        self.interfaces = interfaces
        self.initial_variables = domain.initial_variables
        self.domain = domain

        # load templates and apis
        self.templates = [Template(t) for t in domain.agent_templates_list]
        self.api_functions = [API(a) for a in domain.api_functions.values()]
        self.end_dialog = API(domain.end_dialog)

    def initial_message(self):
        '''See base class'''
        raise NotImplementedError

    def on_message(self, message: str, events: dict) -> dict:
        '''See base class'''

        # prepare variables
        available_variables = flatten_variables(self.initial_variables['variables'] + [v for e in events if e['event_type'] == 'user_utterance' or e['event_type'] == 'api_call' for v in e['variables']])
        for v in available_variables:
            v['name'] = str(v['name'])

        result = []

        action = WAIT_FOR_USER
        while True:
            action = self.predict_action(message, events, available_variables)

            if action == WAIT_FOR_USER:
                break

            # Fill slots
            selected_variables = []
            slot_index = len(selected_variables)
            for i in range(action.n_slots):
                if isinstance(action, API):
                    selected_variable = self.fill_api(message, events, action, slot_index, available_variables, selected_variables)
                elif isinstance(action, Template):
                    selected_variable = self.fill_template(message, events, action, slot_index, available_variables, selected_variables)

                # remove selected_variable from available_variables and update selected_variables
                available_variables.remove(selected_variable)
                selected_variables.append(selected_variable)

            # reset available_variables
            available_variables.extend(selected_variables)

            # actually fill api and templates
            if isinstance(action, API):
                debug_message, new_variables = action.call_api(selected_variables)
                self.on_api_call(action, selected_variables, debug_message, new_variables)

                # api call succeeded
                if new_variables is not None:
                    available_variables.extend(new_variables)
                    if action == self.end_dialog:
                        self.on_end_dialog(result, available_variables)

                result.append(debug_message)
            elif isinstance(action, Template):
                agent_message = action.fill_slots(selected_variables)
                self.on_template_fill(action, selected_variables, agent_message)
                result.append(agent_message)

        return result

    def predict_action(self, message: str, events: list, available_variables: list):
        '''
        Choose the next action when nothing is selected. Selects a variable container (either a template or API call or wait for user)

        Should return an instance of Template or API
        '''
        raise NotImplementedError

    def fill_template(self, message: str, events: list, template: Template, slot_index: int, available_variables: list, selected_variables: list) -> dict:
        '''
        Choose the next click when a template is currently selected

        Should return an element from available_variables'''
        raise NotImplementedError

    def fill_api(self, message: str, events: list, api: API, slot_index: int, available_variables: list, selected_variables: list) -> dict:
        '''
        Choose the next click when an API is selected

        Should return an element from available_variables
        '''
        raise NotImplementedError

    # Some optional callbacks for more control
    def on_api_call(self, api, selected_variables, debug_message, new_variables):
        '''Called after an API is called. Can be used to check if the call was successful'''
        pass

    def on_template_fill(self, template, selected_variables, message):
        '''Called after a template is filled'''
        pass

    def on_end_dialog(self, messages: list, available_variables: list):
        '''Called after successfully calling end_dialog'''
        pass
