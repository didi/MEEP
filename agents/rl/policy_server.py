''' Policy server for RL agents
Example command:
1) Start policy server
(dest-dialog-py3_6) scotfang@la-nlp:~/gits/macroworld/agents/rl$ export CUDA_VISIBLE_DEVICES=1 && python policy_server.py
2) Start rl agent
(dest-dialog-py3_6) scotfang@la-nlp:~/gits/macroworld/gui/backend$ export CUDA_VISIBLE_DEVICES="1" && python main.py --agent_class_name agents.rl.microworld_agent.MicroworldAgent --port 9987 --domain microworld --log_dir logs/microworld --num_rooms=1 --user_class_name users.microworld_user.MicroworldUser --generate_destinations --purge_logs_every_N=1000
'''
import gym
from gym.spaces import Discrete
import ray
from ray.rllib.env.policy_server_input import PolicyServerInput
from ray.rllib.agents.dqn import DQNTrainer
import ray.rllib.agents.ppo as ppo
import ray.rllib.agents.pg as pg
from ray.tune.registry import register_env
from ray.tune.logger import pretty_print
from enum import Enum

import os
import sys
ROOT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__))))  # ROOT directory for this repo
sys.path.append(ROOT_DIR)
from gui.backend.domains.domain import load_domain
from agents.rl.env import MicroworldEnv
from agents.rl.model import ValidActionsModel
from ray.rllib.models import ModelCatalog
from ray.rllib.agents.callbacks import DefaultCallbacks
import torch

class SuccessRateMetricCallbacks(DefaultCallbacks):
    def on_episode_end(self, worker, base_env, policies, episode):
        if "task_success" not in episode.custom_metrics:
            episode.custom_metrics["task_success"] = 0
        episode.custom_metrics["task_success"] += episode._agent_reward_history['agent'][-1] > 1 # TODO don't make this hard-coded

# DQN with torch currently doesn't work, see issue https://github.com/ray-project/ray/issues/9989
DQN_CONFIG = {
    "trainer_class": "DQNTrainer", 
    "trainer_config": {
        #### BEGIN Policy Server params
        # Use a single worker process to run the server.
        "num_workers": 0,
        # Disable OPE, since the rollouts are coming from online clients.
        "input_evaluation": [],
        "train_batch_size": 1,
        "rollout_fragment_length": 1,
        "framework": "torch",
        #### END Policy Server params

        #### BEGIN train_class-specific params
        "exploration_config": {
            "type": "EpsilonGreedy",
            "initial_epsilon": 1.0,
            "final_epsilon": 0.02,
            "epsilon_timesteps": 1000,
        },
        "learning_starts": 0,
        "timesteps_per_iteration": 1,
        "log_level": "INFO",
        #### END train_class-specific params
    }
}

PPO_CONFIG = {
    "trainer_class": "PPOTrainer", 
    "trainer_config": {
        **ppo.DEFAULT_CONFIG.copy(),
        **{
            #### BEGIN Policy Server params
            # Use a single worker process to run the server.
            "num_workers": 0,
            "num_gpus": 1,
            # Disable OPE, since the rollouts are coming from online clients.
            "input_evaluation": [],
            "train_batch_size": 100,
            # "rollout_fragment_length": 1, #20,
            "framework": "torch",
            #### END Policy Server params

            #### BEGIN train_class-specific params
            "sgd_minibatch_size": 50,
            # "num_sgd_iter": 1,
            #### END train_class-specific params
        }
    }
}

