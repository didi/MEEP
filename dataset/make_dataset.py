# Do a random (but consistent) train/eval/test split in three
# different formats that depend on how your agent works.

import glob
import json
import random
import os
import sys
import argparse

parser = argparse.ArgumentParser(description='do random train/eval/test split')
parser.add_argument('input_dir')
parser.add_argument('output_dir')
parser.add_argument(
    'granularity',
    choices=[
        'click_level',
        'action_level',
        'json'],
    help='predict a single api call / slot fill / template selection (click), everything jointly (action), or just generate json files (json)')
parser.add_argument('--num_test_files', default=50, type=int)
parser.add_argument('--num_dev_files', default=50, type=int)

# The commands you are probably looking for are:
# GRANULARITY={action_level,click_level,json}
# python3 make_dataset.py
# /home/shared/speech_based_destination_chat/gui/backend/logs
# /home/shared/speech_based_destination_chat/dataset/$GRANULARITY
# $GRANULARITY


def get_variables(v):
    variables = {}
    if isinstance(v['value'], list):
        for inner_v in v['value']:
            variables.update(get_variables(inner_v))
    else:
        variables[v['full_name']] = v['value']
    return variables


def make_prediction_file(f, granularity="click_level"):
    output = []
    variables = {}

    # Skip over dialogs that lead to incorrect destination
    if not f['correct_destination']:
        return output

    # Handle json
    if granularity == 'json':
        return f

    # Load initial variables
    if not isinstance(f['initial_variables'], list):
        f['initial_variables'] = f['initial_variables']['variables']
    for variable in f['initial_variables']:
        new_variables = get_variables(variable)
        for k, v in new_variables.items():
            output.append('{} = {}'.format(k, v))
        variables.update(new_variables)

    events = f.get('events', [])
    first_event = True
    consecutive_user_utterance = False

    for event in events:
        if event['event_type'] == 'user_utterance':
            if not first_event and not consecutive_user_utterance:
                if granularity == "action_level":
                    output.append("PREDICT: [ACTION] wait_for_user")
                elif granularity == "click_level":
                    output.append("PREDICT: wait_for_user")
            consecutive_user_utterance = True
        elif event['event_type'] == 'agent_utterance':
            consecutive_user_utterance = False
            if granularity == "action_level":
                s = [event['template']]
                for param in event['params']:
                    if '+' in param:
                        p = ''
                        for v in param.split(' + '):
                            p += variables.get(v, ' ')
                        s.append(p)
                    else:
                        s.append(variables.get(param, param))
                output.append("PREDICT: [ACTION] {}".format(
                    " [PARAM] ".join(map(str, s))))
            elif granularity == "click_level":
                output.append("PREDICT: {}".format(event['template']))
                for param in event['params']:
                    if '+' in param:
                        p = ''
                        for v in param.split(' + '):
                            p += variables.get(v, ' ')
                        output.append("PREDICT: {}".format(p))
                    else:
                        output.append("PREDICT: {}".format(variables[param]))
        elif event['event_type'] == 'api_call':
            if granularity == "action_level":
                s = [event['endpoint']]
                for param in event['params']:
                    s.append(param['value'])
                output.append("PREDICT: [ACTION] {}".format(
                    " [PARAM] ".join(map(str, s))))
            if granularity == "click_level":
                output.append("PREDICT: {}".format(event['endpoint']))
                for param in event['params']:
                    output.append("PREDICT: {}".format(param['value']))
        elif event['event_type'] == 'end_dialog':
            # end_dialog is implied if start_driving or another terminal api is called
            # so predicting this is useless
            pass
        if 'variables' in event:
            for variable in event['variables']:
                new_variables = get_variables(variable)
                for k, v in new_variables.items():
                    output.append('{} = {}'.format(k, v))
                variables.update(new_variables)
        first_event = False
    return output


if __name__ == "__main__":
    args = parser.parse_args()

    input_files = glob.glob(args.input_dir + '/*.json')
    random.seed(123)
    random.shuffle(input_files)
    datasets = {
        'train': input_files[args.num_test_files + args.num_dev_files:],
        'dev': input_files[args.num_test_files:args.num_test_files + args.num_dev_files],
        'test': input_files[:args.num_test_files]
    }
    for dataset in ('train', 'dev', 'test'):
        os.makedirs(os.path.join(args.output_dir, dataset), exist_ok=True)
        for input_file in datasets[dataset]:
            if os.path.basename(input_file).startswith("evaluation_result"):
                continue
            with open(input_file) as f:
                try:
                    f = json.load(f)
                except json.decoder.JSONDecodeError:
                    print("Skipping file {}".format(input_file))
                    continue
                print("processing", input_file)
                output = make_prediction_file(f, args.granularity)
            if len(output) > 0:
                if args.granularity == 'json':
                    with open(os.path.join(args.output_dir, dataset, input_file.rpartition('/')[-1]), 'w') as f:
                        json.dump(output, f)
                else:
                    with open(os.path.join(args.output_dir, dataset, input_file.rpartition('/')[-1]).replace('json', 'txt'), 'w') as f:
                        for line in output:
                            f.write(line + '\n')
