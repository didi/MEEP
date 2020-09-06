''' Policy client agent for microworld Example command:
1) Start policy server
(dest-dialog-py3_6) scotfang@la-nlp:~/gits/macroworld/agents/rl$ export CUDA_VISIBLE_DEVICES=1 && python policy_server.py
2) Start rl agent
(dest-dialog-py3_6) scotfang@la-nlp:~/gits/macroworld/gui/backend$ python main.py --agent_class_name agents.rl.microworld_agent.MicroworldAgent --port 9901 --domain microworld --log_dir logs/microworld --num_rooms=1
'''
import os
import sys

sys.path.append(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from agents.rl.rl_agent import RLAgent
from agents.rl.utils import flatten_variables
from agents.rl.policy_server import ActionType

class MicroworldAgent(RLAgent):
    def _step(self, action_index):
        '''
        Steps the agent one-click forward and executes apis/templates if a full command results from the click.
        Args:
            action_index - index corresponding to the item-to-click (api/template/variable)
        Returns:
            (reward, message, ended_dialog) tuple.  Message corresponds to the agent message to respond with, it may be None.
        '''
        self.state.steps += 1
        reward = {"agent": 0}
        ended_dialog = False
        message = []
        action_type, sub_index = self.agent_shared_state["action_space_partitions"][action_index]
        reward_function = self.agent_shared_state["rl_config"]["rewards"]

        if action_type == ActionType.NO_ACTION:
            # print("DEBUG Driver made no action")
            message = {
                'body': "NO ACTION",
                'template': "NO ACTION",
                'variables': []
            }
            return {"agent": 0}, message, ended_dialog
        elif action_type in (ActionType.API, ActionType.END_DIALOG_API):
            api = list(self.domain.api_functions.values())[sub_index] if action_type == ActionType.API \
                else self.domain.end_dialog
            if not self.state.driver_partial_command:
                # print( "Driver clicked API call: {}".format( api['function'].endpoint))
                self.state.driver_partial_command.append(
                    api['function'].endpoint)
            else:
                # print("Driver tried invalid API click: {}".format(api['function'].endpoint))
                assert False
                return {"agent": reward_function['driver_invalid_api']}, message, ended_dialog
        elif action_type == ActionType.TEMPLATE:
            template = self.domain.agent_templates_list[sub_index]
            if not self.state.driver_partial_command:
                # print("Driver clicked template: {}".format(template))
                self.state.driver_partial_command.append(template)
            else:
                # print("Driver tried invalid template click: {}".format(template))
                assert False
                return {"agent": reward_function['driver_invalid_template']}, message, ended_dialog
        elif action_type == ActionType.VARIABLE:
            if self.state.driver_partial_command:
                if 0 <= sub_index < len(self.state.driver_variables):
                    # print("Driver clicked variable {}".format(sub_index))
                    variable = self.state.driver_variables[sub_index]
                    if len(self.state.driver_partial_command) > 0 and \
                            type(self.state.driver_partial_command[-1]) is dict and \
                            self.state.driver_partial_command[-1].get('full_name', '').startswith('u') and \
                            variable.get('full_name', '').startswith('u'):
                        # Concatenate consecutive user variables
                        new_user_variable = variable.get('value')
                        if not new_user_variable.startswith("'"):
                            new_user_variable = ' ' + new_user_variable
                        self.state.driver_partial_command[-1]['full_name'] += ' + ' + variable.get('full_name')
                        self.state.driver_partial_command[-1]['value'] += new_user_variable
                    else:
                        self.state.driver_partial_command.append(variable)
                else:
                    # print( "Driver tried invalid variable click: {}".format(sub_index))
                    assert False
                    return {"agent": reward_function['driver_invalid_variable']}, message, ended_dialog
            else:
                # print("Driver tried invalid variable click (no action selected)")
                assert False
                return {"agent": reward_function['driver_invalid_variable']}, message, ended_dialog
        else:
            assert False, "Invalid action_type: %s" % str(action_type)

        if self._command_complete(self.state.driver_partial_command):
            print("Driver completed an action: {}".format( self.state.driver_partial_command))
            reward, message, ended_dialog = self._execute_command(
                self.state.driver_partial_command)

        return reward, message, ended_dialog

    def _execute_command(self, command):
        ''' Executes a complete API or template command and returns the reward, agent message, and whether 
            the dialog was ended by an API call or not
        '''
        message = []
        reward = {"agent": 0}
        ended_dialog = False
        action, params = command[0], command[1:]
        api = None
        if action == self.domain.end_dialog['function'].endpoint:
            api = self.domain.end_dialog
        else:
            api = self.domain.api_functions.get(action, None)

        if api:
            response = api["function"](self._format_api_params(api, params))
            self.state.driver_partial_command = []
            self.state.api_call_count += 1
            variables = flatten_variables(response)
            if hasattr(api['function'], 'completes_dialog'): 
                ended_dialog = True
            else:
                if any('error' in v.get('full_name', 'test') for v in variables) or len(variables) == 0:
                    # print("API call was an error or empty")
                    reward["agent"] = self.agent_shared_state["rl_config"]["rewards"]['driver_bad_api_call']
                else:
                    # print("API call got results!")
                    reward["agent"] = self.agent_shared_state["rl_config"]["rewards"]['driver_good_api_call']
                    reward["user"] = self.agent_shared_state["rl_config"]["rewards"]['passenger_good_api_call']
        elif action in self.domain.agent_templates_list:
            message = {
                'body': action.format(*[p['value'] for p in params]),
                'template': action,
                'variables': []
            }
            self.state.driver_partial_command = []
        else:
            assert False, "Invalid action: '%s'" % action

        # self.dones = {'__all__': self.state.is_done()}
        return reward, message, ended_dialog
