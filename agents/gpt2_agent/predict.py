import glob
import re
import os

import argparse
import numpy as np
import torch
from tqdm import tqdm
from transformers import (
    GPT2LMHeadModel,
    GPT2Tokenizer
)

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
from agents.gpt2_agent.utils import get_action_beam, parse_action, parse_params, preprocess_context, detokenizer


def load_model(model_path):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = GPT2LMHeadModel.from_pretrained(model_path)
    tokenizer = GPT2Tokenizer.from_pretrained(model_path)
    model.to(device)
    return model, tokenizer, device


def prepare_contexts(f):
    context = []
    current_user_utterance = []
    predict_prefix = "PREDICT: "
    with open(f) as test_file:
        for line in test_file:
            line = line.rstrip()
            match = re.match('^u([0-9]+)_.*= (.*)', line)
            if line.startswith(predict_prefix):
                if len(current_user_utterance) > 0:
                    context.append(
                        'User: {}'.format(
                            detokenizer.detokenize(current_user_utterance)))
                    current_user_utterance = []
                target = line[len(predict_prefix):]
                context = preprocess_context(context)
                yield '\n'.join(context + [predict_prefix]), parse_action(target), parse_params(target)
                context.append(line)
            elif match is not None:
                current_user_utterance.append(match.group(2))
            else:
                # Combine user utterances into one line
                if len(current_user_utterance) > 0:
                    context.append(
                        'User: {}'.format(
                            detokenizer.detokenize(current_user_utterance)))
                    current_user_utterance = []
                context.append(line)


def predict(model_path, test_set_glob, output_dir):
    model, tokenizer, device = load_model(model_path)
    for f in tqdm(glob.glob(test_set_glob)):
        predict_lines = []
        for context, action, params in prepare_contexts(f):
            predicted_action, predicted_params = get_action_beam(
                model, tokenizer, context, device)[0]

            # Predict action
            context += "[ACTION] {}".format(action)
            if predicted_action != action:
                _, predicted_params = get_action_beam(
                    model, tokenizer, context, device)[0]
            predicted_params = predicted_params[:len(params)]

            # Predict parameters
            for i in range(len(params)):
                predicted_p = predicted_params[i] if i < len(
                    predicted_params) else "NULL"
                p = params[i]
                context += " [PARAM] {}".format(p)
                context = '\n'.join(
                        preprocess_context(
                            context.split('\n')))
                if p != predicted_p and i + 1 < len(params):
                    # Update variables with context from gold for incorrect
                    # predictions
                    _, new_params = get_action_beam(
                        model, tokenizer, context, device)[0]
                    new_params = new_params[:len(params) - i - 1]
                    while len(new_params) + i + 1 < len(params):
                        new_params.append("NULL")
                    predicted_params[i + 1:] = new_params
            while len(predicted_params) < len(params):
                predicted_params.append("NULL")
            predict_lines.append((predicted_action, predicted_params))
        if output_dir is not None:
            if not os.path.isdir(os.path.join(output_dir, 'click')):
                os.makedirs(os.path.join(output_dir, 'click'))
            if not os.path.isdir(os.path.join(output_dir, 'action')):
                os.makedirs(os.path.join(output_dir, 'action'))
            with open(f) as f_in, open(os.path.join(output_dir, "action", os.path.basename(f)), 'w') as f_out_action, \
                    open(os.path.join(output_dir, "click", os.path.basename(f)), 'w') as f_out_click:
                lines = f_in.readlines()
                predict_index = 0
                for line in lines:
                    if line.startswith('PREDICT'):
                        predicted_action, predicted_params = predict_lines[predict_index]
                        f_out_action.write('PREDICT: [ACTION] {} {}\n'.format(
                            predicted_action, ' '.join(['[PARAM] {}'.format(p) for p in predicted_params])))
                        f_out_click.write(
                            'PREDICT: {}\n'.format(predicted_action))
                        for p in predicted_params:
                            f_out_click.write('PREDICT: {}\n'.format(p))
                        predict_index += 1
                    else:
                        f_out_action.write(line)
                        f_out_click.write(line)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model_path", required=True,
        help="Model path"
    )
    parser.add_argument(
        "--test_dir", required=True,
        help="Test set directory"
    )
    parser.add_argument(
        "--output_dir", default=None,
        help="Output directory"
    )
    args = parser.parse_args()
    test_set_glob = "{}/log_*.txt".format(args.test_dir)
    predict(args.model_path, test_set_glob, args.output_dir)
