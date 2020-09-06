import re
from users.user import User

class GenericUser(User):
    ''' Domain-Agnostic User '''
    def __init__(self, user_shared_state, user_model_path, domain):
        super().__init__(user_shared_state, user_model_path)
        self.domain = domain

    def _command_complete(self, partial_command):
        ''' Args:
                partial_command - A list consisting of API endpoint or a template plus its parameters
            Returns bool: 
                Whether the partial command has all the necessary parameters or not
        '''
        if len(partial_command) == 0: return False
        action, params = partial_command[0], partial_command[1:]
        for template in self.domain.user_templates_list:
            if template == action:
                return len(re.findall(r'{.*?}', template)) == len(params)
        assert False, "Couldn't find matching api or templates for action: '%s'" % action
