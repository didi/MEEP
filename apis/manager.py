import copy
import os
from apis.utils import add_full_names


class VariableManager():
    '''Manages:
        - saved variable state for when agent refreshes
        - interface including counter for logger
    '''

    def __init__(self, socket_emit_fn, logger, initial_variables,
                 get_destination, confirmation_handler, user):
        self.emit = socket_emit_fn
        self._logger = logger
        # deepcopy initial_variables to make every variable manager object have
        # independent initial_variables
        self.initial_variables = copy.deepcopy(initial_variables)
        self.get_destination = get_destination

        self.apis = []
        self.user = user
        self.user_destination, self.dst_lat, self.dst_lng = None, None, None
        self.clear_variables()
        self.end_hint = None
        self.confirmation_handler = confirmation_handler

    def get_variables_helper(self, v):
        variables = {}
        if isinstance(v['value'], list):
            for inner_v in v['value']:
                variables.update(self.get_variables_helper(inner_v))
        else:
            variables[v['full_name']] = v['value']
        return variables

    def get_variables_dict(self):
        variables = {}
        for variable_list in self.request_variables:
            for v in variable_list['variables']:
                variables.update(self.get_variables_helper(v))
        return variables

    def lookup_variable_by_name(self, variable_name, default=''):
        variable_dict = self.get_variables_dict()
        return variable_dict.get(variable_name, default)

    def set_initial_variables(self, initial_variables):
        for key in initial_variables.keys():
            for variable in self.initial_variables['variables']:
                if variable['name'] == key:
                    variable['value'] = initial_variables[key]
        self.request_variables = [copy.deepcopy(self.initial_variables)]
        self.emit('/update_initial_variables')
        self.emit('/history/request_variables/agent', self.request_variables)

    def get_initial_variables(self):
        return {
            v['name']: v['value'] for v in self.initial_variables.get('variables', [])
        }

    def set_end_hint(self, hint):
        self.end_hint = hint

    def clear_variables(self):
        '''Reset variables available to the agent. This should be called when resetting the chat'''
        self.request_number = 0
        self.request_variables = [copy.deepcopy(self.initial_variables)]
        self.emit('/history/request_variables/agent', self.request_variables)
        if self.get_destination is not None:
            source_lat, source_lng = None, None
            for variable in self.initial_variables['variables']:
                if variable['name'] == 'latitude':
                    source_lat = variable['value']
                elif variable['name'] == 'longitude':
                    source_lng = variable['value']
            user_destination = self.get_destination(source_lat, source_lng)
            user_destination['name'] = 'destination'
            user_destination['variables'] = user_destination['value']
            del user_destination['value']
            for variable in user_destination['variables']:
                if variable['name'] == 'latitude':
                    self.dst_lat = variable['value']
                elif variable['name'] == 'longitude':
                    self.dst_lng = variable['value']
            self.user_destination = self.remove_latlong(user_destination)
            add_full_names(
                self.user_destination['variables'],
                self.user_destination['variable_group'])
            if self.user is not None:
                self.user.destination = user_destination
        else:
            self.user_destination = None
        self.emit('/history/request_variables/user', [self.user_destination])
        self.end_hint = None

    def remove_latlong(self, destination):
        new_variable_group = {
            'variable_group': destination.get(
                'variable_group', 'destination')}
        new_variable_group['variables'] = []
        for variable in destination['variables']:
            if variable['name'] not in ('latitude', 'longitude'):
                new_variable_group['variables'].append(variable)
        return new_variable_group

    def check_destination(self, start_driving_params):
        lat = None
        for variable in start_driving_params:
            if variable.get('param', None) == 'dest latitude':
                lat = variable['value']
        lng = None
        for variable in start_driving_params:
            if variable.get('param', None) == 'dest longitude':
                lng = variable['value']

        return lat == self.dst_lat and lng == self.dst_lng

    def end_dialog(self, success, confirmation_type,
                   method_name, request_params):
        self._logger.log_end_dialog(False, success)  # sets _logger.filename
        if self.user_destination is not None:
            destination_correct = self.check_destination(request_params)
            self.confirmation_handler(destination_correct)
        else:
            message = {
                'success': success,
                'filename': self._logger.filename,
                'confirmationType': confirmation_type,

                # function and data for the call that ended the dialog
                'method': method_name,
                'data': request_params,
            }
            if self.end_hint is not None:
                message['endHint'] = self.end_hint
            self.emit('/end_dialog', message)
