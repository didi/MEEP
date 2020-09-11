from agents.agent import Agent
from utils.utils import load_variable


class CompareNumbersAgent(Agent):
    """Simple rule-based agent to compare 2 numbers"""

    def __init__(self, _agent_shared_state, _agent_model_path,
                 interfaces: list, domain, **kwargs):
        # This agent is stateless, so we don't need a shared state
        # It doesn't need to load a model file, so we don't need model_path
        super().__init__(_agent_shared_state, None, interfaces, domain, **kwargs)

        [self.compare_interface, ] = self.interfaces

    def initial_message(self):
        greeting = "Hello! Try giving me two float/integer numbers to compare! Type STOP to quit",

        return {
            'body': greeting,
            'template': '',
            'variables': [],
            'sender': 'agent',
        }

    def on_message(self, message, events):
        if message.lower().strip() == 'stop':
            self.compare_interface.end_dialog([])
            return {}

        # Extract numeric tokens from the last user utterance
        variables = []
        if not events[-1]['event_type'] == 'user_utterance':
            # This should never happen because on_message is only called after
            # user utterances
            raise ValueError('Did not get a user utterance')

        # var is a dict with keys 'full_name', 'name', 'value'. See json logs
        # for examples
        for var in events[-1]['variables']:

            # Create a list of tokens that can be cast to numeric values
            try:
                float(var['value'])
                variables.append(var)
            except ValueError:
                continue

        # Validate user utterance
        if len(variables) == 2:
            num1, num2 = variables

            result = self.compare_interface.compare([
                {'param': 'number1',
                 'variable_name': num1['full_name'],
                 'value': num1['value']},
                {'param': 'number2',
                 'variable_name': num2['full_name'],
                 'value': num2['value']},
            ])

            comparator = load_variable(result['variables'], 'comparison')
            message = "{} is {} {}".format(
                num1['value'], comparator, num2['value'])
            template = "{} is {} {}"
        else:
            template = message = "Sorry I didn't understand, please give me exactly two numbers to compare in integer or float formats."

        return {
            'body': message,
            'template': template,
            'variables': []
        }
