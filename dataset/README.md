## Datasets
#### Chat Interface Dialogs
Dialogs are collected and self-annotated through the [chat interface](../gui/README.md) and logged in 3 formats:
- json [[example]](examples/log_example1.json) - Primary log format.  Logs all events and variables.  Used for training and evaluation.
- txt [[example]](examples/log_example1.txt) - Convenient, human-readable format.
- py [[example]](examples/log_example1.py) - Python executable to replay a dialog's events.

#### Train/Test Dataset Generation
Dialog datasets are generated from the chat interface's json dialogs above.
``` bash
cd dataset/
python make_dataset.py \
  --num_test_files <num_dialogs_to_allocate_to_test_set> \
  --num_dev_files <num_dialogs_to_allocate_to_dev_set> \
  <input_dir_with_json_dialogs> \
  <output_dir> \
  <output_format: {click_level,action_level,json}>
```
#### Train/Test Dataset Formats
The command above can generate datasets in 3 formats: click-level, action-level, and json.

**click-level** [[example]](examples/log_60.click_level.txt) - Each action performed by the agent
is annotated with PREDICT.
```
# Note that there are 4 *separate* prediction annotations to train/evaluate on.
PREDICT: find_place
PREDICT: Urth Cafe
PREDICT: 33.9816425
PREDICT: -118.4409761
```
**action-level** [[example]](examples/log_60.action_level.txt) - Agent actions and parameters are
grouped together.
```
# Only a single prediction annotation to train on.
PREDICT: [ACTION] find_place [PARAM] Urth Cafe [PARAM] 33.9816425 [PARAM] -118.4409761
```
**json** [[example]](examples/log_60.json) - Leave the json dialogs used as input unchanged, but split them into train/dev/test directories.

#### Pre-Generated Datasets

##### Dialog data for specifying trip destination

We collected 497 dialogs for specifying trip destination. In each of these dialogs, the user has a destination
in their mind which they convey to the agent and the agent has to confirm/clarify the destination
until both the agent and the user come to an agreement about where they are driving to. After the completion of the
dialog, a map is shown to the user to ascertain whether it was the intended destination or not.

The dialogs are split into train, development and test splits. As mentioned previously, there are
3 different formats of the dataset. The links to these formats of the dataset are below (TODO: Update these links to a public location)

- [action-level](#)
- [click-level](#)
- [json](#)

The train/dev/test split of the dataset is as follows:

|  Train | Dev  |  Test |
|---|---|---|
| 404  | 46  | 47  |

This dialog dataset can be used to train automated agents and evaluate the various automated agents developed. For more details please refer to [training and evaluating a GPT agent](../agents/README.md#gpt-agent).
