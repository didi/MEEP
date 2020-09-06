import logging
logging.getLogger('env').setLevel(logging.INFO)
logger = logging.getLogger('env')

from gym.spaces import Tuple, Dict, Box, Discrete, MultiDiscrete
from ray.rllib.env import MultiAgentEnv
from ray.rllib.utils.spaces.repeated import Repeated
import random
random.seed(1)

import pdb

from state import DialogStateNano

class NanoworldEnv(MultiAgentEnv):
    # Constants
    agents = ('passenger', 'driver')

    max_num_actions = 10
    parameters = [".", "yes", "no", "starbucks", "peets"]  # dummy destination '.' to be paired with 'OVER', 'YES', 'NO'
    # parameters = [
    #                ".",
    #                "yes",
    #                "no",
    #                "starbucks",
    #                "peets",
    #                "ralphs",
    #                "traderjoes",
    #                "wholefoods",
    #                "walmart",
    #                "cvs",
    #                "toysrus",
    #                "applestore",
    #                "bestbuy",
    #         ]

    # Action spaces
    passenger_actions = ["SAY", "OVER"]
    passenger_action_space = Tuple([Discrete(len(passenger_actions)), Discrete(len(parameters))])

    driver_actions = ["CONFIRM", "DRIVE"]
    driver_action_space = Tuple([Discrete(len(driver_actions)), Discrete(len(parameters))])

    # observation spaces
    passenger_observation_space = Dict({
        'dialog_history': Repeated(Discrete(len(agents)),
                                   Tuple([Discrete(len(passenger_actions)),
                                          Discrete(len(parameters))]),
                                   max_len=max_num_actions),
        'destination': Discrete(len(parameters))})
    driver_observation_space = Dict({
        'dialog_history': Repeated(Discrete(len(agents)),
                                   Tuple([Discrete(len(passenger_actions)),
                                          Discrete(len(parameters))]),
                                   max_len=max_num_actions)})

    perfect_dialogs = [
        # ("starbucks", [('SAY', 'starbucks'), ('OVER', '.'), ('DRIVE', 'starbucks')]),
        # ("peets", [('SAY', 'peets'), ('OVER', '.'), ('DRIVE', 'peets')]),

        ("starbucks", [('SAY', 'starbucks'),
                       ('OVER', '.'),
                       ('CONFIRM', 'starbucks'),
                       ('DRIVE', 'starbucks')]),

        ("peets", [('SAY', 'peets'),
                   ('OVER', '.'),
                   ('CONFIRM', 'peets'),
                   ('DRIVE', 'peets')]),

        # ("starbucks", [('SAY', 'starbucks'),
        #                ('OVER', '.'),
        #                ('CONFIRM', 'starbucks'),
        #                ('OVER', '.'),
        #                ('YES', '.'),
        #                ('OVER', '.'),
        #                ('DRIVE', 'starbucks')]),
        #
        # ("peets", [('SAY', 'peets'),
        #             ('OVER', '.'),
        #             ('CONFIRM', 'peets'),
        #             ('OVER', '.'),
        #             ('YES', '.'),
        #             ('OVER', '.'),
        #             ('DRIVE', 'peets')]),
    ]

    def __init__(self, config):
        self.is_supervised = False
        destination_id = random.randint(3, len(NanoworldEnv.parameters) - 1)
        self.state = DialogStateNano(NanoworldEnv.max_num_actions, desired_destination=NanoworldEnv.parameters[destination_id])
        self.num_episodes = 0
        self.supervised_episodes = 10000
        self.rewards = dict()
        self.print_episodes = 10000

    def reset(self):
        '''
        Called before each episode, returns the first observation
        '''
        if self.num_episodes % 1000 == 0:
            logger.warning("completed {} episodes.".format(self.num_episodes))

        if self.num_episodes >= self.print_episodes:
            logger.warning('episode ' + str(self.num_episodes))
            logger.warning('------------')
            _, _, history,_ = self.state.get_global_state()
            for h in history:
                logger.warning(h)
            logger.warning('-------------')
        self.num_episodes += 1

        # select the destination

        if self.is_supervised and self.num_episodes < self.supervised_episodes:
            a_list = [3, 4]
            distribution = [.5, .5]
            destination_id = random.choices(a_list, distribution)[0]
        else:
            destination_id = random.randint(3, len(NanoworldEnv.parameters) - 1)

        if self.num_episodes >= self.print_episodes:
            logger.warning('set destination: ' + NanoworldEnv.parameters[destination_id])

        self.state = DialogStateNano(NanoworldEnv.max_num_actions, desired_destination=NanoworldEnv.parameters[destination_id])

        self.obs = {
            'passenger': self.state.make_passenger_observation()
        }
        return self.obs

    def driver_step(self, action):
        a1, a2 = action
        self.state.update_state(NanoworldEnv.driver_actions[a1], NanoworldEnv.parameters[a2])
        obs = self.state.make_driver_observation()
        return obs

    def passenger_step(self, action):
        a1, a2 = action
        self.state.update_state(NanoworldEnv.passenger_actions[a1], NanoworldEnv.parameters[a2])
        obs = self.state.make_passenger_observation()
        return obs

    def compute_driver_reward(self):
        driver_reward = 0
        _, verbal_history, _, driven_destination = self.state.get_global_state()
        if self.state.is_done():   # to compute at the very end
            if self.state.dialog_complete:
                if driven_destination:  # completion through a final drive action
                    if len(verbal_history) == 0:  # driver drives before user says anything
                        driver_reward += -1
                    else:
                        last_uttered_destination = verbal_history[-1].split(" ")[1]
                        if driven_destination == last_uttered_destination:
                            driver_reward += 1
                        else:
                            driver_reward += -1
            else:  # timeout
                driver_reward += -10
        else:  # dialog not yet over
            driver_reward += 0

        if self.is_supervised: # and self.num_episodes < self.supervised_episodes:
            driver_reward += self.compositional_supervision_reward()

        return driver_reward

    def compute_passenger_reward(self):
        desired_destination, verbal_history, _, driven_destination = self.state.get_global_state()
        passenger_reward = 0
        if self.state.is_done():  # to compute at the very end
            if self.state.dialog_complete:  # completion through a final drive action
                if desired_destination == driven_destination:
                    passenger_reward += 1
                else:
                    passenger_reward += -1
            else:  # timeout
                passenger_reward += -10
        else:  # dialog not yet over
            passenger_reward += 0

        if self.is_supervised: # and self.num_episodes < self.supervised_episodes:
            passenger_reward += self.compositional_supervision_reward()

        return passenger_reward

    def compute_supervision_reward(self):
        desired_dest, _, all_actions, _ = self.state.get_global_state()
        dialog_so_far = ", ".join(all_actions)
        for dest, dialog_raw in NanoworldEnv.perfect_dialogs:
            dialog = ", ".join([a + " " + p for a, p in dialog_raw])
            if dest == desired_dest and dialog.startswith(dialog_so_far): # and len(all_actions) > 2:
                return 1
        return 0

    def compositional_supervision_reward(self):
        desired_dest, _, all_actions_sofar, _ = self.state.get_global_state()
        all_actions_sofar = " ".join([action.split(" ")[0] for action in all_actions_sofar])
        perfect_dialog = " ".join([x[0] for x in NanoworldEnv.perfect_dialogs[0][1]])
        if perfect_dialog.startswith(all_actions_sofar):
            return 1
        else:
            return 0

    # any kind of exploration is punished ... so negative reward in supervision is bad..
    def compute_supervision_reward_negative(self):
        desired_dest, _, all_actions, _ = self.state.get_global_state()
        dialog_so_far = ", ".join(all_actions)
        for dest, dialog_raw in NanoworldEnv.perfect_dialogs:
            dialog = ", ".join([a + " " + p for a, p in dialog_raw])
            if dest == desired_dest and dialog.startswith(dialog_so_far): # and len(all_actions) > 2:
                return 1
        return -1

    def step(self, action_dict):
        '''
        Given an action_dict, compute the next observation, rewards, and dones
        '''
        # pdb.set_trace()
        driver_obs = None
        passenger_obs = None

        if 'driver' in action_dict:
            driver_obs = self.driver_step(action_dict['driver'])
        if 'passenger' in action_dict:
            passenger_obs = self.passenger_step(action_dict['passenger'])

        if self.state.turn == 0:
            passenger_obs = self.state.make_passenger_observation()
            driver_obs = None
        elif self.state.turn == 1:
            driver_obs = self.state.make_driver_observation()
            passenger_obs = None

        self.obs = {}
        self.rewards = {}

        if passenger_obs:
            self.obs['passenger'] = passenger_obs
            self.rewards['passenger'] = self.compute_passenger_reward()

        if driver_obs:
            self.obs['driver'] = driver_obs
            self.rewards['driver'] = self.compute_driver_reward()

        self.dones = {'__all__': self.state.is_done()}

        if self.state.is_done():
            self.obs['passenger'] = self.state.make_passenger_observation()
            self.rewards['passenger'] = self.compute_passenger_reward()
            self.obs['driver'] = self.state.make_driver_observation()
            self.rewards['driver'] = self.compute_driver_reward()

        self.infos = {}

        return self.obs, self.rewards, self.dones, self.infos
