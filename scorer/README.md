## Evaluating my automatic dialog agent

#### Intrinsic Evaluation

The intrinsic metric evaluates "what to do/say next?" at a finer grain.
Because trained agents are intended to mimic human agent decisions seen in the training data, we can test how often their individual "click decisions" match those of human agents.
To better understand the agent clicks and study the system behaviors in different conditions, we categorize agent clicks into action clicks, query clicks, and parameter clicks and measure them separately.
As the goal of the conversation is to let the agent locate the correct destination, we use "destination accuracy" to measure whether the agent drives to the correct place in the end.
Our scorer prints accuracy of the following items:
* Action accuracy: prediction of API and template selection, such as find_place and "It is {} away."
* Query accuracy: a fuzzy macth based accuracy score that measures the query selection for certain API calls, for example, "Starbucks in Venice"
* Parameter accuracy: prediction of the parameter selections, such as latitude and longitude.
* Overall accuracy: an overall accuracy of action, query and parameter prediction.
* Destination accuracy: the percentage of in how many conversations, the agent drives to the correct place.

Command for intrinsic evaluation:
```bash
python eval_click_level.py \
    <hypothesis_dir> \
    <gold_dir>
```

The format of files in the system output directory `<hypothesis_dir>` and the ground truth directory `<gold_dir>` is **.txt** which is defined in [Dialog Serialization/Log Formats](../README.md#log-formats).
An example of how to run scorer: [eval_click_level_example.sh](eval_click_level_example.sh)

#### Extrinsic evaluation

In extrinsic evaluation, we evaluate agents according to successful task completion in live dialogs with human users. 
After each dialog, the user is shown the target lat/long destination on a map and is asked to approve or disapprove the agent's final decision.

To compare agents fairly, we devise the test cases. Each test case is a source address, a manually-written destination constraint, and a first user utterance.
[../gui/backend/evaluation/test_set.txt](../gui/backend/evaluation/test_set.txt) contains some examples of the destination chat test cases, where each column is **source_address**, **first_user_utterance**, and **destination_address** respectively.

Extrinsic evaluation UI and instructions:
![](../img/extrinsic_eval_ui.png)


Command to start extrinsic evaluation backend:
```bash
cd ../gui/backend
python main.py
    --port=<backend_port>
    --domain=destination
    --evaluation_file <evaluation_file>
    --agent_class_name <agent_class_name>
```
`evaluation_file` is the file that contains extrinsic evaluation test cases, e.g. [../gui/backend/evaluation/test_set.txt](../gui/backend/evaluation/test_set.txt).
`agent_class_name` is Python path of automatic-agent class name, e.g. `agents.rule_based_agent.RuleBasedAgent`.

Command to start extrinsic evaluation frontend:
```bash
cd ../gui/frontend
python bash run.sh <backend_port> <frontend_port>
```
