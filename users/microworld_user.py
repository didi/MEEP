from users.rl_user import RLUser
from agents.rl.policy_server import ActionType
from agents.rl.utils import flatten_variables

class MicroworldUser(RLUser):
    def _step(self, action_index):
        '''
        Steps the user one-click forward and sends utterances using templates after all placeholders are filled.
        Args: 
            action_index - index corresponding to the item-to-click (wait-for-agent/template/variable)
        Returns:
            (reward, message) tuple.  Message corresponds to the user message to respond with, it may be None.
        '''
        self.room.agent.state.steps += 1
        reward = 0
        message = []
        action_type, sub_index = self.user_shared_state["action_space_partitions"][action_index]
        reward_function = self.user_shared_state["rl_config"]["rewards"]

        if action_type == ActionType.NO_ACTION:
            # print("DEBUG User made no action")
            message = {
                    'body': "NO ACTION",
                    'template': "NO ACTION",
                    'variables': []
                }
            return 0, message
        elif action_type == ActionType.TEMPLATE:
            template = self.domain.user_templates_list[sub_index]
            if not self.room.agent.state.passenger_partial_command:
                # print("User clicked template: {}".format(template))
                self.room.agent.state.passenger_partial_command.append(template)
            else:
                # print("User tried invalid template click: {}".format(template))
                assert False
                return reward_function['passenger_invalid_template'], message
        elif action_type == ActionType.VARIABLE:
            # TODO: Combine utterance variables, as is done in the UI
            if self.room.agent.state.passenger_partial_command:
                if 0 <= sub_index < len(self.room.agent.state.passenger_variables):
                    # print("User clicked variable {}".format(sub_index))
                    variable = self.room.agent.state.passenger_variables[sub_index]
                    if len(self.room.agent.state.passenger_partial_command) > 0 and \
                            type(self.room.agent.state.passenger_partial_command[-1]) is dict and \
                            self.room.agent.state.passenger_partial_command[-1].get('full_name', '').startswith('a') and \
                            variable.get('full_name', '').startswith('a'):
                        # Concatenate consecutive user variables
                        new_user_variable = variable.get('value')
                        if not new_user_variable.startswith("'"):
                            new_user_variable = ' ' + new_user_variable
                        self.room.agent.state.passenger_partial_command[-1]['full_name'] += ' + ' + variable.get('full_name')
                        self.room.agent.state.passenger_partial_command[-1]['value'] += new_user_variable
                    else:
                        self.room.agent.state.passenger_partial_command.append(variable)
                else:
                    # print("User tried invalid variable click: {}".format(sub_index))
                    return reward_function['passenger_invalid_variable'], message
            else:
                # print("User tried invalid variable click (no template selected)")
                assert False
                return reward_function['passenger_invalid_variable'], message
        else:
            assert False, "Invalid action_type: %s" % str(action_type)

        if self._command_complete(self.room.agent.state.passenger_partial_command):
            # print("User completing an action: {}".format(self.room.agent.state.passenger_partial_command))
            reward, message = self._execute_command(self.room.agent.state.passenger_partial_command)

        return reward, message
