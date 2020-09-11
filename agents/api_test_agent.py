from agents.agent import Agent


class APITestAgent(Agent):
    '''
    Agent that calls all the APIs to test logging
    '''

    def __init__(self, agent_shared_state, agent_model_path,
                 api_interfaces, domain, **kwargs):
        super().__init__(agent_shared_state, agent_model_path, api_interfaces, domain, **kwargs)
        self.num_turns = 0
        self.MAX_TURNS = 3  # number of turns that should be tested

        self.microworld_interface, = self.interfaces

    def on_message(self, message, events):
        '''Test logging of each interface'''

        if self.num_turns == 0:
            self.microworld_interface.find_place([
                {"param": "query",
                 "variable_name": "u1_0",
                 "value": "Gap"},
                {"param": "src latitude",
                 "variable_name": "source_latitude",
                 "value": 1},
                {"param": "src longitude",
                 "variable_name": "source_longitude",
                 "value": 1}
            ])
        elif self.num_turns == 1:
            self.microworld_interface.find_place([
                {"param": "query",
                 "variable_name": "u1_0",
                 "value": "Starbucks"},
                {"param": "src latitude",
                 "variable_name": "source_latitude",
                 "value": 1},
                {"param": "src longitude",
                 "variable_name": "source_longitude",
                 "value": 1}
            ])
        elif self.num_turns == 2:
            self.microworld_interface.start_driving([
                {'param': 'latitude',
                 'variable_name': 'v1_latitude',
                 'value': 2},
                {'param': 'longitude',
                 'variable_name': 'v1_longitude',
                 'value': 3}
            ])
            return

        self.num_turns += 1

        return {
            'body': 'Done turn {}'.format(self.num_turns),
            'template': '',
            'variables': []
        }
