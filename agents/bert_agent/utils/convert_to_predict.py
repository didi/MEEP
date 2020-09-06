import argparse
import logging
import collections
import os

logging.basicConfig(format='%(asctime)s: %(levelname)s: %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger()


def convert_to_predict(args):
    # make sys_predict_out_dir if not exists
    if not os.path.exists(args.sys_predict_out_dir):
        os.makedirs(args.sys_predict_out_dir, exist_ok=True)

    # read system output
    sys_logs = collections.defaultdict(dict)
    with open(args.sys_out) as f:
        for line in f:
            idx, sys_predict, prediction_type = line.strip().split('\t')
            log_id, predict_idx = idx.split('-')
            sys_logs[log_id][predict_idx] = sys_predict

    # validate system output
    gold_fn = os.listdir(args.gold_predict_dir)
    for log_id, sys_predictions in sys_logs.items():
        fn = 'log_{}.txt'.format(log_id)
        if fn not in gold_fn:
            raise FileNotFoundError(
                'system prediction {} not found in gold.'.format(fn)
            )
        # check if the number of predictions matches
        with open(os.path.join(args.gold_predict_dir, fn)) as f,\
                open(os.path.join(args.sys_predict_out_dir, fn), 'w') as f_out:
            predict_num = 0
            for line in f:
                if line.startswith('PREDICT:'):
                    sys_pred = sys_predictions.get(str(predict_num), '[None]')
                    f_out.write('PREDICT: {}\n'.format(sys_pred))
                    predict_num += 1
                else:
                    f_out.write(line)
            if predict_num != len(sys_predictions):
                logging.warning(
                    'the number of predictions of {} does not match gold:\n sys: {}, gold: {}'.format(
                        log_id, len(sys_predictions), predict_num)
                )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('sys_out')
    parser.add_argument('gold_predict_dir')
    parser.add_argument('sys_predict_out_dir')
    args = parser.parse_args()

    convert_to_predict(args)


if __name__ == "__main__":
    main()
