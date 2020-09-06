# Agents

## Implementing a Custom Agent

#### The `Agent` Class

After collecting dialog data, you may want to build a virtual agent that can automatically handle users' request and reply to them.
We provide an [`Agent`](agent.py) as a base for your agent. Customized agents should implement the `on_message` method.
The simplest example is the [echo agent](echo_agent.py), which just repeats the user's message.
You can use the chat interface to interact with an agent, and use the agent interface to see what API calls it makes.

The `on_message` method in the `Agent` class is called whenever the system receives user-message and returns an agent-message in response.

<details>
  <summary>An example:</summary>

In the following example, the user wants to go to a roof top bar in Marina del Rey, CA.

The parameter `events` is passed to `on_message` and contains the current dialog context (variables are omitted to save space). See the example in [`dataset/examples/log_60.json`](/dataset/examples/log_60.json) for the complete log.
```json
{
    "events": [
        {
          "event_type": "user_utterance",
          "utterance": "i want to go to a rooftop bar",
          "variables": [...]
        },
        {
          "event_type": "api_call",
          "endpoint": "find_place",
          "params": [
            {
              "param": "query",
              "variable_name": "u1_6 + \" \" + u1_7",
              "value": "rooftop bar"
            },
            {
              "param": "src latitude",
              "variable_name": "source_latitude",
              "value": 33.9816425
            },
            {
              "param": "src longitude",
              "variable_name": "source_longitude",
              "value": -118.4409761
            }
          ],
          "variables": [...]
        }
    ]
}
```

`on_message` method returns next agent action(s) as a list of JSON objects
```json
[
    {
        "body": "How about High Rooftop Lounge?",
        "template": "How about {}?",
        "variables": [
            "v1_name"
        ]
    }
]
```

</details>


#### Agent Training and Evaluation Example
An example detailing the training and evaluation procedure for an agent pre-trained off GPT2 is provideded [here](gpt2_agent).  Note that this is how we produced the pre-trained GPT2 agent listed below.

## Deploying your agent
Follow the deployment instructions in [30-second-startup](../README.md#30-second-startup),
with `--agent_class_name` and `--agent_model_file` set to your agent.

## Pre-Trained Agents
There is a pre-trained model at <TBD>. They work for `--domain=destination` and can be loaded in the backend like so:
```bash
cd ../gui/backend
python main.py --port=<backend_port> --domain=destination --num_rooms=1 --log_dir=<your_log_dir> \
    --agent_class_name=$AGENT_CLASS_NAME \
    --agent_model_path=$AGENT_MODEL_PATH
```

**GPT Agent**
```bash
AGENT_CLASS_NAME=agents.gpt2_agent.agent.GPT2Agent
AGENT_MODEL_PATH=/home/shared/public/meep/gpt_agent
```
**BERT Agent**
```bash
AGENT_CLASS_NAME=agents.bert_agent.methods.baseline.agent.BERTAgent
AGENT_MODEL_PATH=/home/shared/public/meep/bert_agent
```
**Rule-based Agent**
``` bash
AGENT_CLASS_NAME=agents.rule_based_agent.RuleBasedAgent
AGENT_MODEL_PATH=""
```

