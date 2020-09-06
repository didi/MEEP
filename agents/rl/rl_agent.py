''' Generic RL Agent
# Example command:
1) Start policy server
(dest-dialog-py3_6) scotfang@la-nlp:~/gits/macroworld/agents/rl$ export CUDA_VISIBLE_DEVICES=1 && python policy_server.py
2) Start rl agent
(dest-dialog-py3_6) scotfang@la-nlp:~/gits/macroworld/gui/backend$ python main.py --agent_class_name agents.rl.rl_agent.RLAgent --port 9901 --domain compare_numbers --log_dir logs/compare_numbers_rl --num_rooms=1
'''
import json
import sys

from overrides import overrides
from ray.rllib.env.policy_client import PolicyClient

import os
sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.abspath(__file__)))))
from agents.generic_agent import GenericAgent
from users.human_user import HumanUser

from agents.rl.state import DialogState
from agents.rl.policy_server import DEFAULT_CONFIG, action_space_partitions, register_custom_model, ActionType

class RLAgent(GenericAgent):
    @overrides
    def __init__(self, agent_shared_state,
                 agent_model_path, interfaces, domain):
        super().__init__(agent_shared_state, agent_model_path, interfaces, domain)

        self.interfaces = interfaces

        if "rl_config" not in agent_shared_state:
            if agent_model_path:
                with open(agent_model_path, "r") as f:
                    agent_shared_state["rl_config"] = json.load(f)
            else:
                agent_shared_state["rl_config"] = DEFAULT_CONFIG
            agent_shared_state["action_space_partitions"] = action_space_partitions(
                    domain, agent_shared_state["rl_config"]["state_space"]["max_variables"], True)
            custom_model = agent_shared_state["rl_config"].get("custom_model", None)
            if custom_model:
                register_custom_model(custom_model)
            assert domain.name == agent_shared_state["rl_config"]["domain"], \
                "Domain mismatch %s != %s" % (domain.name, agent_shared_state["rl_config"]["domain"])

        config = agent_shared_state["rl_config"]
        self.state = DialogState(
                config["state_space"]["max_steps"],
                config["state_space"]["max_utterances"],
                config["state_space"]["max_variables"],
                config["state_space"]["embed_dim"],
                config["state_space"]["max_command_length"],
                config["state_space"]["max_conversation_length"],
                # get the number of actions for the user
                len(action_space_partitions(
                        domain,
                        agent_shared_state["rl_config"]["state_space"]["max_variables"], False)),
                len(agent_shared_state["action_space_partitions"]))

        self.policy_client = PolicyClient(
                "http://%s:%d" % (config["policy_server_host"],
                                  int(config["policy_server_port"])),
                inference_mode=config["inference_mode"])

    def send_reward_to_policy_server(self, reward):
        assert isinstance(reward, dict), "reward should be a dict but it's this: %s" % reward
        if not self.agent_shared_state["rl_config"]["multiagent"]:
            reward = reward["agent"]
        self.policy_client.log_returns(self.current_episode_id, reward)

    def make_observation(self):
        obs = self.state.make_driver_observation(self._get_valid_actions_mask())
        if not self.agent_shared_state["rl_config"]["state_space"]["include_steps_in_obs_space"] \
                and "steps" in obs:
            del obs["steps"]

        if self.agent_shared_state["rl_config"]["multiagent"]:
            obs = {"agent": obs}
        return obs

    def get_action(self):
        ''' Returns the action index for the driver '''
        action = self.policy_client.get_action(self.current_episode_id, self.make_observation())
        if self.agent_shared_state["rl_config"]["multiagent"]:
            assert len(action) == 1 and "agent" in action, "Bad action_dict: %s" % str(action)
            return action["agent"]
        else:
            return action

    @overrides
    def on_dialog_finished(self, completed, correct):
        '''
        Called at the end of a dialog. 
        If the dialog is restarted before completion, 'completed' is set to False.
        '''
        reward_function = self.agent_shared_state["rl_config"]["rewards"]
        if self.state.is_done(): # early termination
            agent_reward = reward_function["driver_max_steps"]
        else:
            agent_reward = reward_function["driver_correct_destination"] if correct \
                           else reward_function["driver_incorrect_destination"]
        
        user_reward = None
        if not isinstance(self.room.user, HumanUser):
            if self.state.is_done(): # early termination
                user_reward = reward_function["passenger_max_steps"]
            else:
                user_reward = reward_function["passenger_correct_destination"] if correct\
                             else reward_function["passenger_incorrect_destination"]

        # print("DEBUG: Dialog was finished with reward", agent_reward + user_reward)
        if user_reward is not None:
            joint_reward = {"agent": agent_reward, "user": user_reward}
        else:
            joint_reward = {"agent": agent_reward}
        self.send_reward_to_policy_server(joint_reward)
            
        if self.agent_shared_state["rl_config"]["multiagent"]:
            final_obs = {
                **self.make_observation(),
                **(self.room.user.make_observation() if not isinstance(self.room.user, HumanUser) else {})
            }
        else:
            final_obs = self.make_observation()
        self.policy_client.end_episode(
            self.current_episode_id, final_obs)

    @overrides
    def reset(self, initial_variables):
        ''' Actions to perform when a dialog starts. '''
        super().reset(initial_variables)
        self.state.reset()

        self.current_episode_id = self.policy_client.start_episode(
            training_enabled=self.agent_shared_state["rl_config"]["policy_client_training_enabled"])
        # print("DEBUG started episode", self.current_episode_id)

    def _get_valid_actions_mask(self):
        '''
        Return indicator mask of valid actions for driver

        TODO use action partition indices instead of hard-coded ordering if different action types.
        '''
        mask = [0] * len(self.agent_shared_state["action_space_partitions"])
        assert len(mask) == self.state.driver_max_actions, \
                "%d != %d" % (len(mask) == len(self.state.driver_max_actions))
        empty_command = len(self.state.driver_partial_command) == 0
        for index, action_type_and_sub_index in self.agent_shared_state["action_space_partitions"].items():
            action_type, sub_index = action_type_and_sub_index
            if empty_command and action_type in \
                    (ActionType.API, ActionType.END_DIALOG_API, ActionType.TEMPLATE): # TODO add ActionType.NO_ACTION
                mask[index] = 1
            elif not empty_command and action_type == ActionType.VARIABLE and \
                    sub_index < len(self.state.driver_variables):
                variable = self.state.driver_variables[sub_index]
                variable_name = variable.get('full_name', '')
                if self.state.driver_partial_command[0] in ('/maps/find_place', '/maps/places_nearby'):
                    if (len(self.state.driver_partial_command) == 1 # Query parameter, must click a user utterance
                            and variable_name.startswith('u')) or \
                       (len(self.state.driver_partial_command) == 2 and (variable_name.startswith('u') or 'latitude' in variable_name)) or \
                       (len(self.state.driver_partial_command) == 3 and 'longitude' in variable_name):
                        mask[index] = 1
                elif self.state.driver_partial_command[0] == '/maps/start_driving_no_map':
                    if (len(self.state.driver_partial_command) == 1 and 'latitude' in variable_name) or \
                       (len(self.state.driver_partial_command) == 2 and 'longitude' in variable_name):
                        mask[index] = 1
                else:
                    # Template variable
                    mask[index] = 1
        return mask

    def _step(self, action_index):
        '''
        Steps the agent one-click forward and executes apis/templates if a full command results from the click.
        Args: 
            action_index - index corresponding to the item-to-click (api/template/variable)
        Returns:
            (reward, message) tuple.  Message corresponds to the agent message to respond with, it may be None.
        '''
        raise NotImplementedError

    def on_message(self, message: str, events: dict) -> dict:
        agent_message = None
        while not agent_message:
            if self.state.is_done():
                self.room.manager.end_dialog(False, None, 'give_up', {})
                break
            cur_state = self.room.state()
            self.state.update_state(cur_state)
            action_index = self.get_action()
            reward, agent_message, ended_dialog = self._step(action_index)
            self.send_reward_to_policy_server(reward)
            if ended_dialog:
                break
        return agent_message
