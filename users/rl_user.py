import json
from users.generic_user import GenericUser
from agents.rl.policy_server import DEFAULT_CONFIG, action_space_partitions, ActionType

class RLUser(GenericUser):
    def __init__(self, user_shared_state, user_model_path, domain):
        super().__init__(user_shared_state, user_model_path, domain)

        if "rl_config" not in user_shared_state:
            if user_model_path:
                with open(user_model_path, "r") as f:
                    user_shared_state["rl_config"] = json.load(f)
            else:
                user_shared_state["rl_config"] = DEFAULT_CONFIG
            user_shared_state["action_space_partitions"] = action_space_partitions(
                    domain, user_shared_state["rl_config"]["state_space"]["max_variables"], False)

            assert domain.name == user_shared_state["rl_config"]["domain"], \
                "Domain mismatch %s != %s" % (domain.name, user_shared_state["rl_config"]["domain"])
        
            # TODO Currently RLUser can only be run in conjunction with RLAgent, it depends on RLAgent's
            # state and attributes.  To support running RLUser without RLAgent, (e.g. a human or simulation acting as agent)
            # we need to initialize other fields here like we do in rl_agent.py.
            assert user_shared_state["rl_config"]["multiagent"], "Currently only supports multi-agent self-play"

    def make_observation(self):
        obs = self.room.agent.state.make_passenger_observation(self._get_valid_actions_mask())
        if not self.user_shared_state["rl_config"]["state_space"]["include_steps_in_obs_space"] \
                and "steps" in obs:
            del obs["steps"]

        return { "user": obs }

    def get_action(self):
        ''' Returns the action index for the driver '''
        action = self.room.agent.policy_client.get_action(self.room.agent.current_episode_id, self.make_observation())
        assert len(action) == 1 and "user" in action, "Bad action_dict: %s" % str(action)
        return action["user"]

    def _execute_command(self, command):
        ''' Executes a complete template command and returns the reward and user message '''
        message = []
        reward = 0
        action, params = command[0], command[1:]
        if action in self.domain.user_templates_list: 
            message = {
                'body': action.format(*[p['value'] for p in params]),
                'template': action,
                'variables': []
            }
            self.room.agent.state.passenger_partial_command = []
        else:
            assert False, "Invalid action: '%s'" % action
                     
        # self.dones = {'__all__': self.state.is_done()}
        return reward, message

    def _get_valid_actions_mask(self):
        '''
        Return indicator mask of valid actions
        '''
        mask = [0] * len(self.user_shared_state["action_space_partitions"])
        assert len(mask) == self.room.agent.state.passenger_max_actions, \
                "%d != %d" % (len(mask) == len(self.room.agent.state.passenger_max_actions))
        empty_command = len(self.room.agent.state.passenger_partial_command) == 0
        for index, action_type_and_sub_index in self.user_shared_state["action_space_partitions"].items():
            action_type, sub_index = action_type_and_sub_index
            if (action_type == ActionType.TEMPLATE and empty_command) or \
                   (action_type == ActionType.VARIABLE and not empty_command and \
                        sub_index < len(self.room.agent.state.passenger_variables)):
                # TODO ADD (action_type == ActionType.NO_ACTION and empty_command) or \
                mask[index] = 1
        return mask

    def on_message(self, message: str) -> dict:
        user_message = None
        while not user_message:
            cur_state = self.room.state()
            self.room.agent.state.update_state(cur_state)
            action_index = self.get_action()
            reward, user_message = self._step(action_index)
            self.room.agent.send_reward_to_policy_server({"user": reward})
        user_message["sender"] = "user"
        return user_message