PG_CONFIG = {
    "policy_server_logfile": "logs/V2_PG_ValidActions.log",
    "model_checkpoint_dir": "models/microworld/V2_PG_ValidActionsModel",
    "trainer_class": "PGTrainer", 
    "trainer_config": {
        **pg.DEFAULT_CONFIG.copy(),
        **{
            #### BEGIN Policy Server params
            # Use a single worker process to run the server.
            "callbacks": SuccessRateMetricCallbacks,
            "num_workers": 0,
            "num_gpus": 1,
            # Disable OPE, since the rollouts are coming from online clients.
            "input_evaluation": [],
            "train_batch_size": 200,
            "batch_mode": "truncate_episodes",
            # "rollout_fragment_length": 1, #20,
            "framework": "torch",
            #### END Policy Server params

            #### BEGIN train_class-specific params
            # Learning rate.
            "lr": 0.0004,
            #### END train_class-specific params
        }
    }
}

DEFAULT_CONFIG = {
    **PG_CONFIG,
    **{
        "domain": "microworld", 
        "policy_server_host": "localhost",
        "policy_server_port": "9900",
        "policy_client_training_enabled": True,
        "inference_mode": "local", # Can be set to "local" or "remote"
        "debug_mode": False,
        "checkpoint_freq": 30,  
        # Observation space:
        # * Variables: (max_length * embed_dim * max_variables * 2)
        # * Dialog history: (1 + max_length * embed_dim) * max_utterances
        # * Partial command: (max_length * embed_dim * max_command_length)
        "state_space": {
            "max_utterances": 10,
            "max_variables": 50, 
            "embed_dim": 768, 
            "max_command_length": 5,
            "max_conversation_length": 5, # 10,
            "max_steps": 20, # 150,
            "include_steps_in_obs_space": False, # TODO support steps in obs_space
        },
        "rewards": {
            'driver_good_api_call': 1, # 5,
            'driver_bad_api_call': 0,
            'driver_invalid_api': -1,
            'driver_invalid_template': -1,
            'driver_invalid_variable': -1,
            'driver_correct_destination': 10, # 100,
            'driver_incorrect_destination': 0, #-10,
            'driver_max_steps': 0, # -20
            'passenger_good_api_call': 1, # 5,
            'passenger_invalid_template': -1,
            'passenger_invalid_variable': -1,
            'passenger_correct_destination': 10, # 100,
            'passenger_incorrect_destination': 0, # -10,
            'passenger_max_steps': 0, # -20,
        },
        "custom_model": "ValidActionsModel",
        "multiagent": True, # If False, only trains agent, not user.
    }
}

SUPPORTED_TRAINER_CLASSES = { 
    "DQNTrainer": DQNTrainer,
    "PPOTrainer": ppo.PPOTrainer,
    "PGTrainer": pg.PGTrainer,
}
SUPPORTED_CUSTOM_MODELS = {
    "ValidActionsModel": ValidActionsModel
}

def register_custom_model(custom_model):
    print("Registering custom_model:", custom_model)
    ModelCatalog.register_custom_model(custom_model, SUPPORTED_CUSTOM_MODELS[custom_model])
    return True

