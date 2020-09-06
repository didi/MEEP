import argparse
import glob
import random
import os

from utils import API_CALL, fuzzy_string_match

print('''
Welcome to the human evalation. This tool will help you establish a human baseline for how hard your task is.

At each step, type the most likely next action
(slot value, template, API action).
I recommend that you have open:
`gui/backend/static/templates.txt`

You will start in the training phase.
Type 'exit' to go into the test phase, and again to quit.
After quitting, you will see a bunch of metrics.
''')

predict_prefix = 'PREDICT: '


def run_evaluation(data_dir):
    correct_clicks, total_clicks = 0, 0
    correct_actions, total_actions = 0, 0
    correct_queries, total_queries = 0, 0
    correct_variables, total_variables = 0, 0
    correct_joint_action, total_joint_action = 0, 0

    exit_eval = False
    files = glob.glob(os.path.join(data_dir, '*.txt'))
    random.shuffle(files)
    for i, f in enumerate(files):
        if exit_eval:
            break
        print("Evaluating on file {} out of {}".format(i, len(files)))
        print()
        prediction_type = 'action'
        predictions_to_make = 0
        prediction_number = 0
        all_action_correct = True
        with open(f) as eval_file:
            for line in eval_file:
                line = line.strip()
                correct = line[len(predict_prefix):]
                if line.startswith(predict_prefix):
                    prediction = input(predict_prefix)
                    if prediction == 'exit':
                        exit_eval = True
                        break
                    total_clicks += 1
                    if prediction_type == 'action':
                        total_actions += 1
                        if prediction == correct:
                            print("Correct!")
                            correct_actions += 1
                            correct_clicks += 1
                        else:
                            all_action_correct = False
                            print("Incorrect! Correct prediction was:")
                            print(line)
                        prediction_type = 'query' if correct in API_CALL and API_CALL[
                            correct][0] == 0 else 'variable'
                        predictions_to_make = len(
                            API_CALL[correct]) if correct in API_CALL else correct.count('{}')
                        if predictions_to_make == 0:
                            prediction_type = 'action'
                        prediction_number = 0
                    elif prediction_type == 'query':
                        total_queries += 1
                        correct_queries += fuzzy_string_match(
                            correct, prediction)
                        correct_clicks += fuzzy_string_match(
                            correct, prediction)
                        if prediction == correct:
                            print("Correct!")
                        else:
                            all_action_correct = False
                            print("Incorrect! Correct prediction was:")
                            print(line)
                        prediction_type = 'variable'
                        prediction_number += 1
                    elif prediction_type == 'variable':
                        total_variables += 1
                        if prediction == line[len(predict_prefix):]:
                            print("Correct!")
                            correct_variables += 1
                            correct_clicks += 1
                        else:
                            all_action_correct = False
                            print("Incorrect! Correct prediction was:")
                            print(line)
                        prediction_number += 1
                        if prediction_number == predictions_to_make:
                            correct_joint_action += all_action_correct
                            total_joint_action += 1
                            prediction_type = 'action'
                            all_action_correct = True
                else:
                    print(line.rstrip())
            if not exit_eval:
                print("Finished dialog!")
                print("Click level accuracy: {}% ({}/{})".format(100.0 *
                                                                 correct_clicks /
                                                                 max(total_clicks, 1), correct_clicks, total_clicks))
                print("Action prediction accuracy: {}% ({}/{})".format(100.0 *
                                                                       correct_actions /
                                                                       max(total_actions, 1), correct_actions, total_actions))
                print("Query prediction accuracy (fuzzy): {}% ({}/{})".format(100.0 *
                                                                              correct_queries / max(total_queries, 1), correct_queries, total_queries))
                print("Variable prediction accuracy: {}% ({}/{})".format(100.0 *
                                                                         correct_variables /
                                                                         max(total_variables, 1), correct_variables, total_variables))
                print("Joint action prediction accuracy: {}% ({}/{})".format(100.0 *
                                                                             correct_joint_action /
                                                                             max(total_joint_action, 1), correct_joint_action, total_joint_action))
                print("======================")
                print()
            print()
    print("=== FINAL ACCURACY ===")
    print("Click level accuracy: {}% ({}/{})".format(100.0 *
                                                     correct_clicks / max(total_clicks, 1), correct_clicks, total_clicks))
    print("Action prediction accuracy: {}% ({}/{})".format(100.0 *
                                                           correct_actions / max(total_actions, 1), correct_actions, total_actions))
    print("Query prediction accuracy (fuzzy): {}% ({}/{})".format(100.0 *
                                                                  correct_queries / max(total_queries, 1), correct_queries, total_queries))
    print("Variable prediction accuracy: {}% ({}/{})".format(100.0 *
                                                             correct_variables /
                                                             max(total_variables, 1), correct_variables, total_variables))
    print("Joint action prediction accuracy: {}% ({}/{})".format(100.0 *
                                                                 correct_joint_action /
                                                                 max(total_joint_action, 1), correct_joint_action, total_joint_action))
    print("======================")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('train_dir')
    parser.add_argument('test_dir')
    args = parser.parse_args()

    print("Running training, continue until you feel like you get the idea, then predict 'exit'")
    run_evaluation(args.train_dir)
    print("Evaluating on test data")
    run_evaluation(args.test_dir)
