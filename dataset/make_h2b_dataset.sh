#!/bin/bash -ex


GRANULARITY=action_level
python make_dataset.py \
    "../gui/backend/logs/gpt_h2b_dev_set_click_level_corrections" \
    "/home/shared/speech_based_destination_chat/dataset/gpt_h2b_dev_set_click_level_corrections/$GRANULARITY" \
    $GRANULARITY \
    --num_test_files=100