def init_policy_server(config):
    ''' Start the policy serve r that receives (state, action, reward) batches
        and computes gradients for RL '''
    # By default, Ray will parallelize its workload. However, if you need to debug your Ray program,
    # it may be easier to do everything on a single process. You can force all Ray functions to occur
    # on a single process with local_mode=True.
    memory_limit = 1024 * 1024 * 1024 * 10 # GB
    ray.init(local_mode=config["debug_mode"], object_store_memory=memory_limit)

    trainer_config = config["trainer_config"]
    assert torch.cuda.device_count() >= trainer_config["num_gpus"]
    trainer_config["input"] = lambda ioctx: PolicyServerInput(ioctx, config["policy_server_host"], int(config["policy_server_port"]))

    custom_model = config.get("custom_model", None)
    if custom_model:
        register_custom_model(custom_model)
        trainer_config["model"]["custom_model"] = custom_model

    agent_obs_space, agent_action_space = \
        make_observation_space_and_action_space(config, True)
    if config["multiagent"]:
        user_obs_space, user_action_space = \
            make_observation_space_and_action_space(config, False)
        trainer_config["multiagent"] = {
            "policies": {
                # the first tuple value is None -> uses default policy
                "agent": (None, agent_obs_space, agent_action_space, {}),
                "user": (None, user_obs_space, user_action_space, {})
            },
            "policy_mapping_fn": lambda agent_id: agent_id
        }
        from ray.rllib.examples.env.random_env import RandomMultiAgentEnv
        # Create a fake env for the server. This env will never be used (neither
        # for sampling, nor for evaluation) and its obs/action Spaces do not
        # matter either (multi-agent config above defines Spaces per Policy).
        register_env("custom_env", lambda c: RandomMultiAgentEnv(c))
    else: 
        def custom_env(env_config):
            ''' Create an env stub for policy training.  Only the 
                action_space and observation_space attributes need to be defined,
                no other env functions are needed (e.g. step(), reset(), etc). '''
            env = gym.Env()
            env.action_space = agent_action_space
            env.observation_space = agent_obs_space
            return env
        register_env("custom_env", custom_env)

    trainer = SUPPORTED_TRAINER_CLASSES[config["trainer_class"]](
	    env="custom_env", config=trainer_config)

    os.makedirs(config["model_checkpoint_dir"], exist_ok=True)
    # Attempt to restore from checkpoint if possible.
    latest_checkpoint = os.path.join(
        config["model_checkpoint_dir"], "latest_ckpt")
    if os.path.exists(latest_checkpoint):
        latest_checkpoint = open(latest_checkpoint).read()
        print("Restoring from checkpoint", latest_checkpoint)
        trainer.restore(latest_checkpoint)

    # Serving and training loop
    print("######## Training loop begins... ########")
    count = 0
    while True:
        train_log = trainer.train()
        # print(pretty_print(train_log))
        count += 1
        if count % config["checkpoint_freq"] == 0:
            checkpoint = trainer.save()
            print("#### Writing checkpoint for train iteration", count, "####")
            with open(latest_checkpoint, "w") as f:
                f.write(checkpoint)

class ActionType(Enum):
    NO_ACTION = 0
    API = 1
    END_DIALOG_API = 2
    TEMPLATE = 3
    VARIABLE = 4

def action_space_partitions(domain, max_variables, for_agent):
    ''' Returns a dictionary that maps an action_index to 
    an ActionType and its subindex 
    
    args:
        domain - Domain object from domain.py
        max_variables - max number of variables to choose from
        for_agent - If set to True, computes action space partitions
                    for the agent.  If False, computes partitions for
                    the user.
    '''
    index = 0
    partitions = {}
    partitions[index] = (ActionType.NO_ACTION, None)
    if for_agent:
        for i in range(len(domain.api_functions)):
            index += 1
            partitions[index] = (ActionType.API, i)

        index += 1
        partitions[index] = (ActionType.END_DIALOG_API, None)

    for i in range(len(domain.agent_templates_list if for_agent else \
                       domain.user_templates_list)):
        index += 1
        partitions[index] = (ActionType.TEMPLATE, i)

    for i in range(max_variables):
        index += 1
        partitions[index] = (ActionType.VARIABLE, i)
    return partitions

def make_observation_space_and_action_space(config, for_agent):
    assert not config["state_space"]["include_steps_in_obs_space"], "Currently doesn't support 'include_steps_in_obs_space'"
    action_space = Discrete(len(
        action_space_partitions(
            domain, 
            config["state_space"]["max_variables"],
            for_agent)))
    observation_space = \
        MicroworldEnv.make_observation_space(
            config["state_space"]["embed_dim"],
            None if not config["state_space"]["include_steps_in_obs_space"] else \
                config["state_space"]["max_steps"], # TODO include max_steps in obs space after adding support for it
            config["state_space"]["max_variables"],
            config["state_space"]["max_utterances"],
            config["state_space"]["max_command_length"],
            action_space.n)
    return observation_space, action_space

if __name__ == "__main__":
    # TODO make the config a command-line arg
    config = DEFAULT_CONFIG

    domain = load_domain(config["domain"])
    init_policy_server(config)
