def flatten_variables(variables):
    flattened = []
    if isinstance(variables, dict):
        if 'variables' in variables:
            # Variable group
            flattened += flatten_variables(variables['variables'])
        elif 'value' in variables:
            # Variable value
            if type(variables['value']) in (list, dict):
                flattened += flatten_variables(variables['value'])
            else:
                flattened.append({
                    'full_name': variables.get('full_name', 'var'),
                    'value': str(variables.get('value', ''))
                })
    elif isinstance(variables, list):
        for group in variables:
            flattened += flatten_variables(group)
    return flattened
