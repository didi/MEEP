# Script to decouple start_driving and end_dialog
# Only runs on json files, because the other two formats are just human readable
# This script also traces back the variable names for start_driving calls

# This script will fail if the destination location isn't from a variable
# This is usually the case if the destination is accidentally set to the source
# or if the dialog is empty as a relic of changing start location
# Tested on Boliang's cleaned dataset

import argparse
import json
import os

parser = argparse.ArgumentParser(
    description='Decouple start_driving and end_dialog')
parser.add_argument(
    'input_directory',
    help='path to directory containing json files')
parser.add_argument('output_directory', help='path to new output files')
args = parser.parse_args()


def find_variable(request_body, parameter_name, value):
    '''Find the full name of a variable'''
    for variable in request_body:
        if variable['name'] == parameter_name and abs(
                float(variable['value']) - float(value)) < 0.000005:
            return variable['full_name']
        elif isinstance(variable['value'], list):
            val = find_variable(variable['value'], parameter_name, value)
            if val is not None:
                return val


files = os.listdir(args.input_directory)
num_fixed_files = 0
print('Found {} files'.format(len(files)))
for filename in files:
    if filename.endswith('.json'):

        # Skip blank files
        try:
            data = json.load(
                open(
                    os.path.join(
                        args.input_directory,
                        filename)))
        except BaseException:
            continue

        # skip dialogs with no events
        if not data['events']:
            continue
        last_event = data['events'].pop()

        # modify how dialogs end
        if 'success' in last_event:
            continue  # script has already done this dialog
        assert last_event['event_type'] == "end_dialog" and 'start_driving' in last_event

        new_events = []
        if 'destination' in last_event:
            # find where the final lat-long came from by searching backwards
            destination_lat_var = destination_lon_var = None
            for event in reversed(data['events']):
                if event['event_type'] != 'api_call':
                    continue

                destination_lat_var = find_variable(
                    event['variables'], 'latitude', last_event['destination']['latitude'])
                destination_lon_var = find_variable(
                    event['variables'], 'longitude', last_event['destination']['longitude'])

                if destination_lat_var is not None and destination_lon_var is not None:
                    break
            else:
                raise Exception(
                    'Could not backtrace destination in file {}'.format(filename))

            new_events.append({
                "event_type": "api_call",
                "params": [
                    {
                        "variable_name": destination_lat_var,
                        "value": last_event['destination']['latitude'],
                        "param": "latitude"
                    },
                    {
                        "variable_name": destination_lon_var,
                        "value": last_event['destination']['longitude'],
                        "param": "longitude"
                    },
                ],
                "variables": [],
                "endpoint": "start_driving",
            })
        new_events.append(
            {
                "event_type": "end_dialog",
                "success": last_event["start_driving"],
                "user_ended_dialog": False,
            })
        data['events'].extend(new_events)

        with open(os.path.join(args.output_directory, filename), 'w') as fh:
            json.dump(data, fh)
            num_fixed_files += 1
print('Fixed {} files'.format(num_fixed_files))
