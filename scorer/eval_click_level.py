import argparse
import logging
import os

from utils import API_CALL, fuzzy_string_match

logging.basicConfig(format='%(asctime)s: %(levelname)s: %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger()


def score_predict(args):
    # read file names
    hypothesis = [fn for fn in os.listdir(args.hypothesis_dir)
                  if fn.endswith('.txt')]
    gold = [fn for fn in os.listdir(args.gold_dir)
            if fn.endswith('.txt')]
    mismatched_hypo = [fn for fn in hypothesis if fn not in gold]
    mismatched_gold = [fn for fn in gold if fn not in hypothesis]
    assert len(hypothesis) == len(gold), \
        'the number of hypothesis and gold files does not ' \
        'match.\nmismatched_hypo: {}\nmismatched_gold: {}'.format(
        ', '.join(mismatched_hypo), ', '.join(mismatched_gold)
    )

    # iterate on each file
    hits = {}
    for fn in hypothesis:
        # assert file names of gold and hypothesis are same
        if fn not in gold:
            raise FileNotFoundError(
                '{} not found in {}.'.format(
                    fn, args.gold_dir))
        hypo_fp = os.path.join(args.hypothesis_dir, fn)
        gold_fp = os.path.join(args.gold_dir, fn)

        # load hypo and gold lines
        with open(hypo_fp) as f_hypo, open(gold_fp) as f_gold:
            hypo_lines = f_hypo.read().strip().splitlines()
            gold_lines = f_gold.read().strip().splitlines()

        assert len(hypo_lines) == len(gold_lines), \
            'the number of hypothesis ({}) and gold lines ({}) in {} does not match.'.format(
            len(hypo_lines), len(gold_lines), fn)

        # assert PREDICTs in hypo and gold are valid.
        for i, (hypo_l, gold_l) in enumerate(
                list(zip(hypo_lines, gold_lines))):
            if hypo_l.startswith('PREDICT'):
                assert gold_l.startswith('PREDICT'), \
                    'PREDICT of hypothesis and gold does not match in line {} in ' \
                    '{}.'.format(i, fn)

        # score
        hits[fn] = score(
            hypo_lines, gold_lines
        )

    # print results
    print_results(hits, args.all, args.confusion_matrix)


def score(hypo_lines, gold_lines):
    # get predict values
    hypo_predicts = [line[9:].strip() for line in hypo_lines
                     if line.startswith('PREDICT')]
    gold_predicts = [line[9:].replace('[ACTION]', '').strip()
                     for line in gold_lines if line.startswith('PREDICT')]

    assert len(hypo_predicts) == len(gold_predicts)

    # count hits
    idx = 0
    action_hit = 0
    action_predict = 0
    query_hit = 0
    query_predict = 0
    variable_hit = 0
    variable_predict = 0
    joint_action_hit = 0
    joint_action_predict = 0
    start_driving = 0
    start_driving_hit = 0
    action_confusion_matrix = {}
    while idx < len(gold_predicts):
        if gold_predicts[idx] in API_CALL:
            params = API_CALL[gold_predicts[idx]]
        else:
            params = [1] * gold_predicts[idx].count('{}')

        joint_action_correct = True
        joint_action_predict += 1
        # compare action
        if gold_predicts[idx] in [ele.split('=')[0]
                                  for ele in hypo_predicts[idx].split('|')]:
            action_hit += 1
        else:
            joint_action_correct = False
        action_predict += 1
        action_confusion_matrix.setdefault(gold_predicts[idx], {})
        action_confusion_matrix[gold_predicts[idx]
                                ].setdefault(hypo_predicts[idx], 0)
        action_confusion_matrix[gold_predicts[idx]][hypo_predicts[idx]] += 1

        # compare start_driving
        if gold_predicts[idx] == 'start_driving':
            start_driving += 1
            if gold_predicts[idx + 1] in \
                [ele.split('=')[0] for ele in hypo_predicts[idx + 1].split('|')] and \
                gold_predicts[idx + 2] in \
                    [ele.split('=')[0] for ele in hypo_predicts[idx + 2].split('|')]:
                start_driving_hit += 1

        # compare params
        idx += 1
        for i, p in enumerate(params):
            if gold_predicts[idx + i] != hypo_predicts[idx + i]:
                joint_action_correct = False
            if p == 0:
                query_hit += fuzzy_string_match(
                    gold_predicts[idx + i], hypo_predicts[idx + i]
                )
                query_predict += 1
            elif p == 1:
                variable_hit += 1 if gold_predicts[idx + i] in [
                    ele.split('=')[0] for ele in hypo_predicts[idx + i].split('|')] else 0
                variable_predict += 1
        joint_action_hit += joint_action_correct

        # update idx
        idx += len(params)

    return action_hit, action_predict, query_hit, query_predict, variable_hit, \
        variable_predict, joint_action_hit, joint_action_predict, action_confusion_matrix,\
        start_driving, start_driving_hit


def merge_confusion_matrices(m1, m2):
    '''
    Adds m2 values to m1
    '''
    for k in m2:
        for k2 in m2[k]:
            m1.setdefault(k, {})
            m1[k].setdefault(k2, 0)
            m1[k][k2] += 1


def print_confusion_matrix(m):
    all_keys = set(m.keys())
    for k in m:
        all_keys.union(set(m[k].keys()))
    action_keys = {k for k in all_keys if '_' in k}
    template_keys = {k for k in all_keys if not '_' in k}
    all_keys = sorted(action_keys) + sorted(template_keys)
    # Print column headings
    print('actual \\ predicted \t' + '\t'.join(all_keys))
    # Print rows
    for k1 in all_keys:
        row = [k1]
        for k2 in all_keys:
            # Gold = k1, Hypothesis = k2
            row.append(str(m.get(k1, {}).get(k2, 0)))
        print(';'.join(row))


def print_results(hits, all, print_confusion_matrix):
    # compute acc
    total_action_hit = 0
    total_action_predict = 0
    total_query_hit = 0
    total_query_predict = 0
    total_variable_hit = 0
    total_variable_predict = 0
    total_joint_action_hit = 0
    total_joint_action_predict = 0
    total_action_confusion_matrix = {}
    total_start_driving = 0
    total_start_driving_hit = 0

    log_results = {}
    for log_fn, log_hits in hits.items():
        total_action_hit += log_hits[0]
        total_action_predict += log_hits[1]
        total_query_hit += log_hits[2]
        total_query_predict += log_hits[3]
        total_variable_hit += log_hits[4]
        total_variable_predict += log_hits[5]
        total_joint_action_hit += log_hits[6]
        total_joint_action_predict += log_hits[7]
        merge_confusion_matrices(total_action_confusion_matrix, log_hits[8])
        total_start_driving += log_hits[9]
        total_start_driving_hit += log_hits[10]

        log_results[log_fn] = [
            sum([log_hits[0], log_hits[2], log_hits[4]]) /  # predict acc
            sum([log_hits[1], log_hits[3], log_hits[5]]),
            log_hits[0] / log_hits[1],  # action acc
            log_hits[2] / log_hits[3],  # query acc
            log_hits[4] / log_hits[5],  # variable acc
            log_hits[6] / log_hits[7]  # joint action acc
        ]

    total_predict_hit = sum(
        [total_action_hit, total_query_hit, total_variable_hit]
    )
    total_predict = sum(
        [total_action_predict, total_query_predict, total_variable_predict]
    )
    total_predict_acc = total_predict_hit / total_predict

    total_action_acc = total_action_hit / total_action_predict
    total_query_acc = total_query_hit / total_query_predict
    total_variable_acc = total_variable_hit / total_variable_predict
    total_joint_action_acc = total_joint_action_hit / total_joint_action_predict
    total_start_driving_acc = total_start_driving_hit / total_start_driving

    # print total accuracy
    logger.info('scores:')
    print('\n{:<35}{:>5}{:>10}{:>10}'.format(
        'category', 'acc', 'hit', 'total'))
    print('-' * 60)
    formatter = '{:<35}{:>5.2f}{:>10.2f}{:>10.2f}'
    print(formatter.format('PREDICTION accuracy:', total_predict_acc,
                           total_predict_hit, total_predict))
    print(formatter.format('action prediction accuracy:', total_action_acc,
                           total_action_hit, total_action_predict))
    print(formatter.format('query prediction accuracy:', total_query_acc,
                           total_query_hit, total_query_predict))
    print(formatter.format('variable prediction accuracy:', total_variable_acc,
                           total_variable_hit, total_variable_predict))
    print(formatter.format('joint action prediction accuracy:', total_joint_action_acc,
                           total_joint_action_hit, total_joint_action_predict))
    print(formatter.format('destination accuracy:', total_start_driving_acc,
                           total_start_driving_hit, total_start_driving))
    print()

    # print confusion matrix
    if print_confusion_matrix:
        logger.info('(copy/paste confusion matrix to spreadsheet)')
        print_confusion_matrix(total_action_confusion_matrix)
        print()

    # copy/paste string to spreadsheet
    logger.info('(copy/paste string to spreadsheet)')
    print('{:.2f}\t{:.2f}\t{:.2f}\t{:.2f}\t{:.2f}'.format(
        total_predict_acc, total_action_acc, total_query_acc, total_variable_acc, total_joint_action_acc
    ))

    # print result for each log
    if all:
        log_results = sorted(log_results.items(), key=lambda x: x[1][0])
        logger.info('scores by log:\n')
        # print title
        print('{:<13}{:>15}{:>15}{:>15}{:>15}{:>20}'.format(
            'log_id', 'PREDICT_acc', 'action_acc', 'query_acc', 'variable_acc', 'joint_action_acc'
        ))
        print('-' * 93)
        formatter = '{:<13}{:>15.2f}{:>15.2f}{:>15.2f}{:>15.2f}{:>20.2f}'
        for log_fn, results in log_results:
            print(formatter.format(log_fn, *results))
        print('')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('hypothesis_dir')
    parser.add_argument('gold_dir')
    parser.add_argument('-a', '--all', action='store_true', default=False,
                        help='print result for each log.')
    parser.add_argument('-c', '--confusion_matrix', action='store_true',
                        default=False, help='print confusion matrix.')
    args = parser.parse_args()

    score_predict(args)


if __name__ == "__main__":
    main()
