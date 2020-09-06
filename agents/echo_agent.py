from agents.agent import Agent


class EchoAgent(Agent):
    '''
    The simplest agent, just repeats the user's message back to them every time
    '''

    def on_message(self, message, events):
        return {
            'body': message,
            'template': '',
            'variables': []
        }
