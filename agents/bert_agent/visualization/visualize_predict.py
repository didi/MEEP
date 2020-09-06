import argparse
import logging

logging.basicConfig(format='%(asctime)s: %(levelname)s: %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger()


def visualize_predict(args):
    with open(args.src) as f_src, open(args.gold_tgt) as f_gold_tgt, open(args.sys_tgt) as f_sys_tgt, open(args.out, 'w') as f_out:
        for src, gold_tgt, sys_tgt in zip(f_src, f_gold_tgt, f_sys_tgt):
            gold_tgt = [ele.strip() for ele in gold_tgt.strip().split('[SEP]')]
            sys_tgt = [ele.strip() for ele in sys_tgt.strip().split('[SEP]')]

            line_to_print = max(len(gold_tgt), len(sys_tgt))

            for i in range(line_to_print):
                if i >= len(gold_tgt):
                    g = ''
                else:
                    g = gold_tgt[i]
                if i >= len(sys_tgt):
                    s = ''
                else:
                    s = sys_tgt[i]

                f_out.write('{}\t{}\n'.format(s, g))
            f_out.write('\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('src')
    parser.add_argument('gold_tgt')
    parser.add_argument('sys_tgt')
    parser.add_argument('out')
    args = parser.parse_args()

    visualize_predict(args)


if __name__ == "__main__":
    main()
