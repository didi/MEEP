from agents.agent import Agent


class HumanAgent(Agent):
    def __init__(self, *args, **kwargs):
        super(HumanAgent, self).__init__(*args, **kwargs)
        self.name = '007'
