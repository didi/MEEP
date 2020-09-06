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

            # split templates
            dialog = split_templates(stats, dialog)

            # consolidate templates
            dialog = consolidate_templates(stats, dialog)

            # merge lat long
            dialog = merge_latlong(stats, dialog)

            # move_api_call_after_agent_utter
            dialog = move_api_call_after_agent_utter(stats, dialog)

            # remove_duplicated_events
            dialog = remove_duplicated_adjacent_events(stats, dialog)

            f_out.write(json.dumps(dialog, indent=2))
    for k, v in stats.items():
        print('{}: {}'.format(k, v))


def consolidate_templates(stats, dialog):
    rules = [
        # time/distance 1
        (
            ('{} is {} away.',
             'It is {} away.',
             'It is {} and {} away.'),
            2,
            (('distance',), ('duration',))
        ),
        # time/distance 2
        (
            ('You will reach there in {}.',
             'It will take us {} to get there. '),
            1,
            (('duration',),)
        ),
        # time/distance 3
        (
            ('{} is {} away from {}.',
             'It is {} away from {}.'
             ),
            1,
            (('duration',),)
        ),
        # time/distance 4
        (
            ('{} is closest.')
        ),
        # time/distance 5
        (
            ('They are {}, {}, {} away respectively.',)
        ),
        # Identifying places 1
        (
            ('There is {} on {}',
             'There is a {} on {}.',
             'There is {} on {}.',
             '{} on {}?',
             'The one on {}?',
             'There is a {} nearby.',
             '{} is on {}.',
             '{} is on {}'
             'I found {} on {} in {}, does that sound right?'),
            1,
            (('name',), ('street_name', 'address_simple'))
        ),
        # Identifying places 2
        (
            ('There is a {} in {}.',
             'I found {} in {}.',
             'Is the address {}?',
             '{} is in {}.',
             '{} in {}?',
             '{} is the closest {} I could find.',
             '{} is a {}.'),
            1,
            (('name',), ('neighborhood', 'locality', 'address'))
        ),
        # Identifying places 3
        (
            ('I found {} on {}, is that ok?',
             'I found a {} called {} on {} in {}.'),
            0,
            (('name',), ('street_name', 'address_simple', 'address'))
        ),
        # Identifying places 4
        (
            ('Do you mean {}?',
             'How about {}?'),
            0,
            (('name',),)
        ),
        # Identifying places 5
        (
            ('It is on {}.')
        ),
        # Identifying places 6
        (
            ('The address is {}.')
        ),
        # Confirmations 1
        (
            ('Going to {} in {}.',
             'We are going to the {} in {}.',
             'Great, we are going to {}.',
             'You are all set!',
             'We are going to the {} in {}.'),
            2,
            (('name',),)
        ),
        # Confirmations 2
        (
            ('Shall we go?',
             'Shall we go to {} on {}?'),
            0,
            ()
        ),
        # Enumeration two
        (
            ('I also found {} and {}.',
             'I found two places: {} and {}.',
             'I found two {} in {} and {}.'),
            1,
            (('name',), ('name',))
        ),
        # Enumeration three
        (
            ('I found three places: {}, {} and {}.',
             'It’s {}, {}, {}.'),
            0,
            (('name',), ('name',), ('name',))
        ),
        # To remove
        (
            ('Sure, give me a moment.',
             'Pleasure serving you!',
             'Are you okay with that one?',
             'Which one would you like to go to?',
             'Let me check that for you.',
             'Please wait a minute, while I quickly look up this information.',
             'Which would you like to go to?',
             'Where are we going today ?',
             'Please let me know where you would like to go now.',
             'Is it one of those?',
             'Does that sound correct?',
             'I am not sure if it matches your criteria.',
             'Do you want to know how long it takes to get there?'),
            None,
            ()
        ),
        # ratings 1
        (
            ('{} has a rating of {}.',
             'It has a rating of {}.'),
            1,
            (('rating',),)
        ),
        # ratings 2
        (
            ('They are all rated {}.',
             'All are rated {}.',
             ),
        ),
        # ratings 3
        (
            ('Their ratings are {} and {} respectively.',)
        ),
        # Request more info
        (
            ("I don't know.",
             'Could you please give me the cross streets or a major landmark?',
             "I can't find any places for your request, can you give me more information?",
             'I am sorry I am unable to find the place.',
             'I am sorry I am unable to find that information',
             'I could not find a place called {}.',
             'Can you be more specific?',
             'I could not find {} on {}.',
             'Do you happen to know the neigborhood or cross street?',
             'Is there anything else you want me to look up?',
             'Do you know the name of the place?',
             "I'm sorry, I'm not sure what you mean.",
             "I'm sorry, I can't find cross streets yet.",
             "Sorry, I'm not able to do that yet.",
             'I could not find a {} closer than that.',
             'I could not find a {} in {}.',
             'I could not find a {} close to {}.',
             ),
            2,
            ()
        ),
        # Punctuations 1
        (
            ('It is in {}',
             'It is in {}.',
             'The neighborhood is {}.'),
            1,
            (('neighborhood', 'locality'),)
        ),
        # Punctuations 2
        (
            ('Their ratings are {}, {} and {} respectively',
             'Their ratings are {}, {} and {} respectively.'),
            1,
            (('rating',), ('rating',), ('rating',))
        ),
        # confirm
        (
            ('Yes.')
        ),
        # open
        (
            ('{} on {} is open.',
             'It is open.',
             'I dont know. But it is currently open.',)
        ),
        # not open
        (
            ('It is not open.',)
        ),
    ]

    # load variables
    variables = collections.OrderedDict()
    for event in dialog['events']:
        if event['event_type'] == 'api_call':
            flattened_variables = flatten_variables(event['variables'])
            for p in flattened_variables:
                variables[p['full_name']] = p

    # build template mapping
    template_mapping = {}
    for r in rules:
        for t in r[0]:
            if r[1] is None:
                template_mapping[t] = None
            else:
                template_mapping[t] = (r[0][r[1]], r[2])

    # map templates
    new_events = []
    for event in dialog['events']:
        # only process agent utterances
        if event['event_type'] != 'agent_utterance':
            new_events.append(event)
            continue
        stats['num_of_agent_utterances'] += 1
        # only process templates in the mapping table
        if event['template'] not in template_mapping:
            new_events.append(event)
            continue
        # skill when the mapped template and the original template are the same
        mapped_template = template_mapping[event['template']]
        if mapped_template is not None and mapped_template[0] == event['template']:
            new_events.append(event)
            continue

        # ignore event if its template is to be removed.
        if mapped_template is None:
            stats['{} removed'.format(event['template'])] += 1
            stats['num_of_consolidated_templates'] += 1
            continue

        # update event template with the mapped template
        stats['{} --> {}'.format(event['template'], mapped_template[0])] += 1
        stats['num_of_consolidated_templates'] += 1
        event['template'] = mapped_template[0]

        # update params
        if event['template'] in ['Their ratings are {}, {} and {} respectively.',
                                 'I found two places: {} and {}.',
                                 'I found three places: {}, {} and {}.']:
            pass
        elif event['template'] in ['Great, we are going to {}.']:
            end_dialog_event = dialog['events'][-1]
            start_driving_lat = end_dialog_event['destination']['latitude']
            start_driving_long = end_dialog_event['destination']['longitude']
            var_lat = [k for k, v in reversed(variables.items())
                       if v['value'] == start_driving_lat][0]
            var_long = [k for k, v in reversed(variables.items())
                        if v['value'] == start_driving_long][0]
            assert get_entity_from_full_name(
                var_lat) == get_entity_from_full_name(var_long)

            var_name = '{}_name'.format(get_entity_from_full_name(var_lat))

            assert var_name in variables
            event['params'] = [var_name]
        elif mapped_template[1]:
            if len(set([get_entity_from_full_name(p)
                        for p in event['params']])) != 1:
                logging.warning(event)

            entities = [get_entity_from_full_name(
                p) for p in event['params'] if p.startswith('v')]

            # upadate event params
            new_params = []
            for slot_types in mapped_template[1]:
                added = False
                for e in entities:
                    for ele in slot_types:
                        full_name = '{}_{}'.format(e, ele)
                        # print(full_name)
                        if full_name in variables:
                            new_params.append(full_name)
                            added = True
                            break
                    if added:
                        break
            event['params'] = new_params
        else:
            event['params'] = []

        # update event utterance
        event['utterance'] = event['template'].format(
            *[variables[p]['value'] for p in event['params']]
        )

        # print(mapped_template)
        # try:
        #   event['utterance'] = event['template'].format(
        #   *[variables[p]['value'] for p in event['params']]
        # )
        # except:
        #   print(variables)
        #   print(event)
        #   exit()

        new_events.append(event)

    # update events
    dialog['events'] = new_events
    return dialog


def split_templates(stats, dialog):
    # load variables
    variables = collections.OrderedDict()
    for event in dialog['events']:
        if event['event_type'] == 'api_call':
            flattened_variables = flatten_variables(event['variables'])
            for p in flattened_variables:
                variables[p['full_name']] = p

    new_events = []
    for event in dialog['events']:
        if event['event_type'] != 'agent_utterance':
            new_events.append(event)
            continue
        if event['template'] != 'How about one on {}? It is {} away.':
            new_events.append(event)
            continue
        first_event = {
            "event_type": "agent_utterance",
            "utterance": "The one on {}?".format(variables[event['params'][0]]['value']),
            "template": "The one on {}?",
            "params": [event['params'][0]]
        }
        second_event = {
            "event_type": "agent_utterance",
            "utterance": "It is {} away.".format(variables[event['params'][1]]['value']),
            "template": "The one on {}?",
            "params": [event['params'][1]]
        }
        stats['split_templates'] += 1
        new_events += [first_event, second_event]

    # update events
    dialog['events'] = new_events
    return dialog


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
