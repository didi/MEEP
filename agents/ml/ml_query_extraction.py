""" Simple prediction class that takes as input json dialog contexts """
import copy
import torch
import json
import numpy as np
from transformers import (
    #    WEIGHTS_NAME,
    #    AdamW,
    #    BertConfig,
    BertForTokenClassification,
    BertTokenizer,
    #    CamembertConfig,
    #    CamembertForTokenClassification,
    #    CamembertTokenizer,
    #    DistilBertConfig,
    #    DistilBertForTokenClassification,
    #    DistilBertTokenizer,
    #    RobertaConfig,
    #    RobertaForTokenClassification,
    #    RobertaTokenizer,
    #    XLMRobertaConfig,
    #    XLMRobertaForTokenClassification,
    #    XLMRobertaTokenizer,
    #    get_linear_schedule_with_warmup,
)
import os
import sys
sys.path.append(os.path.dirname(__file__))
import utils_query_extraction as utils


class QueryExtractor():
    def __init__(self, model_dir, device="cuda", do_lower_case=True,
                 max_seq_length=512, pad_token_label_id=-100):
        self.tokenizer = BertTokenizer.from_pretrained(
            model_dir, do_lower_case=do_lower_case)
        self.model = BertForTokenClassification.from_pretrained(model_dir)
        self.model.eval()
        self.model.to(device)
        self.max_seq_length = max_seq_length
        self.device = device
        self.pad_token_label_id = pad_token_label_id

    def extract_query(self, json_dialog, api_endpoint):
        # Do some preprocessing to json dialog
        empty_query_event = {
            'event_type': 'api_call',
            'endpoint': api_endpoint,
            'params': [{"param": "query", "variable_name": "", "value": ""}],
            'variables': []
        }
        dialog_copy = copy.deepcopy(json_dialog)
        dialog_copy['events'].append(empty_query_event)
        #print("dialog_copy", dialog_copy)

        # Convert json dialog to examples
        example = utils.convert_dialog_json_to_ner_tagged_examples(
            dialog_copy, "dummy_id", api_endpoints=[api_endpoint], param_name="query", do_predict=True)[-1]
        # print("example", example)
        # Convert examples to Bert Features
        input_features = utils.convert_examples_to_features(
            [example], self.max_seq_length, self.tokenizer, debug_log=False)[0]

        # Create input tensors
        input_ids = torch.tensor(
            input_features.input_ids).unsqueeze(0).to(
            self.device)  # Batch size 1
        input_mask = torch.tensor(
            input_features.input_mask).unsqueeze(0).to(
            self.device)  # Batch size 1
        # Need labels for pad_token_id
        labels = torch.tensor(
            input_features.label_ids).unsqueeze(0).to(
            self.device)  # Batch size 1

        with torch.no_grad():
            outputs = self.model(
                input_ids,
                labels=labels,
                attention_mask=input_mask)
            _loss, logits = outputs[:2]
            preds = logits.detach().cpu().numpy()

        preds = np.argmax(preds, axis=2)[0]
        # print(len(preds), "preds", preds)
        assert len(preds) == len(input_features.label_ids)
        assert len(preds) == len(input_features.input_mask)
        assert len(preds) == len(input_features.input_ids)
        assert len(preds) == len(input_features.original_words)

        out_pred_query_list = list()
        for i, pred in enumerate(preds):
            if input_features.input_mask[i] and input_features.label_ids[i] != self.pad_token_label_id:
                if pred in range(len(utils.LABELS)
                                 ) and utils.LABELS[pred] == utils.CLICK_LABEL:
                    out_pred_query_list.append(
                        input_features.original_words[i])
        predicted_query = " ".join(out_pred_query_list)
        # print("predicted_query", predicted_query)
        return predicted_query

    def extract_find_place_query(self, json_dialog):
        return self.extract_query(json_dialog, "find_place")

    def extract_places_nearby_query(self, json_dialog):
        return self.extract_query(json_dialog, "places_nearby")

    def extract_find_place_query_v2(self, source, events):
        return self.extract_query(
            self._convert_source_events_to_json_dialog(source, events), "find_place")

    def extract_places_nearby_query_v2(self, source, events):
        return self.extract_query(self._convert_source_events_to_json_dialog(
            source, events), "places_nearby")

    def _convert_source_events_to_json_dialog(self, source, events):
        json_dialog = {}
        json_dialog["events"] = list(events)
        initial_variables = []
        initial_variables.append(
            {"full_name": "source_address", "name": "address", "value": source["address"]})
        initial_variables.append(
            {"full_name": "source_latitude", "name": "latitude", "value": source["latitude"]})
        initial_variables.append(
            {"full_name": "source_longitude", "name": "longitude", "value": source["longitude"]})
        json_dialog["initial_variables"] = initial_variables
        return json_dialog


if __name__ == "__main__":
    extractor = QueryExtractor(
        "/home/scotfang/gits/dest-handwritten/ml-param-extraction/training_runs/20200107/max_seq_length512/")
    json_dialog = '''
    {
        "initial_variables": [
            {
                "full_name": "source_address",
                "name": "address",
                "value": "4640 Admiralty Way, Marina del Rey"
            },
            {
                "full_name": "source_latitude",
                "name": "latitude",
                "value": 33.9816425
            },
            {
                "full_name": "source_longitude",
                "name": "longitude",
                "value": -118.4409761
            }
        ],
        "duration": 59.75649094581604,
        "agent_name": "Arkady",
        "events": [
            {
                "variables": [
                    {
                        "full_name": "u1_0",
                        "name": 0,
                        "value": "i"
                    },
                    {
                        "full_name": "u1_1",
                        "name": 1,
                        "value": "want"
                    },
                    {
                        "full_name": "u1_2",
                        "name": 2,
                        "value": "to"
                    },
                    {
                        "full_name": "u1_3",
                        "name": 3,
                        "value": "go"
                    },
                    {
                        "full_name": "u1_4",
                        "name": 4,
                        "value": "to"
                    },
                    {
                        "full_name": "u1_5",
                        "name": 5,
                        "value": "usc"
                    },
                    {
                        "full_name": "u1_6",
                        "name": 6,
                        "value": "village"
                    }
                ],
                "utterance": "i want to go to usc village",
                "event_type": "user_utterance"
            }
        ]
    }
    '''
    predicted_q = extractor.extract_find_place_query(json.loads(json_dialog))
    print("predicted_q:", predicted_q)
