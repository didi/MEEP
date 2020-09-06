'''Tool to see how well this agent performs on training data'''

import os
import sys
import json
from glob import glob
from keys import keys

sys.path.extend([
    # for loading main backend stuff
    os.path.join(sys.path[0], '../../gui/backend'),
    os.path.join(sys.path[0], '../..')  # for loading agents, apis
])
# remove current directory to eliminate naming conflict with utils
sys.path = sys.path[1:]

from app_factory import AppFactory
from apis import MapInterface

from agents.agent import create_agent


def prepare_two_turn_dataset(split="train"):
    dataset_dir = '/home/shared/speech_based_destination_chat/dataset/json/%s' % split
    dialog_jsons = []
    for fname in sorted(glob(dataset_dir + "/*.json")):
        with open(fname) as f:
            try:
                j = json.load(f)
                dialog_jsons.append(j)
            except json.decoder.JSONDecodeError:
                print("Warning couldn't decode json in", fname)
                continue
    print("loaded %d dialogs" % len(dialog_jsons))

    two_turn_examples = []
    for dialog in dialog_jsons:
        user_utts = []
        prev_event_type = None
        for event in dialog['events']:
            if len(user_utts) == 2 and event['event_type'] != "user_utterance":
                break

            if event["event_type"] == "user_utterance":
                if prev_event_type == "user_utterance":
                    user_utts[-1] += " " + event['utterance']
                else:
                    user_utts.append(event['utterance'])
            prev_event_type = event['event_type']
        assert len(user_utts) <= 2
        if len(user_utts) == 2:
            two_turn_examples.append(user_utts)
    return two_turn_examples


def get_received(socket_client):
    '''return a list of messages received from the server from the agent'''
    result = []
    for variable in socket_client.get_received():
        if variable['name'] == '/message' and variable['args'][0]['sender'] == 'agent':
            result.append(variable['args'][0]['body'])
    return result


if __name__ == '__main__':
    # Set up message passing and agent
    destination_app = AppFactory(
        [MapInterface(map_provider='google', api_key=keys['google_maps'])])
    _flask_client, socket_client = destination_app.create_test_clients()
    agent = create_agent(
        'agents.rule_based_agent.RuleBasedAgent',
        lambda lat, long: None,
        destination_app.interfaces,
    )
    destination_app.set_agent(agent)

    # Consume startup messages
    socket_client.get_received()

    # Test agent by writing training data to it
    split = 'train'
    two_turn_examples = prepare_two_turn_dataset(split)
    out_fname = "two_turn_examples.%s.txt" % split
    with open(out_fname, "w") as out_f:
        for i, turns in enumerate(two_turn_examples):
            user_utt_1, user_utt_2 = turns

            # Send test messages to user
            socket_client.emit(
                '/message', {'sender': 'user', 'body': user_utt_1})
            response1 = get_received(socket_client)
            socket_client.emit(
                '/message', {'sender': 'user', 'body': user_utt_2})
            response2 = get_received(socket_client)

            # Write to output file
            out_f.write(
                "\n".join(
                    ("dialog_idx %d" %
                     i,
                     user_utt_1,
                     *
                     response1,
                     user_utt_2,
                     *
                     response2)) +
                "\n\n")
            agent.reset()
    print("Finished writing examples to", out_fname)
