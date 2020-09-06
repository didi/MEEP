import re
from functools import wraps


def add_full_names(variables, variable_prefix):
    '''
    Flatten a nested dict and concatenate keys {variable_prefix_key1_key2_key3: value}
    modifies `variables`.
    '''
    for i, v in enumerate(variables):
        if isinstance(v['value'], list):
            add_full_names(v['value'], '_'.join((variable_prefix, v['name'])))
        else:
            v['full_name'] = variable_prefix + '_' + str(v['name'])


def load_parameter(request_body, parameter_name):
    '''Find `parameter_name` in `request_body`, which should be in the format that data is sent by requests'''
    for parameter in request_body:
        if parameter['param'] == parameter_name:
            return parameter['value']


def make_english_list(list_, conjunction, oxford_comma=False):
    '''
    Turns a list into an English list. The conjunction should be a word like 'and' or 'or'.

    e.g. [cat, dog, pig], conjunction='and' -> "cat, dog and pig"
    Returns a string
    '''
    if len(list_) <= 1:
        return ''.join(list_)
    elif len(list_) == 2:
        oxford_comma = False  # two element lists never get Oxford commas

    list_ = list_[:]
    if oxford_comma:
        list_[-1] = conjunction + ' ' + list_[-1]
        return ', '.join(list_)
    else:
        list_[-2:] = [list_[-2] + ' ' + conjunction + ' ' + list_[-1]]
        return ', '.join(list_)


def route(endpoint, **kwargs):
    '''
    Decorator to annotate a function, which is used to create React API endpoints
    (see apis/base.py for how they are consumed)
    endpoint (str): the URL endpoint used to mount this function
    '''
    def decorator(fcn):
        fcn.endpoint = endpoint
        fcn.flask_kwargs = kwargs
        return fcn
    return decorator


def completes_dialog(success=True, confirmation_type=None,
                     *, confirmation_params=None):
    '''
    This decorator needs to be called after @route
    I'm not sure why, but it has something to do with how decorators interact
    '''
    if confirmation_type not in [
            'map', 'rate_satisfaction', 'confirm_information', 'default']:
        raise ValueError(
            'Got unexpected confirmation type "{}"'.format(confirmation_type))

    def decorator(fcn):
        fcn.completes_dialog = True

        @wraps(fcn)
        def api_call(self, request_params, *args, **kwargs):
            result = fcn(self, request_params, *args, **kwargs)
            self.manager.end_dialog(
                success=success,
                confirmation_type=confirmation_type,
                method_name=fcn.__name__,
                request_params=request_params)
            return result
        return api_call
    return decorator


def add_adjacent_variable(param_name, replacement):
    '''
    Add a variable to the request_params before the request.
    This is useful for finding extra information about a variable without making the agent enter it

    param_name - name to give the new variable
    replacement - a 2-tuple, containing the first variable name in request_params and the new key to add the value of

    TODO: Make this operate on the entity that the variable corresponds to and move this functionality into interface functions
    '''
    def decorator(fcn):
        @wraps(fcn)
        def api_call(self, request_params, *args, **kwargs):
            new_variable_name = request_params[0]['variable_name'].replace(
                replacement[0], replacement[1])
            new_variable_value = self.manager.lookup_variable_by_name(
                new_variable_name, 'undefined')
            request_params.append({
                "param": param_name,
                "variable_name": new_variable_name,
                "value": new_variable_value
            })
            return fcn(self, request_params, *args, **kwargs)
        return api_call
    return decorator


def add_variable_if_exists(variables, place, variable_name, variable_access):
    current_variable = place
    for key in variable_access:
        if isinstance(key, int):
            if len(current_variable) <= key:
                return
        elif not key in current_variable:
            return
        current_variable = current_variable[key]
    if isinstance(current_variable, list):
        variables.append({'name': variable_name, 'value': [
            {'name': i, 'value': current_variable[i].replace('_', ' ')} for i in range(len(current_variable))
        ]})
    else:
        variables.append(
            {'name': variable_name, 'value': str(current_variable)})


if __name__ == '__main__':
    '''Basic tests. TODO: add these to unittests'''
    assert make_english_list(['cat', 'dog', 'pig'],
                             'and', oxford_comma=False) == 'cat, dog and pig'
    assert make_english_list(['cat', 'dog', 'pig'],
                             'and', oxford_comma=True) == 'cat, dog, and pig'
    assert make_english_list(['cat', 'dog'], 'or',
                             oxford_comma=True) == 'cat or dog'
    assert make_english_list(['cat'], 'or', oxford_comma=True) == 'cat'
