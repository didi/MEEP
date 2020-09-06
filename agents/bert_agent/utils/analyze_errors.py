import argparse
import logging
import os

logging.basicConfig(format='%(asctime)s: %(levelname)s: %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger()


CONSISTENCY_TEMPLATE = ['It is {} and {} away.',
                        'I found {} on {}, is that ok?',
                        'I found {} in {}.',
                        '{} is {} away.',
                        'I found a {} called {} on {} in {}.',
                        'There is a {} in {}.',
                        'There is {} on {}',
                        'There is a {} on {}.',
                        'Going to {} in {}.',
                        '{} in {}?',
                        'We are going to the {} in {}.',
                        'It is {} away from {}.',
                        '{} on {}?',
                        '{} has a rating of {}.',
                        '{} is in {}.',
                        'How about one on {}? It is {} away.',
                        'There is {} on {}.',
                        '{} on {} is open.',
                        '{} is on {}.',
                        'Shall we go to {} on {}?',
                        '{} is the closest {} I could find.',
                        '{} has {} category.',
                        'It is on {} in {}.',
                        '{} is at {}.',
                        '{} is a {}.',
                        '{} is on {}',
                        'I could not find {} on {}.',
                        'I could not find a {} in {}.',
                        'The closest {} is {} away.',
                        'I found {} on {} in {}, does that sound right?',
                        'find_place',
                        'distance_matrix',
                        'places_nearby',
                        'start_driving']


def analyze_errors(args):
    sys_fn = sorted(
        [fn for fn in os.listdir(args.sys_click_level_dir)
         if fn.endswith('.txt')]
    )
    gold_fn = sorted(
        [fn for fn in os.listdir(args.gold_click_level_dir)
         if fn.endswith('.txt')]
    )

    assert sys_fn == gold_fn

    num_consistency_pair = 0
    num_consistency_pair_hit = 0
    initial_var_hit = 0
    with open(args.out_file, 'w') as f_out:
        for sys_f, gold_f in zip(sys_fn, gold_fn):
            f_out.write('{}\n'.format(sys_f))
            with open(os.path.join(args.sys_click_level_dir, sys_f)) as f_sys, \
                    open(os.path.join(args.gold_click_level_dir, gold_f)) as f_gold:
                sys_lines = f_sys.read().strip().splitlines()
                gold_lines = f_gold.read().strip().splitlines()
                assert len(sys_lines) == len(gold_lines)

                # write to analysis file
                for s_l, g_l in zip(sys_lines, gold_lines):
                    g_l = g_l.replace('[ACTION] ', '')
                    if s_l.startswith('PREDICT'):
                        assert g_l.startswith('PREDICT')
                        g_l = g_l.replace('PREDICT: ', '')
                        candidates = [ele.replace('PREDICT: ', '').split('=')[
                            0] for ele in s_l.split('|')]
                        if candidates[0] == g_l:
                            label = 'hit'
                        elif g_l in candidates:
                            label = 'topK_hit'
                        else:
                            label = 'miss'
                        f_out.write('{}\t{}\t{}\n'.format(g_l, s_l[9:], label))
                    else:
                        f_out.write('{}\n'.format(g_l))

            f_out.write('\n')

def get_name_from_full_name(full_name):
    v = full_name.split('_')
    if len(v[1]) == 1:
        var = '_'.join(v[:2])
    else:
        var = '_'.join(v[:1])

    return var


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('sys_click_level_dir')
    parser.add_argument('gold_click_level_dir')
    parser.add_argument('out_file')
    args = parser.parse_args()

    analyze_errors(args)


if __name__ == "__main__":
    main()
