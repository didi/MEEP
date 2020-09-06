import collections
from frozendict import frozendict
import re


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
    for parameter in request_body:
        if parameter['param'] == parameter_name:
            return parameter['value']


def load_variable(api_variables, variable_name):
    '''Used by runnable log to select a variable by name'''
    for variable in api_variables:
        if variable['name'] == variable_name:
            return variable['value']


def load_templates(template_file):
    templates_list = []
    with open(template_file, 'r') as f:
        for line in f:
            line = line.rstrip('\n')
            if line.startswith('---'):
                template_group = line.rstrip(' ---').lstrip('--- ')
                templates_list.append(
                    {"groupDescription": template_group, "templates": []})
            elif len(templates_list) > 0:
                templates_list[-1]["templates"].append(
                    {'group': template_group, 'template': line, 'params': list(range(len(re.findall('{.*?}', line))))})
    return templates_list


def freeze(obj):
    '''make an object hashable. borrowed from https://stackoverflow.com/a/6025884'''
    if isinstance(obj, collections.Hashable):
        items = obj
    elif isinstance(obj, collections.Mapping):
        items = frozendict((k, freeze(v)) for k, v in obj.items())
    elif isinstance(obj, collections.Iterable):
        items = tuple(freeze(item) for item in obj)
    else:
        raise TypeError(type(obj))
    return items


def snake_case(s):
    '''Turn a string from CamelCase to snake_case'''
    return re.sub('([a-z0-9])([A-Z])', '\\1_\\2', s).lower()


if __name__ == '__main__':
    '''Basic functionality tests'''
    assert snake_case('CamelCase') == 'camel_case'
    assert snake_case('longword') == 'longword'
    assert snake_case(
        'myVariable2AndMyVariable3') == 'my_variable2_and_my_variable3'
