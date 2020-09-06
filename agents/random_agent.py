import random
import json
import re

from agents.agent import Agent
from apis.utils import add_full_names

end_words = {'goodbye', 'bye', 'stop', 'quit', 'exit', 'thanks', 'thank', 'ty'}

def flatten_variables(variables):
    # Flatten nested response
    result = []
    for var in variables:
        if isinstance(var['value'], list):
            result.extend(flatten_variables(var['value']))
        else:
            result.append(var)
    return result


class RandomAgent(Agent):
    '''Agent that randomly picks actions'''

    def __init__(self, _agent_shared_state, agent_model_path,
                 interfaces, *, domain=None, seed=None, **kwargs):
        super().__init__(_agent_shared_state, agent_model_path, interfaces)

        self.interfaces = interfaces
        self.domain = domain

        if seed is not None:
            random.seed(seed)

        # load templates. we don't care about grouping, so just load raw text
        # from file
        with open(self.domain.agent_templates) as f:
            self.templates = [line.strip() for line in f if not line.startswith(
                '---') and not line.isspace()]

        # get active api functions.
        # `api_functions` looks like the list of objects in apis.json except that each api also has the key 'function' containing the executable function
        # `end_dialog` is a single instance of that^. Assume that there is only one function that can end the dialog, otherwise take the first one
        with open(self.domain.apis) as f:
            # api_functions is similar to a list of dict with keys name,
            # endpoint, params, function
            self.api_functions = {api['endpoint']: api for api in json.load(f)}
        self.end_dialog = None

        for interface in self.interfaces:
            for attr in dir(interface):
                function = getattr(interface, attr)

                if hasattr(
                        function, 'endpoint') and function.endpoint in self.api_functions:
                    if hasattr(function, 'completes_dialog'):
                        self.end_dialog = self.api_functions[function.endpoint]
                        self.end_dialog['function'] = function
                        del self.api_functions[function.endpoint]
                    else:
                        self.api_functions[function.endpoint]['function'] = function
        # filter out functions not in apis.json
        self.api_functions = {
            k: v for k,
            v in self.api_functions.items() if 'function' in v}
        if self.end_dialog is None:
            raise Exception('Could not find an API to end dialog')

    def initial_message(self):
        return {
            'body': 'Hi, I\'m a random agent, but will try to complete the dialog. Type QUIT to force the dialog to end',
            'template': '',
            'variables': [],
            'sender': 'agent',
        }

    def _fill_template(self, template: str, available_variables: list) -> dict:
        '''Randomly fill slots in a template'''

        # select a template that has few enough slots that it can be filled
        # with the available variables

        # remove and ignore type hints for now
        template = re.sub(r'\{.*?\}', '{}', template)

        slots = template.count('{}')
        if slots <= len(available_variables):
            selected_variables = random.sample(available_variables, k=slots)
            filled_template = {
                'body': template.format(*[v['value'] for v in selected_variables]),
                'template': template,
                'variables': [v['full_name'] for v in selected_variables],
                'sender': 'agent',
            }
            return filled_template
        else:
            raise ValueError('Too few variables to fill the selected template')

    def _make_api_call(self, api: dict, available_variables: list) -> list:
        '''
        Randomly fill slots in an API call

        api - an element from self.api_functions OR self.end_dialog
        available_variables - a list of available variables. This list will be modified if an API call is successful

        return a list of (debugging) messages to send
        '''

        name = api['name']
        params = api['params']
        function = api['function']
        endpoint = api['endpoint']
        slots = len(params)

        result = []

        # Error checking
        if len(available_variables) < slots:
            raise ValueError('Too few variables to send the api request')

        # Try to make the request a few times. Since APIs are more structured than templates, this is more likely to fail
        # To avoid biasing towards APIs that are easier to fill (e.g. because
        # they have fewer parameters), we keep the same endpoint over multiple
        # tries

        MAX_API_RETRIES = 5
        for api_attempts in range(MAX_API_RETRIES):
            # TODO: for the rule-based agent, reweight variables to reward
            # matching names with param names
            selected_variables = random.sample(available_variables, k=slots)

            request_params = [
                {'param': param['name'],
                 'variable_name': var['full_name'],
                 'value': var['value']}
                for param, var in zip(params, selected_variables)
            ]

            # Common information to go in the debug message
            formatted_params = ' | '.join(
                '{} = {}'.format(
                    param['name'], var['value']) for param, var in zip(
                    params, selected_variables))
            variable_names = [v['full_name'] for v in selected_variables]

            try:
                response = function(request_params)
            except Exception as e:
                # Catch Python errors
                result.append({
                    'body': 'DEBUG: Made an unsuccessful ({}/{}) API call to {} with arguments {}. Received the error: {}.'.format(api_attempts, MAX_API_RETRIES, endpoint, formatted_params, str(e)),
                    'template': 'DEBUG',
                    'variables': variable_names,
                    'sender': 'agent'
                })
                break

            if not response:
                # Empty response
                result.append({
                    'body': 'DEBUG: Made an unsuccessful ({}/{}) API call to {} with arguments {}. Got an empty response.'.format(api_attempts, MAX_API_RETRIES, endpoint, formatted_params),
                    'template': 'DEBUG',
                    'variables': variable_names,
                    'sender': 'agent'
                })
            else:
                # API call was successful
                result.append({
                    'body': 'DEBUG: Made a successful API call to {} with arguments {}.'.format(endpoint, formatted_params),
                    'template': 'DEBUG',
                    'variables': [v['full_name'] for v in selected_variables],
                    'sender': 'agent',
                })
                available_variables.extend(flatten_variables(response['variables']))
                break

        return result

    def on_message(self, message, events):
        '''
        Flip a coin to decide whether to make an API call or template

        Randomly select an API call or template
        Randomly select parameters with no replacement

        If the API call fails, try again with new parameters. Try a few times, otherwise restart
        Repeat until successfully filling a template, then return and wait for user
        '''

        # Gather variables

        # Initial variables is passed as key-value pairs instead of objects with keys name, full_name and value
        # Convert to the latter format
        # TODO: See comment at app_factory.py:handle_message to pass the
        # original get_initial_variables object
        initial_variables = [
            {
                'name': k,
                'full_name': k,
                'value': v,
            } for k, v in self.initial_variables.items()
        ]

        variables = initial_variables + [v for e in events if e['event_type'] ==
                                         'user_utterance' or e['event_type'] == 'api_call' for v in e['variables']]
        variables = flatten_variables(variables)

        # test if the message contains a string like "goodbye", and end the
        # dialog if so

        if self.is_end_dialog(message):
            debug_messages = self._make_api_call(self.end_dialog, variables)
            return debug_messages + [{
                'body': 'Goodbye, ending dialog as requested by user',
                'template': 'Goodbye',
                'variables': [],
                'sender': 'agent',
            }]

        final_result = []

        # Always do some number of API calls, send exactly one message to the
        # user, then wait
        while random.random() < 0.5:
            debug_messages = self._make_api_call(random.choice(
                list(self.api_functions.values())), variables)
            final_result.extend(debug_messages)

        for template_attempts in range(3):
            try:
                messages = self._fill_template(
                    random.choice(self.templates), variables)
                final_result.append(messages)
                break
            except ValueError:
                # if the agent can't find a template with enough slots, you
                # will get here. This should be rare but depends on your schema
                final_result.append({
                    'body': 'DEBUG: No template can be filled with the available variables, waiting for user',
                    'template': 'DEBUG: not enough variables',
                    'variables': [],
                    'sender': 'agent',
                })

        return final_result

    def is_end_dialog(self, message):
        '''Simple rule-based check to see if a message ends the dialog'''

        return any(word in end_words for word in message.lower().split())
