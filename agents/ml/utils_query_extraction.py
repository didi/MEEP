# coding=utf-8
# Copyright 2018 The Google AI Language Team Authors and The HuggingFace Inc. team.
# Copyright (c) 2018, NVIDIA CORPORATION.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
""" Named entity recognition fine-tuning: utilities to work with CoNLL-2003 task. """


import logging
import os
from copy import deepcopy
import json


logger = logging.getLogger(__name__)
NOCLICK_LABEL = "0"
CLICK_LABEL = "1"
LABELS = [NOCLICK_LABEL, CLICK_LABEL]
LABEL_MAP = {label: i for i, label in enumerate(LABELS)}

SPECIAL_SEPARATORS = {
    "initial_variables": "[INITIAL]",
    "agent_utterance": "[AGENT]",
    "user_utterance": "[USER]",
    "api_call": "[API]",
    "api_param_name": "[API_PARAM_NAME]",
    "api_param_value": "[API_PARAM_VALUE]",
    "var_type": "[VAR_TYPE]",
    "var_value": "[VAR_VALUE]",
}

DOCSTART = "-DOCSTART-"


def remove_underscore(text):
    """ Call this on variable names and api endpoints, so that
        BERT tokenizes names like 'find_place' as 'find place'. """
    return text.replace("_", " ")


def split_utterance_var(v):
    return v.split(' + " " + ')


def recursive_var_search(v, variable_list):
    """ Add all variables to var_list, recursively.
        v is the json variable that will be searched recursively.

        each element in variable_list will be a 3-tuple consisting of:
          * full_name
          * name
          * value
    """
    if isinstance(v['value'], list):
        for v2 in v['value']:
            # print("val:", json.dumps(val, indent=2))
            recursive_var_search(v2, variable_list)
            # var_names_to_tokens[val['full_name']] = val['value']
    else:
        try:
            variable_list.append((v['full_name'], v['name'], v['value']))
        except BaseException:
            assert False, "Json parsing error for variable %s" % (
                json.dumps(v, indent=2))


