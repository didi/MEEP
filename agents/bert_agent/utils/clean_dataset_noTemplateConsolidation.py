import argparse
import logging
import os
import json
import collections
from agents.bert_agent.methods.baseline.dataset.dialog import flatten_variables

logging.basicConfig(format='%(asctime)s: %(levelname)s: %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger()


def clean_dataset(args):
    stats = collections.defaultdict(int)

    for fn in os.listdir(args.json_dir):
        with open(os.path.join(args.json_dir, fn)) as f, \
                open(os.path.join(args.out_dir, fn), 'w') as f_out:
            dialog = json.load(f)

            # remove api calls whose variables are not used.
            dialog = remove_unnecessary_api_calls(stats, dialog)

            # merge lat long
            # dialog = merge_latlong(stats, dialog)

            # move_api_call_after_agent_utter
            dialog = move_api_call_after_agent_utter(stats, dialog)

            # remove_duplicated_events
            dialog = remove_duplicated_adjacent_events(stats, dialog)

            f_out.write(json.dumps(dialog, indent=2))
    for k, v in stats.items():
        print('{}: {}'.format(k, v))


def merge_latlong(stats, dialog):
    # update source var
    source_variables = dialog['initial_variables']['variables'] \
        if 'variables' in dialog['initial_variables'] \
        else dialog['initial_variables']
    new_source_variables = source_variables[:1] + [
        {
            "name": "latlong",
            "value": '{}/{}'.format(source_variables[1]['value'],
                                    source_variables[2]['value']),
            "full_name": "source_latlong"
        }
    ]
    dialog["initial_variables"] = {
        "variable_group": "source",
        "variables": new_source_variables
    }

    # update events
    new_events = []
    var_dict = {}
    var_dict['source_latitude'] = source_variables[1]
    var_dict['source_longitude'] = source_variables[2]
    for event in dialog['events']:
        if event['event_type'] == 'agent_utterance':
            new_params = []
            for p in event['params']:
                if p.endswith('latitude'):
                    new_params.append(p.replace('latitude', 'latlong'))
                elif p.endswith('longitude'):
                    pass
                else:
                    new_params.append(p)
            event['params'] = new_params
        elif event['event_type'] == 'api_call':
            # load variables
            variables = flatten_variables(event['variables'])
            for var in variables:
                var_dict[var['full_name']] = var

            # update query
            new_params = []
            for p in event['params']:
                if p['param'] == 'query':
                    new_params.append(p)
                elif p['param'].endswith('latitude'):
                    p['param'] = p['param'].replace('latitude', 'latlong')
                    p['value'] = '{}/{}'.format(
                        p['value'],
                        var_dict[p['variable_name'].replace(
                            'latitude', 'longitude')]['value']
                    )
                    p['variable_name'] = p['variable_name'].replace(
                        'latitude', 'latlong')
                    new_params.append(p)
                elif p['param'].endswith('longitude'):
                    pass
                else:
                    new_params.append(p)
            event['params'] = new_params

            # update variables
            new_variables = []
            for var in variables:
                if var['full_name'].endswith('latitude'):
                    longitude = var_dict[var['full_name'].replace(
                        'latitude', 'longitude')]
                    var['full_name'] = var['full_name'].replace(
                        'latitude', 'latlong')
                    var['value'] = '{}/{}'.format(var['value'],
                                                  longitude['value'])
                    var['name'] = 'latlong'
                    new_variables.append(var)
                elif var['full_name'].endswith('longitude'):
                    pass
                else:
                    new_variables.append(var)
            event['variables'] = new_variables
        elif event['event_type'] == 'end_dialog':
            event['destination'] = {
                'latlong': '{}/{}'.format(
                    event['destination']['latitude'],
                    event['destination']['longitude']
                )
            }
        new_events.append(event)

    # update events
    dialog['events'] = new_events
    return dialog


def move_api_call_after_agent_utter(stats, dialog):
    events = dialog['events']
    old_e = [e['event_type'] for e in events]
    new_events = []
    is_modified = True
    while is_modified is True:
        is_modified = False
        new_events.clear()
        idx = 0
        while idx < len(events):
            if events[idx]['event_type'] == 'api_call':
                if events[idx + 1]['event_type'] == 'user_utterance':
                    new_events.append(events[idx + 1])
                    new_events.append(events[idx])
                    is_modified = True
                    idx = idx + 2
                    stats['move_api_call_after_agent_utter'] += 1
                else:
                    new_events.append(events[idx])
                    idx += 1
            else:
                new_events.append(events[idx])
                idx += 1
        events = tuple(new_events)
    new_e = [e['event_type'] for e in new_events]
    # if old_e != new_e:
    #   print('old:', old_e)
    #   print('new:', new_e)

    # update events
    dialog['events'] = new_events
    return dialog


def remove_duplicated_adjacent_events(stats, dialog):
    new_events = []
    prev_event = None
    for event in dialog['events']:
        if event != prev_event:
            new_events.append(event)
        else:
            stats['remove_duplicated_adjacent_events'] += 1
        prev_event = event

    # update events
    dialog['events'] = new_events
    return dialog


def remove_unnecessary_api_calls(stats, dialog):
    used_variables = set()
    # get used variables
    for event in dialog['events']:
        stats['num_events'] += 1
        if event['event_type'] == 'api_call':
            stats['num_api_call_events'] += 1
            for p in event['params']:
                if p['variable_name'].startswith('u'):
                    continue
                else:
                    used_variables.add(p['variable_name'])
        elif event['event_type'] == 'agent_utterance':
            for p in event['params']:
                used_variables.add(p)

    # remove unnecessary api_call events
    new_events = []
    for event in dialog['events']:
        if event['event_type'] == 'api_call':
            flattened_variables = flatten_variables(event['variables'])
            is_necessary = False
            for var in flattened_variables:
                if var['full_name'] in used_variables:
                    is_necessary = True
                    break
            if is_necessary:
                new_events.append(event)
            else:
                stats['num_events_removed'] += 1
        else:
            new_events.append(event)

    # update events
    dialog['events'] = new_events
    return dialog


def get_entity_from_full_name(full_name):
    p = full_name.split('_')
    if len(p[1]) == 1:
        entity = '_'.join(p[:2])
    else:
        entity = '_'.join(p[:1])

    return entity


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('json_dir')
    parser.add_argument('out_dir')
    args = parser.parse_args()

    clean_dataset(args)


if __name__ == "__main__":
    main()
