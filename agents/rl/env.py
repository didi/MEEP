import json
import logging
logging.getLogger('env').setLevel(logging.INFO)
logger = logging.getLogger('env')

import re
from threading import Thread

from gym.spaces import Tuple, Dict, Box, Discrete, MultiDiscrete
from ray.rllib.env import MultiAgentEnv
from ray.rllib.utils.spaces.repeated import Repeated
import requests
import socketio

import os, sys
sys.path.append(os.path.dirname(__file__))
from state import DialogState
from api import API, Parameter
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from rl.utils import flatten_variables

class MicroworldEnv(MultiAgentEnv):
    # Constants
    agents = ('passenger', 'driver')

    rewards = {
        'driver_good_api_call': 0.1,
        'driver_bad_api_call': 0.0,
        'driver_invalid_api': -0.1,
        'driver_invalid_template': -0.1,
        'driver_invalid_variable': -0.1,
        'driver_correct_destination': 1.0,
        'driver_incorrect_destination': -1.0,
        'driver_max_steps': -2.0,
        'driver_no_action': -0.1,
        'passenger_invalid_template': -0.1,
        'passenger_invalid_variable': -0.1,
        'passenger_correct_destination': 1.0,
        'passenger_incorrect_destination': -1.0,
        'passenger_max_steps': -2.0,
        'passenger_no_action': -0.1,
    }

    apis = [
        API("find_place", params=(
            Parameter('query', True),
            Parameter('src latitude', False),
            Parameter('src longitude', False),
        )),
        API("places_nearby", params=(
            Parameter('query', True),
            Parameter('src latitude', False),
            Parameter('src longitude', False),
        )),
        # API("distance_matrix", params=(
        #     Parameter('src latitude', False),
        #     Parameter('src longitude', False),
        #     Parameter('dest latitude', False),
        #     Parameter('dest longitude', False),
        # )),
        API("start_driving", params=(
            Parameter('dest latitude', False),
            Parameter('dest longitude', False),
        )),
    ]
    driver_templates = ["I found {}"]
    passenger_templates = ["I would like to go to {}"]

    @staticmethod
    def make_observation_space(embed_dim, max_steps, max_variables, max_utterances, max_command_length, max_actions):
        # Variables: (embed_dim * max_variables * 2)
        # Dialog history: (embed_dim) * max_utterances
        # Partial command: (embed_dim * max_command_length)
        space = {}
        if max_steps:
            space['steps'] = Discrete(max_steps)
        return Dict(
            **space,  
            **{
                'variables': Repeated(
                    Box(-10, 10, shape=(embed_dim,)), max_len=max_variables
                ),
                'dialog_history': Repeated(
                    Dict({
                        'sender': Discrete(3),
                        'utterance': Box(-10, 10, shape=(embed_dim,))
                    }), max_len=max_utterances
                ),
                'partial_command': Repeated(
                    Box(-3, 3, shape=(embed_dim,)), max_len=max_command_length
                ),
                # 'avail_actions': Box(-10, 10, shape=(max_actions, embed_dim)),
                'action_mask': MultiDiscrete([2 for _ in range(max_actions)]),
             })

    @staticmethod
    def initialize_spaces(config=None):
        if config is None: config = {}
        max_steps = config.get('max_steps', 100)
        max_variables = config.get('max_variables', 50)
        max_utterances = config.get('max_utterances', 10)
        max_command_length = config.get('max_command_length', 5)
        max_conversation_length = config.get('max_conversation_length', 10)
        embed_dim = config.get('sentence_embed_dim', 768)

        # Action spaces
        # TODO: Load templates from API call for passengers and drivers
        passenger_max_actions = 1 + len(MicroworldEnv.passenger_templates) + max_variables
        passenger_action_space = Discrete(passenger_max_actions)

        driver_max_actions = 1 + len(MicroworldEnv.apis) + len(MicroworldEnv.driver_templates) + max_variables
        driver_action_space = Discrete(driver_max_actions)

        # Observation spaces
        passenger_observation_space = MicroworldEnv.make_observation_space(embed_dim, max_steps, max_variables, max_utterances, max_command_length, passenger_max_actions)
        driver_observation_space = MicroworldEnv.make_observation_space(embed_dim, max_steps, max_variables, max_utterances, max_command_length, driver_max_actions)

        return passenger_observation_space, driver_observation_space, passenger_action_space, driver_action_space

    def __init__(self, config):
        self.room_id = str(config.worker_index - 1)
        self.initialize_networking(config.get('backend_url', 'localhost'), config.get('backend_port', 5000))
        self.max_steps = config.get('max_steps', 100)
        self.max_variables = config.get('max_variables', 50)
        self.max_utterances = config.get('max_utterances', 10)
        self.max_command_length = config.get('max_command_length', 5)
        self.max_conversation_length = config.get('max_conversation_length', 10)
        self.embed_dim = config.get('sentence_embed_dim', 768)

        self.passenger_max_actions = 1 + len(MicroworldEnv.passenger_templates) + self.max_variables
        self.driver_max_actions = 1 + len(MicroworldEnv.apis) + len(MicroworldEnv.driver_templates) + self.max_variables

    def get_global_state(self):
        response = requests.get('{}/{}'.format(self.request_prefix, 'state'))
        state = response.json()
        return state

    def initialize_networking(self, backend_url='localhost', backend_port=5000):
        # Initialize socket, for messages
        self.socket = socketio.Client()

        @self.socket.event
        def connect():
            self.socket.emit('join', {
                "roomId": self.room_id,
                "sender": 'agent'
            });
            logger.info('Connected to room {}'.format(self.room_id))

        @self.socket.on('/end_dialog_confirm')
        def end_dialog(data):
            logger.info("[{}] Received end dialog message: {}".format(self.room_id, data))
            self.dialog_completed = True
            if data['correct']:
                self.rewards = {'driver': MicroworldEnv.rewards['driver_correct_destination'], 'passenger': MicroworldEnv.rewards['passenger_correct_destination']}
            else:
                self.rewards = {'driver': MicroworldEnv.rewards['driver_incorrect_destination'], 'passenger': MicroworldEnv.rewards['passenger_incorrect_destination']}
            self.dones = {'__all__': True}

        try:
            self.socket.connect("http://{}:{}".format(backend_url, backend_port))
        except socketio.exceptions.ConnectionError:
            print("Could not connect to backend at 'http://{}:{}'".format(backend_url, backend_port))
            exit()
        receive_events_thread = Thread(target=self.start_listening)
        receive_events_thread.daemon = True
        receive_events_thread.start()

        # Initialize for HTTP requests
        self.request_prefix = "http://{}:{}/{}".format(backend_url, backend_port, self.room_id)

    def start_listening(self):
        self.socket.wait()

    def driver_valid_actions(self):
        '''
        Return list of valid actions for driver
        '''
        null_action_mask = [1]
        api_and_template_mask = [len(self.state.driver_partial_command) == 0 for _ in MicroworldEnv.apis + MicroworldEnv.driver_templates]
        variable_mask = []
        for i in range(self.max_variables):
            if i >= len(self.state.driver_variables) or \
                len(self.state.driver_partial_command) == 0:
                    variable_mask.append(0)
            else:
                variable = self.state.driver_variables[i]
                if self.state.driver_partial_command[0] in ('find_place', 'places_nearby'):
                    if len(self.state.driver_partial_command) == 1:
                        # Query parameter, must click a user utterance
                        variable_mask.append(variable.get('full_name', '').startswith('u'))
                    elif len(self.state.driver_partial_command) == 2:
                        # Latitude
                        variable_mask.append('latitude' in variable.get('full_name', ''))
                    elif len(self.state.driver_partial_command) == 3:
                        # Longitude
                        variable_mask.append('longitude' in variable.get('full_name', ''))
                elif self.state.driver_partial_command[0] == 'start_driving':
                    if len(self.state.driver_partial_command) == 1:
                        # Latitude
                        variable_mask.append('latitude' in variable.get('full_name', ''))
                    elif len(self.state.driver_partial_command) == 2:
                        # Longitude
                        variable_mask.append('longitude' in variable.get('full_name', ''))
                else:
                    variable_mask.append(1)
        return null_action_mask + api_and_template_mask + variable_mask

    def passenger_valid_actions(self):
        '''
        Return list of valid actions for passenger
        '''
        return [1] + \
            [len(self.state.passenger_partial_command) == 0 for _ in MicroworldEnv.passenger_templates] + \
            [len(self.state.passenger_partial_command) > 0 and i < len(self.state.passenger_variables) for i in range(self.max_variables)]

    def reset(self):
        '''
        Called before each episode, returns the first observation
        '''
        logger.info("[{}] Resetting environment".format(self.room_id))
        self.dialog_completed = False
        self.socket.emit('/restart_dialog', {
            'roomId': self.room_id,
        })
        self.state = DialogState(self.max_steps, self.max_utterances, self.max_variables, self.embed_dim, self.max_command_length, self.max_conversation_length, self.passenger_max_actions, self.passenger_max_actions)
        self.state.update_state(self.get_global_state())
        self.obs = {
            'driver': self.state.make_driver_observation(self.driver_valid_actions()),
            'passenger': self.state.make_passenger_observation(self.passenger_valid_actions())
        }
        self.rewards = {'driver': 0, 'passenger': 0}
        self.dones = {'__all__': False}
        self.infos = {}
        return self.obs

    def _send_message(self, sender, template, params):
        body = template.format(*[p['value'] for p in params])
        self.socket.emit('/message', {
            'roomId': self.room_id,
            'sender': ('user', 'agent')[sender],
            'body': body,
            'inputType': 'text',
            'template': template,
            'variables': [p['full_name'] for p in params]
        })

    def _driver_step(self, action):
        '''
        Returns the driver's reward from the action
        '''
        reward = 0
        if action == 0:
            # 0 => No action
            logger.info("[{}] Driver clicked no action".format(self.room_id))
            return MicroworldEnv.rewards['driver_no_action']
        elif 1 <= action < 1 + len(MicroworldEnv.apis):
            # API clicked
            api_index = action - 1
            api = MicroworldEnv.apis[api_index]
            if not self.state.driver_partial_command:
                self.state.driver_partial_command.append(api.name)
                logger.info("[{}] Driver clicked API call: {}".format(self.room_id, api.name))
            else:
                logger.info("[{}] Driver tried invalid API click: {}".format(self.room_id, api.name))
                reward = MicroworldEnv.rewards['driver_invalid_api']
                if reward:
                    logger.info("[{}] --- Driver got a reward: {}".format(self.room_id, reward))
                return reward
        elif 1 + len(self.apis) <= action < 1 + len(self.apis) + len(self.driver_templates):
            # Template clicked
            template_index = action - len(MicroworldEnv.apis) - 1
            template = MicroworldEnv.driver_templates[template_index]
            if not self.state.driver_partial_command:
                logger.info("[{}] Driver clicked template: {}".format(self.room_id, template))
                self.state.driver_partial_command.append(template)
            else:
                logger.info("[{}] Driver tried invalid template click: {}".format(self.room_id, template))
                reward = MicroworldEnv.rewards['driver_invalid_template']
                if reward:
                    logger.info("[{}] --- Driver got a reward: {}".format(self.room_id, reward))
                return reward
        else:
            # Variable clicked
            # TODO: Combine utterance variables, as is done in the UI
            if self.state.driver_partial_command:
                variable_index = action - len(MicroworldEnv.apis) - len(MicroworldEnv.driver_templates) - 1
                if 0 <= variable_index < len(self.state.driver_variables):
                    variable = self.state.driver_variables[variable_index]
                    logger.info("[{}] Driver clicked variable: {}".format(self.room_id, variable))
                    self.state.driver_partial_command.append(variable)
                else:
                    logger.info("[{}] Driver tried invalid variable click: {}".format(self.room_id, variable_index))
                    reward = MicroworldEnv.rewards['driver_invalid_variable']
                    if reward:
                        logger.info("[{}] --- Driver got a reward: {}".format(self.room_id, reward))
                    return reward
            else:
                logger.info("[{}] Driver tried invalid variable click (no action selected)".format(self.room_id))
                reward = MicroworldEnv.rewards['driver_invalid_variable']
                if reward:
                    logger.info("[{}] --- Driver got a reward: {}".format(self.room_id, reward))
                return reward

        if self._driver_command_complete(self.state.driver_partial_command):
            logger.info("[{}] --- Driver completed an action: {}".format(self.room_id, self.state.driver_partial_command))
            reward = self._apply_driver_command(self.state.driver_partial_command)
            if reward:
                logger.info("[{}] --- Driver got a reward: {}".format(self.room_id, reward))
        return reward

    def _driver_command_complete(self, partial_command):
        if len(partial_command) == 0: return False
        action, params = partial_command[0], partial_command[1:]
        for api in MicroworldEnv.apis:
            if api.name == action:
                return len(api.params) == len(params)
        for template in MicroworldEnv.driver_templates:
            if template == action:
                return len(re.findall(r'{.*?}', template)) == len(params)

    def _format_params(self, api, params):
        return [{
            'param': api.params[i].name,
            'variable_name': p['full_name'],
            'value': p['value']
        } for i, p in enumerate(params)]

    def _apply_driver_command(self, command):
        reward = 0
        action, params = command[0], command[1:]
        for api in MicroworldEnv.apis:
            if api.name == action:
                api_params = self._format_params(api, params)
                self.state.driver_partial_command = []
                self.state.api_call_count += 1
                response = requests.post('{}/maps/{}'.format(self.request_prefix, api.name), data=json.dumps(api_params),
                    headers={'Content-Type': 'application/json'}).json()
                if api.name == 'start_driving': break
                variables = flatten_variables(response)
                if any('error' in v.get('full_name', 'test') for v in variables) or len(variables) == 0:
                    logger.info("[{}] --- Driver API call was an error or empty".format(self.room_id))
                    reward = MicroworldEnv.rewards['driver_bad_api_call']
                else:
                    logger.info("[{}] --- Driver API call got results!".format(self.room_id))
                    reward = MicroworldEnv.rewards['driver_good_api_call']
                if reward:
                    logger.info("[{}] --- Driver got a reward: {}".format(self.room_id, reward))
        for template in self.driver_templates:
            if template == action:
                self._send_message(1, template, params)
                self.state.driver_partial_command = []
                self.state.driver_last_utterance = self.state.steps
        self.dones = {'__all__': self.state.is_done()}
        return reward

    def _passenger_step(self, action):
        # TODO: Add clear command action
        if action == 0:
            # 0 == No action
            logger.info("[{}] Passenger made no action".format(self.room_id))
            return MicroworldEnv.rewards['passenger_no_action']
        elif 1 <= action < len(MicroworldEnv.passenger_templates) + 1:
            # Template clicked
            template_index = action - 1
            template = MicroworldEnv.passenger_templates[template_index]
            if not self.state.passenger_partial_command:
                logger.info("[{}] Passenger clicked template: {}".format(self.room_id, template))
                self.state.passenger_partial_command.append(template)
            else:
                logger.info("[{}] Passenger tried invalid template click: {}".format(self.room_id, template))
                reward = MicroworldEnv.rewards['passenger_invalid_template']
                if reward:
                    logger.info("[{}] --- Passenger got a reward: {}".format(self.room_id, reward))
                return reward
        else:
            # Variable clicked
            if self.state.passenger_partial_command:
                variable_index = action - len(MicroworldEnv.passenger_templates) - 1
                if 0 <= variable_index < len(self.state.passenger_variables):
                    variable = self.state.passenger_variables[variable_index]
                    logger.info("[{}] Passenger clicked variable: {}".format(self.room_id, variable))
                    self.state.passenger_partial_command.append(variable)
                else:
                    logger.info("[{}] Passenger tried invalid variable click: {}".format(self.room_id, variable_index))
                    reward = MicroworldEnv.rewards['passenger_invalid_variable']
                    if reward:
                        logger.info("[{}] --- Passenger got a reward: {}".format(self.room_id, reward))
                    return reward
            else:
                logger.info("[{}] Passenger tried invalid variable click (no action selected)".format(self.room_id))
                reward =  MicroworldEnv.rewards['passenger_invalid_variable']
                if reward:
                    logger.info("[{}] --- Passenger got a reward: {}".format(self.room_id, reward))
                return reward
        if self._passenger_command_complete(self.state.passenger_partial_command):
            logger.info("[{}] --- Passenger completed an action: {}".format(self.room_id, self.state.passenger_partial_command))
            self._apply_passenger_command(self.state.passenger_partial_command)
        return 0

    def _passenger_command_complete(self, partial_command):
        if len(partial_command) == 0: return False
        action, params = partial_command[0], partial_command[1:]
        for template in MicroworldEnv.passenger_templates:
            if template == action:
                return len(re.findall(r'{.*?}', template)) == len(params)

    def _apply_passenger_command(self, command):
        action, params = command[0], command[1:]
        for template in MicroworldEnv.passenger_templates:
            if template == action:
                self._send_message(0, template, params)
                self.state.passenger_partial_command = []
                self.state.passenger_last_utterance = self.state.steps

    def step(self, action_dict):
        '''
        Given an action_dict, compute the next observation, rewards, and dones
        '''

        # (state, action) => state
        if 'driver' in action_dict:
            driver_reward = self._driver_step(action_dict['driver'])
        if 'passenger' in action_dict:
            passenger_reward = self._passenger_step(action_dict['passenger'])

        # Update obs from state
        self.state.update_state(self.get_global_state())
        self.state.steps += 1
        self.obs = {
            'driver': self.state.make_driver_observation(self.driver_valid_actions()),
            'passenger': self.state.make_passenger_observation(self.passenger_valid_actions())
        }
        if not self.dialog_completed:
            self.dones = {'__all__': self.state.is_done()}
            if self.dones['__all__']:
                driver_reward += MicroworldEnv.rewards['driver_max_steps']
                passenger_reward += MicroworldEnv.rewards['passenger_max_steps']
            self.rewards = {'driver': driver_reward, 'passenger': passenger_reward}
        self.infos = {}
        return self.obs, self.rewards, self.dones, self.infos
