import logging
logging.getLogger('env').setLevel(logging.INFO)
logger = logging.getLogger('env')

from gym.spaces import Tuple, Dict, Box, Discrete, MultiDiscrete
from ray.rllib.env import MultiAgentEnv
from ray.rllib.utils.spaces.repeated import Repeated
import random
random.seed(1)

from state import DialogStateNano

perfect_dialogs = [("starbucks", "wait for passenger, say starbucks, wait for passenger, wait for driver, drive starbucks"),
                   ("starbucks", "wait for passenger, say starbucks, wait for passenger, mental peets, say peets, drive peets"),
                   ("peets", "wait for passenger, say peets, wait for passenger, wait for driver, drive peets"),
                   ("peets", "wait for passenger, say peets, wait for passenger, mental starbucks, say starbucks, drive starbucks")]


class NanoworldEnv(MultiAgentEnv):
    # Constants
    agents = ('passenger', 'driver')

    max_num_actions = 8
    destination = ["", "starbucks", "peets"]

    # Action spaces
    passenger_actions = [
        "wait for driver",
        "say starbucks",
        "say peets",
        "mental starbucks",
        "mental peets"]
    # passenger_actions = ["wait for driver", "say starbucks", "say peets"]
    passenger_action_space = Discrete(len(passenger_actions))

    driver_actions = ["wait for passenger", "drive starbucks", "drive peets"]
    driver_action_space = Discrete(len(driver_actions))

    # observation spaces
    # wait, say starbucks, say peets -- can be repeated at most 4 times +
    # mental state (none, starbucks, peets)
    passenger_observation_space = Dict({'dialog_history': Repeated(
        Discrete(3), max_len=max_num_actions), 'destination': Discrete(3)})
    # wait, say starbucks, say peets -- can be repeated at most 4 times
    driver_observation_space = Dict(
        {'dialog_history': Repeated(Discrete(3), max_len=max_num_actions)})

    def __init__(self, config):
        destination_id = random.randint(1, 2)
        self.state = DialogStateNano(
            NanoworldEnv.max_num_actions,
            desired_destination=NanoworldEnv.destination[destination_id])
        self.num_epidodes = 0
        # self.is_supervised = config['is_supervised']

    def reset(self):
        '''
        Called before each episode, returns the first observation
        '''
        if self.num_epidodes % 1000 == 0:
            logger.warning("completed {} episodes.".format(self.num_epidodes))

        if self.num_epidodes >= 10000:
            logger.warning('episode ' + str(self.num_epidodes))
            logger.warning('------------')
            _, _, history, _ = self.state.get_global_state()
            for h in history:
                logger.warning(h)
            logger.warning('-------------')
        self.num_epidodes += 1

        destination_id = random.randint(1, 2)
        if self.num_epidodes >= 10000:
            logger.warning(
                'set destination: ' +
                NanoworldEnv.destination[destination_id])
        self.state = DialogStateNano(
            NanoworldEnv.max_num_actions,
            desired_destination=NanoworldEnv.destination[destination_id])
        self.obs = {
            'driver': self.state.make_driver_observation(),
            'passenger': self.state.make_passenger_observation()
        }
        return self.obs

    def driver_step(self, action):
        self.state.update_state(NanoworldEnv.driver_actions[action])
        obs = self.state.make_driver_observation()
        return obs

    def passenger_step(self, action):
        self.state.update_state(NanoworldEnv.passenger_actions[action])
        obs = self.state.make_passenger_observation()
        return obs

    def compute_passenger_reward(self):
        # if self.is_supervised:
        #     return self.compute_episode_reward_supervised()
        # else:
        return self.compute_episode_reward()

    def compute_driver_reward(self):
        # return self.compute_episode_reward()

        driver_reward = 0
        desired_destination, verbal_history, all_actions, driven_destination = self.state.get_global_state()
        if self.state.dialog_complete:  # to compute at the very end
            if driven_destination:
                if len(verbal_history) == 0:  # driver drives before user says anything
                    return -1
                else:
                    last_uttered_destination = verbal_history[-1].split(" ")[1]
                    if driven_destination == last_uttered_destination:
                        return 1
                    else:
                        return -1
            else:  # timeout
                return -10
        else:
            return 0

    def compute_episode_reward(self):
        desired_destination, verbal_history, all_actions, driven_destination = self.state.get_global_state()
        if self.state.dialog_complete:  # to compute at the very end
            if driven_destination:
                if desired_destination == driven_destination:
                    return 1
                else:
                    return -1
            else:  # timeout
                return -10
        else:
            return 0

    def step(self, action_dict):
        '''
        Given an action_dict, compute the next observation, rewards, and dones
        '''

        if 'driver' in action_dict:
            driver_obs = self.driver_step(action_dict['driver'])
            if self.state.is_done():
                driver_reward = self.compute_driver_reward()
                return {'driver': driver_obs, 'passenger': self.state.make_passenger_observation()}, \
                       {'driver': driver_reward, 'passenger': self.compute_passenger_reward()}, \
                       {'__all__': self.state.is_done()}, {}

        if 'passenger' in action_dict:
            passenger_obs = self.passenger_step(action_dict['passenger'])

        self.obs = {
            'driver': driver_obs,
            'passenger': passenger_obs
        }
        self.rewards = {
            'driver': self.compute_driver_reward(),
            'passenger': self.compute_passenger_reward()
        }
        self.dones = {'__all__': self.state.is_done()}
        self.infos = {}
        return self.obs, self.rewards, self.dones, self.infos
