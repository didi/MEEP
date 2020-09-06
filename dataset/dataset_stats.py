import json
import glob


def count_dialogs(dataset):
    dataset_files = glob.glob('click_level/{}/*.txt'.format(dataset))
    return len(dataset_files)


def count_agent_decisions(dataset):
    dataset_files = glob.glob('click_level/{}/*.txt'.format(dataset))
    decisions = 0
    for dataset_file in dataset_files:
        with open(dataset_file) as f:
            for line in f:
                if line.startswith('PREDICT'):
                    decisions += 1
    return decisions


def count_turns(dataset):
    dataset_files = glob.glob('json/{}/*.json'.format(dataset))
    turns = 0
    for f in dataset_files:
        with open(f) as f:
            f_json = json.load(f)
            for event in f_json['events']:
                if event.get('event_type', '') in (
                        'user_utterance', 'agent_utterance'):
                    turns += 1
    return turns


def wait_for_user_accuracy(dataset):
    dataset_files = glob.glob('click_level/{}/*.txt'.format(dataset))
    correct_predictions = 0
    for f in dataset_files:
        with open(f) as f:
            for line in f:
                if "wait_for_user" in line:
                    correct_predictions += 1
    return correct_predictions


def main():
    for dataset in ("train", "dev", "test"):
        print(dataset)
        print("Number of dialogs: {}".format(count_dialogs(dataset)))
        predictions = count_agent_decisions(dataset)
        print(
            "Number of agent decisions: {}".format(
                count_agent_decisions(dataset)))
        print("Number of dialog turns: {}".format(count_turns(dataset)))
        print(
            "Wait for user accuracy: {}".format(
                wait_for_user_accuracy(dataset) /
                predictions))


if __name__ == "__main__":
    main()