def convert_dialog_json_to_ner_tagged_examples(d, dialog_id, api_endpoints=[
                                               "find_place", "places_nearby"], param_name="query", do_predict=False):
    ''' Converts a json to [possibly] multiple ner-tagged examples.

        Args:
            d - json representing a single dialog context
            dialog_id - string identifier for the dialog

        Example ner-tagged example format:
        -DOCSTART-log_518.json:::::hawker
        [INITIAL] 0
        [VAR_TYPE] 0
        source address 0
        [VAR_VALUE] 0
        150 North Bridge Road, Singapore 179100 0
        [VAR_TYPE] 0
        source latitude 0
        [VAR_VALUE] 0
        1.293076 0
        [VAR_TYPE] 0
        source longitude 0
        [VAR_VALUE] 0
        103.85206770000002 0
        [USER] 0
        Hi 0
        , 0
        is 0
        there 0
        a 0
        hawker 0
        centre 0
        nearby 0
        ? 0
        [USER] 0
        Hi 0
        , 0
        is 0
        there 0
        a 0
        nearby 0
        hawker 1
        center 0
        ? 0
        [AGENT] 0
        Sure, give me a moment. 0
        [API] 0
        places nearby 0
        [API_PARAM_NAME] 0
        query 0
    '''
    output_examples = list()

    all_tokens_and_labels = list()
    var_name_to_token_index = dict()
    var_names_to_tokens = dict()

    # Add initial variables
    initial_variables = d['initial_variables']['variables'] if isinstance(
        d['initial_variables'], dict) else d['initial_variables']
    all_tokens_and_labels.append(
        [SPECIAL_SEPARATORS['initial_variables'], NOCLICK_LABEL])
    for var in initial_variables:
        var_names_to_tokens[var['full_name']] = str(var['value'])
        all_tokens_and_labels.append(
            [SPECIAL_SEPARATORS["var_type"], NOCLICK_LABEL])
        all_tokens_and_labels.append(
            [remove_underscore(var['full_name']), NOCLICK_LABEL])
        all_tokens_and_labels.append(
            [SPECIAL_SEPARATORS["var_value"], NOCLICK_LABEL])
        # Make token index to relabel correspond to the [VAR_VALUE] token
        var_name_to_token_index[var['full_name']] = len(
            all_tokens_and_labels) - 1
        all_tokens_and_labels.append([var['value'], NOCLICK_LABEL])

    for e in d["events"]:
        if e['event_type'] == "user_utterance":
            all_tokens_and_labels.append(
                [SPECIAL_SEPARATORS['user_utterance'], NOCLICK_LABEL])
            # For user utterances, do not add user variable names (e.g. u1_2)
            # as tokens.
            for var in e['variables']:
                all_tokens_and_labels.append([var['value'], NOCLICK_LABEL])
                var_name_to_token_index[var['full_name']] = len(
                    all_tokens_and_labels) - 1
                var_names_to_tokens[var['full_name']] = var['value']
        elif e['event_type'] == "agent_utterance":
            all_tokens_and_labels.append(
                [SPECIAL_SEPARATORS['agent_utterance'], NOCLICK_LABEL])
            all_tokens_and_labels.append([e['utterance'], NOCLICK_LABEL])
        elif e['event_type'] == "api_call":
            # First, COPY all tokens and labels,
            # and output an example if the endpoint and input parameter match.
            if e['endpoint'] in api_endpoints:
                found_matching_param = False
                gold_params = None
                gold_value = "__DUMMY__"
                copy_all_tokens_and_labels = deepcopy(all_tokens_and_labels)
                # Append something like:
                # [API] 0
                # find_place 0
                copy_all_tokens_and_labels.extend([
                    [SPECIAL_SEPARATORS['api_call'], NOCLICK_LABEL],
                    [remove_underscore(e['endpoint']), NOCLICK_LABEL]
                ])
                # Append something like:
                # [API_PARAM_NAME] 0
                # query 0
                # OR if not target param
                # [API_PARAM_NAME] 0
                # src latitude 0
                # [API_PARAM_VALUE]
                # -118.71 0
                for p in e['params']:
                    copy_all_tokens_and_labels.append(
                        [SPECIAL_SEPARATORS["api_param_name"], NOCLICK_LABEL])
                    copy_all_tokens_and_labels.append(
                        [remove_underscore(p["param"]), NOCLICK_LABEL])
                    if p["param"] == param_name:
                        found_matching_param = True
                        if not do_predict:
                            gold_params = p['variable_name']
                            gold_value = p['value']
                        break
                    copy_all_tokens_and_labels.append(
                        [SPECIAL_SEPARATORS["api_param_value"], NOCLICK_LABEL])
                    copy_all_tokens_and_labels.append(
                        [p["value"], NOCLICK_LABEL])

                if found_matching_param:
                    if not do_predict:
                        # If we found our target API and parameter, re-label their NER NOCLICK tags with CLICK tags,
                        # and write the example to file.
                        assert gold_params is not None
                        gold_params = split_utterance_var(gold_params)
                        for var in gold_params:
                            index = var_name_to_token_index[var]
                            copy_all_tokens_and_labels[index][1] = CLICK_LABEL

                    new_example = [
                        "%s%s:::::%s" %
                        (DOCSTART, dialog_id, gold_value)]
                    for token, label in copy_all_tokens_and_labels:
                        new_example.append(str(token) + " " + label)
                    output_examples.append(new_example)

            # Unrelated to gold-params, add all API stuff
            # Append something like:
            # [API] 0
            # find_place 0
            # [API_PARAM_NAME] 0
            # query 0
            # [API_PARAM_NAME] 0
            # src latitude 0
            # [API_PARAM_VALUE]
            # -118.71 0
            # ...
            all_tokens_and_labels.extend([
                [SPECIAL_SEPARATORS['api_call'], NOCLICK_LABEL],
                [remove_underscore(e['endpoint']), NOCLICK_LABEL]
            ])
            for p in e['params']:
                all_tokens_and_labels.append(
                    [SPECIAL_SEPARATORS["api_param_name"], NOCLICK_LABEL])
                all_tokens_and_labels.append([p["param"], NOCLICK_LABEL])
                all_tokens_and_labels.append(
                    [SPECIAL_SEPARATORS["api_param_value"], NOCLICK_LABEL])
                all_tokens_and_labels.append([p["value"], NOCLICK_LABEL])

            # Append api's returned variables in something like
            # [VAR_TYPE] address
            # [VAR_VALUE] 1234 5th street
            # ....
            # Also index variable tokens and lines by full name
            returned_variables = list()
            for v in e['variables']:
                recursive_var_search(v, returned_variables)
            for full_name, name, value in returned_variables:
                all_tokens_and_labels.append(
                    [SPECIAL_SEPARATORS["var_type"], NOCLICK_LABEL])
                all_tokens_and_labels.append([name, NOCLICK_LABEL])
                all_tokens_and_labels.append(
                    [SPECIAL_SEPARATORS["var_value"], NOCLICK_LABEL])
                # Make token index to relabel correspond to the [VAR_VALUE]
                # token
                var_name_to_token_index[full_name] = len(
                    all_tokens_and_labels) - 1
                all_tokens_and_labels.append([value, NOCLICK_LABEL])
                var_names_to_tokens[full_name] = value

    return output_examples


