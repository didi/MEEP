import argparse
import logging

logging.basicConfig(format='%(asctime)s: %(levelname)s: %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger()


def visualize_actions(args):
    with open(args.action_list) as f:
        actions = f.read().strip().splitlines()
    action_mapping = {i: a for i, a in enumerate(actions)}
    logger.info('{} actions loaded.'.format(len(action_mapping)))

    with open(args.src) as f_src, open(args.gold) as f_gold, \
            open(args.sys) as f_sys, open(args.out, 'w') as f_out:
        for src, gold, sys in zip(f_src, f_gold, f_sys):
            src = src.strip()
            gold = gold.strip()
            sys = sys.strip()
            if not src or not gold or not sys:
                continue

            src = src.split('[ROLE]')
            for i, utter in enumerate(src):
                if i % 2 == 0:
                    role = 'USER'
                else:
                    role = 'AGENT'
                f_out.write('{}\t{}\n'.format(role, utter.strip()))
            sys_action = ' [SEP] '.join(
                [action_mapping[int(a)] for a in sys.split()])
            gold_action = ' [SEP] '.join(
                [action_mapping[int(a)] for a in gold.split()])
            f_out.write('SYS\t{}\t{}\n'.format(sys_action, sys))
            f_out.write('GOLD\t{}\t{}\n\n'.format(gold_action, gold))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('src')
    parser.add_argument('gold')
    parser.add_argument('sys')
    parser.add_argument('action_list')
    parser.add_argument('out')
    args = parser.parse_args()

    visualize_actions(args)


if __name__ == "__main__":
    main()
