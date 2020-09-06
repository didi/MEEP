## GPT agent

#### Introduction

The key component of the `Agent` is how to predict the next agent actions given the dialog history. 
There are many different methods to accomplish this from either machine learning or rule-based system perspectives. 
Generative Pre-training 2 (GPT-2) has been shown impressive results in generating realistic text, and can also be fine-tuned to generate human-like text on a range of domains, including dialog.
In this section, we briefly introduce our machine learning based GPT agent.

We represent the dialogs in plain-text format, including all user utterances, agent utterances, API calls, and their returned variables. 
We fine-tune the model on the causal language modeling objective using this data. 
To produce the agent's action at a given turn, we use the dialog so far as context and generate the next line of text, which corresponds to the agent's predicted action. 
An example is shown in below:

###### Context
```
source_address = 4640 Admiralty Way, Marina del Rey
source_latlong = (33.9816425, -118.4409761)
USER: find a LA fitness near LAX
PREDICT: [ACTION] find_place [PARAM] LAX [PARAM] 33.9816425 [PARAM] -118.4409761
v1_address = 1 World Way, Los Angeles, CA 90045, United States
v1_name = Los Angeles International Airport
v1_latlong = (33.9415889, -118.40853)
v1_place_id = ChIJtU-yE9KwwoAR8a2LaVd7qHc
v1_street_number = 1
v1_street_name = World Way
v1_locality = Los Angeles
v1_distance = 4.7 mi
v1_duration = 17 mins
PREDICT: 
```

###### Generate
```
[ACTION] find_place [PARAM] LA fitness [PARAM] (33.9415889, -118.40853)
```

#### How to train and evaluate

###### Train

Command to train GPT agent:
```bash
cd agents/gpt2_agent

# INPUT_ACTION_LEVEL_DATASET_DIR must contain 3 directories: 
#   train/, dev/, and test/  
# Each directory must store action-level log-files.
# See dataset/README.md for how to generate action-level log-files.
INPUT_ACTION_LEVEL_DATASET_DIR=your_action_level_datasets_dir

# Preprocess action-level datasets.
# Preprocessed datasets will be stored in $OUTPUT_DATASET_DIR/{train|dev|test}.txt
OUTPUT_DATASET_DIR=your_output_dataset_dir
mkdir -p $OUTPUT_DATASET_DIR
./make_dataset.sh $INPUT_ACTION_LEVEL_DATASET_DIR $OUTPUT_DATASET_DIR

# the output directory where the model predictions and checkpoints will be written.
MODEL_OUTPUT_DIR=your_model_output_dir
mkdir -p $MODEL_OUTPUT_DIR

# Make sure you've already installed the requirements.txt in this repo's root folder
pip install -r requirements.txt

# Run fine-tuning (only single-GPU training supported)
mkdir -p $OUTPUT_DATASET_DIR/cache  # gpt2 caches dataset features into the cache/ subdirectory
CUDA_VISIBLE_DEVICES=0 python run_finetuning.py \ 
    --output_dir=$MODEL_OUTPUT_DIR \
    --model_type=gpt2 \
    --model_name_or_path=gpt2 \ 
    --do_train \
    --train_data_file=$OUTPUT_DATASET_DIR/train.txt \
    --do_eval \
    --eval_data_file=$OUTPUT_DATASET_DIR/dev.txt \
    --per_gpu_train_batch_size=1 \
    --per_gpu_eval_batch_size=1 \
    --save_steps=500 \
    --logging_steps=500 \ 
    --overwrite_output_dir \ 
    --num_train_epochs=3 \
    --evaluate_during_training \ 
    --block_size=1024 \
    --overwrite_cache
```

During training, metrics will be saved in the runs/ directory and you can track the training loss and eval perplexity with tensorboard: `tensorboard --logdir=runs/ --bind_all`.

###### Evaluate

Command to evaluate GPT agent:
```bash
cd agents/gpt2_agent

# Generate predictions
PREDICTIONS_DIR=output-predictions-dir
python predict.py \
    --model_path=$MODEL_OUTPUT_DIR/checkpoint-XXXX \
    --test_dir=$INPUT_ACTION_LEVEL_DATASET_DIR/test \
    --output_dir=$PREDICTIONS_DIR

cd ../..
# INPUT_CLICK_LEVEL_DATASET_DIR is similar to INPUT_ACTION_LEVEL_DATASET_DIR
# except it's click-based instead of action-based.
# See dataset/README.md for how to generate click-level log-files.
INPUT_CLICK_LEVEL_DATASET_DIR=path-to-your-click-level-dataset

# Evaluate predictions
python scorer/eval_click_level.py $PREDICTIONS_DIR/click $INPUT_CLICK_LEVEL_DATASET_DIR/test
```
###### Deployment

Command to talk to your agent:
```bash
cd gui/backend
python main.py --port=<backend_port> --domain=destination --num_rooms=1 --log_dir=<your_log_dir> \
  --agent_model_path=$MODEL_OUTPUT_DIR/checkpoint-9000 --agent_class_name=agents.gpt2_agent.agent.GPT2Agent
```
