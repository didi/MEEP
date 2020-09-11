from agents.agent import Agent
import time


class DelayAgent(Agent):
    '''
    A proof-of-concept that shows that an agent can hold off on sending a message
    '''

    def __init__(self, agent_shared_state,
                 agent_model_path, interfaces, domain, **kwargs):
        super().__init__(agent_shared_state, agent_model_path, interfaces, domain, **kwargs)
        delay = 5
        if agent_model_path:
            with open(agent_model_path) as f:
                for line in f:
                    if line.startswith("delay:"):
                        delay = float(line.split(":")[1].strip())
                        break

        self.delay = delay

    def initial_message(self):
        return {
            'body': 'Saying "wait" or "delay" will schedule a message for {} seconds from now. Wait can be interrupted'.format(self.delay),
            'template': '',
            'variables': [],
            'sender': 'agent'
        }

    def on_message(self, message, events):
        if message.lower() == 'wait':
            return {
                'body': 'This message was sent after {} seconds of not receiving another message'.format(self.delay),
                'template': '',
                'variables': [],
                'delay': self.delay,
                # message will be cancelled if another user utterance is
                # received in the next 3 seconds
                'cancellable': True,
            }
        elif message.lower() == 'delay':
            return {
                'body': 'This message was sent after {} seconds of waiting'.format(self.delay),
                'template': '',
                'variables': [],
                'delay': self.delay,
                # message will be cancelled if another user utterance is
                # received in the next 3 seconds
                'cancellable': False,
            }
        else:  # echo
            return {
                'body': message,
                'template': '',
                'variables': [],
            }