class InputFeatures(object):
    """A single set of features of data."""

    def __init__(self, input_ids, input_mask, segment_ids,
                 label_ids, original_words=None):
        # Original words are used to map 0/1 NER tags back to raw GUI words
        # that an agent clicked on.
        assert len(original_words) == len(input_ids)
        self.original_words = original_words
        self.input_ids = input_ids
        self.input_mask = input_mask
        self.segment_ids = segment_ids
        self.label_ids = label_ids


def read_examples_from_file(data_dir, mode):
    ''' Read from train|dev|test.txt file that was generated by convert_dialog_json_to_ner_tagged_examples() '''
    file_path = os.path.join(data_dir, "{}.txt".format(mode))
    examples = []
    with open(file_path, encoding="utf-8") as f:
        cur_example = None
        for line in f:
            line = line.strip()
            if line.startswith("-DOCSTART-"):
                if cur_example is not None:
                    examples.append(cur_example)
                cur_example = [line]
            else:
                cur_example.append(line)
        if cur_example:
            examples.append(cur_example)
    return examples


def convert_examples_to_features(
    examples,
    max_seq_length,
    tokenizer,
    cls_token_at_end=False,
    cls_token="[CLS]",
    cls_token_segment_id=1,
    sep_token="[SEP]",
    sep_token_extra=False,
    pad_on_left=False,
    pad_token=0,
    pad_token_segment_id=0,
    pad_token_label_id=-100,
    sequence_a_segment_id=0,
    mask_padding_with_zero=True,
    debug_log=True
):
    """ Convert examples generated by convert_dialog_json_to_ner_tagged_examples() to BERT features.
        Loads examples into a list of `InputBatch`s
        `cls_token_at_end` define the location of the CLS token:
            - False (Default, BERT/XLM pattern): [CLS] + A + [SEP] + B + [SEP]
            - True (XLNet/GPT pattern): A + [SEP] + B + [SEP] + [CLS]
        `cls_token_segment_id` define the segment id associated to the CLS token (0 for BERT, 2 for XLNet)
    """

    total_truncated = 0
    features = []
    for (ex_index, example) in enumerate(examples):
        if ex_index % 10000 == 0:
            logger.info("Converting example %d of %d", ex_index, len(examples))

        # Split each line into individual words, and assign a label to each
        # word.
        words = []
        labels = []
        doc_start = None
        for line in example:
            line = line.strip()
            if doc_start is None:
                assert line.startswith(DOCSTART), "bad docstart line %s" % line
                doc_start = line
                continue
            splits = line.split(" ")
            assert len(splits) > 1, "invalid input: %s" % line
            words.extend(splits[:-1])
            single_label = splits[-1]
            assert single_label in LABELS, "bad label: %s" % single_label
            if single_label == CLICK_LABEL:
                assert len(splits) == 2, "CLICK_LABEL should never be assigned to more than one token per line, docstart: %s line:%s" % (
                    doc_start, line)
            labels.extend([single_label] * (len(splits) - 1))
        assert len(words) == len(labels), "%d != %d" % (
            len(example.words), len(example.labels))

        # Next split words into subword tokens, and assign label_ids
        # accordingly
        tokens = []  # (These are subword tokens)
        label_ids = []  # (These are subwword label_ids)
        # This is NONE except for subword-tokens that are the FIRST token in a
        # word.
        original_words = []
        for word, label in zip(words, labels):
            subword_tokens = tokenizer.tokenize(word)
            if not subword_tokens:
                if debug_log:
                    logger.warning("unable to tokenize %s" % word)
                continue
            tokens.extend(subword_tokens)
            # Use the real label id for the first subword token of the word,
            # and padding ids for the remaining tokens
            label_ids.extend([LABEL_MAP[label]] +
                             [pad_token_label_id] * (len(subword_tokens) - 1))
            original_words.extend([word] + [None] * (len(subword_tokens) - 1))

        # Account for [CLS] and [SEP] with "- 2" and with "- 3" for RoBERTa.
        special_tokens_count = 3 if sep_token_extra else 2
        if len(tokens) > max_seq_length - special_tokens_count:
            tokens = tokens[-(max_seq_length - special_tokens_count):]
            label_ids = label_ids[-(max_seq_length - special_tokens_count):]
            original_words = original_words[-(max_seq_length -
                                              special_tokens_count):]
            # logger.warning("Truncating input example to max_seq_length")
            total_truncated += 1

        # The convention in BERT is:
        # (a) For sequence pairs:
        #  tokens:   [CLS] is this jack ##son ##ville ? [SEP] no it is not . [SEP]
        #  type_ids:   0   0  0    0    0     0       0   0   1  1  1  1   1   1
        # (b) For single sequences:
        #  tokens:   [CLS] the dog is hairy . [SEP]
        #  type_ids:   0   0   0   0  0     0   0
        #
        # Where "type_ids" are used to indicate whether this is the first
        # sequence or the second sequence. The embedding vectors for `type=0` and
        # `type=1` were learned during pre-training and are added to the wordpiece
        # embedding vector (and position vector). This is not *strictly* necessary
        # since the [SEP] token unambiguously separates the sequences, but it makes
        # it easier for the model to learn the concept of sequences.
        #
        # For classification tasks, the first vector (corresponding to [CLS]) is
        # used as as the "sentence vector". Note that this only makes sense because
        # the entire model is fine-tuned.
        tokens += [sep_token]
        label_ids += [pad_token_label_id]
        original_words += [None]
        if sep_token_extra:
            # roberta uses an extra separator b/w pairs of sentences
            tokens += [sep_token]
            label_ids += [pad_token_label_id]
            original_words += [None]
        segment_ids = [sequence_a_segment_id] * len(tokens)

        if cls_token_at_end:
            tokens += [cls_token]
            label_ids += [pad_token_label_id]
            original_words += [None]
            segment_ids += [cls_token_segment_id]
        else:
            tokens = [cls_token] + tokens
            label_ids = [pad_token_label_id] + label_ids
            original_words = [None] + original_words
            segment_ids = [cls_token_segment_id] + segment_ids

        input_ids = tokenizer.convert_tokens_to_ids(tokens)

        # The mask has 1 for real tokens and 0 for padding tokens. Only real
        # tokens are attended to.
        input_mask = [1 if mask_padding_with_zero else 0] * len(input_ids)

        # Zero-pad up to the sequence length.
        padding_length = max_seq_length - len(input_ids)
        if pad_on_left:
            input_ids = ([pad_token] * padding_length) + input_ids
            input_mask = ([0 if mask_padding_with_zero else 1]
                          * padding_length) + input_mask
            segment_ids = ([pad_token_segment_id] *
                           padding_length) + segment_ids
            label_ids = ([pad_token_label_id] * padding_length) + label_ids
            original_words = ([None] * padding_length) + original_words
        else:
            input_ids += [pad_token] * padding_length
            input_mask += [0 if mask_padding_with_zero else 1] * padding_length
            segment_ids += [pad_token_segment_id] * padding_length
            label_ids += [pad_token_label_id] * padding_length
            original_words += [None] * padding_length

        assert len(input_ids) == max_seq_length
        assert len(input_mask) == max_seq_length
        assert len(segment_ids) == max_seq_length
        assert len(label_ids) == max_seq_length
        assert len(original_words) == max_seq_length

        if ex_index < 5 and debug_log:
            logger.info("*** Example ***")
            logger.info("docstart: %s", doc_start)
            logger.info("tokens: %s", " ".join([str(x) for x in tokens]))
            logger.info("input_ids: %s", " ".join([str(x) for x in input_ids]))
            logger.info("input_mask: %s",
                        " ".join([str(x) for x in input_mask]))
            logger.info("segment_ids: %s",
                        " ".join([str(x) for x in segment_ids]))
            logger.info("label_ids: %s", " ".join([str(x) for x in label_ids]))
            logger.info("original_words: %s", " ".join(
                [str(x) if x is not None else "" for x in original_words]))

        features.append(
            InputFeatures(
                input_ids=input_ids,
                input_mask=input_mask,
                segment_ids=segment_ids,
                label_ids=label_ids,
                original_words=original_words)
        )
        if debug_log:
            logger.info(
                "#### TOTAL TRUNCATED EXAMPLES %d ####" %
                total_truncated)
    return features
