'''Domain-agnostic agent that loads templates and apis generically.'''
import re

from agents.agent import Agent


class GenericAgent(Agent):
    def __init__(self, agent_shared_state,
                 agent_model_path, interfaces, domain, **kwargs):
        super().__init__(agent_shared_state, agent_model_path, interfaces, domain, **kwargs)
        self.domain = domain.clone(interfaces)

        # Load generic params stored in shared state.  Interfaces are not stored in shared state
        # because they have per-agent variable managers attached to them.
        if "generic_agent_params" in agent_shared_state:
            return

        shared_params = dict()
        agent_shared_state["generic_agent_params"] = shared_params

    def initial_message(self):
        return {
            'body': 'Hello',
            'template': '',
            'variables': [],
            'sender': 'agent',
        }

    def _command_complete(self, partial_command):
        ''' Args:
                partial_command - A list consisting of API endpoint or a template plus its parameters
            Returns bool:
                Whether the partial command has all the necessary parameters or not
        '''
        if len(partial_command) == 0:
            return False
        action, params = partial_command[0], partial_command[1:]
        api = self.domain.api_functions.get(action, None)
        if api is not None:
            return len(api["params"]) == len(params)
        if action == self.domain.end_dialog['function'].endpoint:
            return len(self.domain.end_dialog["params"]) == len(params)
        for template in self.domain.agent_templates_list:
            if template == action:
                return len(re.findall(r'{.*?}', template)) == len(params)
        assert False, "Couldn't find matching api or templates for action: '%s'" % action

    def _format_api_params(self, api, params):
        return [{
            'param': api["params"][i]["name"],
            'variable_name': p['full_name'],
            'value': p['value']
        } for i, p in enumerate(params)]
