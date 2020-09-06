#!/bin/bash -e
INPUT_ACTION_LEVEL_DATASET_DIR="$1"
OUTPUT_DATASET_DIR="$2"

for each in $INPUT_ACTION_LEVEL_DATASET_DIR/train/*; do echo "=== $each ==="; cat $each; done > "$OUTPUT_DATASET_DIR"/train.txt
for each in $INPUT_ACTION_LEVEL_DATASET_DIR/dev/*; do echo "=== $each ==="; cat $each; done > "$OUTPUT_DATASET_DIR"/dev.txt
for each in $INPUT_ACTION_LEVEL_DATASET_DIR/test/*; do echo "=== $each ==="; cat $each; done > "$OUTPUT_DATASET_DIR"/test.txt
