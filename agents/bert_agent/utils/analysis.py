import argparse
import logging
import os
import collections
from agents.bert_agent.method_baseline.dataset.dialog import Dialog

logging.basicConfig(format='%(asctime)s: %(levelname)s: %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger()


def analysis(args):
    # load logs from dir
    raw_dialogs = []
    log_fn = [fn for fn in os.listdir(args.log_dir) if fn.endswith('.json')]
    for fn in log_fn:
        with open(os.path.join(args.log_dir, fn)) as f:
            log_json_str = f.read().strip()
            log_id = fn.split('_')[1].split('.')[0]
            raw_dialogs.append((log_id, log_json_str))
    log_num = len(raw_dialogs)
    logger.info('{} dialogs to process.'.format(log_num))

    # load dialogs
    dialogs = [
        Dialog(dialog_json=dialog_json, dialog_id=dialog_id, max_turns=[0, 0, 0],
               is_test=None, tasks=[])
        for dialog_id, dialog_json in raw_dialogs
    ]

    # init stats
    stats = Stats()

    for d in dialogs:
        stats.num_dialogs += 1
        for i, event in enumerate(d.events):
            if event.event_type not in [
                    'api_call', 'agent_utterance', 'end_dialog']:
                continue
            stats.num_commands += 1
            stats.num_action_prediction += 1
            stats.action_distribution[event.action] += 1
            if event.action in ['find_place', 'places_nearby']:
                # get query param stats
                stats.num_query_prediction += 1
                query_param = event.parameters[0]
                if query_param[0].startswith('u'):
                    stats.num_query_from_utterance += 1
                else:
                    stats.num_query_is_variable += 1
                variable_params = event.parameters[1:]
            else:
                variable_params = event.parameters

            # get variable parameter stats
            for param in variable_params:
                if param[0].startswith('u'):
                    stats.num_parameter_from_utterance += 1
                else:
                    stats.num_parameter_is_variable += 1
            stats.num_parameter_prediction += len(variable_params)

            # get variable parameter answer range distribution
            for param in variable_params:
                answer_range = get_answer_range(param[0], d)
                stats.answer_range_dist[answer_range] += 1

                # update parameter type distribution
                if param[0].startswith('u') is True:
                    continue
                _, var_type = parse_var_full_name(param[0])
                stats.parameter_type_distribution[var_type] += 1

            # get number of variable types
            if event.event_type == 'api_call':
                for var in event.variables:
                    stats.variable_type_distribution[var.var_type] += 1

    print(stats)


def get_answer_range(param, dialog):
    for i, e in enumerate(dialog.events):
        if e.event_type not in ['api_call', 'user_utterance',
                                'initial_variables']:
            continue
        for var in e.variables:
            if var.full_name == param:
                return i + 1
    raise ValueError(
        'param {} is not found in any events. dialog id {}'.format(
            param, dialog.dialog_id
        )
    )


def parse_var_full_name(full_name):
    full_name_tokens = full_name.split('_')
    if len(full_name_tokens[1]) == 1:
        entity_id = [full_name_tokens[0], full_name_tokens[1]]
        var_type = ' '.join(full_name_tokens[2:])
    else:
        entity_id = [full_name_tokens[0]]
        var_type = ' '.join(full_name_tokens[1:])
    if ' '.join(entity_id + var_type.split()).replace(' ', '_') != full_name:
        print('parsing var full name error:', full_name, entity_id, var_type)
    return entity_id, var_type


class Stats(object):
    def __init__(self):
        self.num_dialogs = 0
        self.num_commands = 0
        self.num_action_prediction = 0
        self.num_query_prediction = 0
        self.num_query_is_variable = 0
        self.num_query_from_utterance = 0
        self.num_parameter_prediction = 0
        self.num_parameter_is_variable = 0
        self.num_parameter_from_utterance = 0

        self.answer_range_dist = collections.defaultdict(int)
        self.action_distribution = collections.defaultdict(int)
        self.parameter_type_distribution = collections.defaultdict(int)
        self.variable_type_distribution = collections.defaultdict(int)

    def __repr__(self):
        rtn = ''
        fmter = '{:<25}{:>5}\n'
        rtn += fmter.format('Categories', 'Count')
        rtn += '-' * 30 + '\n'
        rtn += fmter.format('dialogs', self.num_dialogs)
        rtn += fmter.format('commands', self.num_commands)
        rtn += fmter.format('action_prediction', self.num_action_prediction)
        rtn += fmter.format('query_prediction', self.num_query_prediction)
        rtn += fmter.format('query_is_variable', self.num_query_is_variable)
        rtn += fmter.format('query_from_utterance',
                            self.num_query_from_utterance)
        rtn += fmter.format('parameter_prediction',
                            self.num_parameter_prediction)
        rtn += fmter.format('parameter_is_variable',
                            self.num_parameter_is_variable)
        rtn += fmter.format('parameter_from_utterance',
                            self.num_parameter_from_utterance)

        rtn += '\nVariable answer range distribution:\n'
        max_range = max(self.answer_range_dist.keys())
        for i in range(1, max_range + 1):
            rtn += '{}\t{}\n'.format(i, self.answer_range_dist[i])

        rtn += '\nAction distribution:\n'
        sorted_dist = sorted(
            self.action_distribution.items(),
            key=lambda x: x[1],
            reverse=True)
        for k, v in sorted_dist:
            rtn += '{}\t{}\n'.format(k, v)

        rtn += '\nParameter type distribution:\n'
        sorted_dist = sorted(self.parameter_type_distribution.items(),
                             key=lambda x: x[1], reverse=True)
        for k, v in sorted_dist:
            rtn += '{}\t{}\n'.format(k, v)

        rtn += '\nVaribale type distribution:\n'
        sorted_dist = sorted(self.variable_type_distribution.items(),
                             key=lambda x: x[1], reverse=True)
        for k, v in sorted_dist:
            rtn += '{}\t{}\n'.format(k, v)

        return rtn


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('log_dir')
    args = parser.parse_args()

    analysis(args)


if __name__ == "__main__":
    main()
