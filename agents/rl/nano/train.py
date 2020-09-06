import argparse
import logging
import os

import ray
import ray.rllib.agents.ppo as ppo
from ray.tune.logger import pretty_print
from ray.rllib.models import ModelCatalog
import torch

from env import NanoworldEnv

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true')
    parser.add_argument("--num_workers", type=int, default=1)
    parser.add_argument(
        "--num_gpus",
        type=int,
        default=torch.cuda.device_count())
    args = parser.parse_args()

    # Set up ray
    ray.init(local_mode=args.debug)
    # ModelCatalog.register_custom_model("model", ValidActionsModel) # todo:
    # what to use here ?

    # Set up training configs
    env = NanoworldEnv
    config = ppo.DEFAULT_CONFIG.copy()
    config["num_workers"] = args.num_workers
    config["num_gpus"] = args.num_gpus
    config["num_envs_per_worker"] = 1
    config["train_batch_size"] = 500
    config["use_pytorch"] = True
    config["multiagent"] = {
        "policies": {
            # the first tuple value is None -> uses default policy
            "driver": (None, env.driver_observation_space, env.driver_action_space, {}),
            "passenger": (None, env.passenger_observation_space, env.passenger_action_space, {}),
        },
        # todo: do we need this ? --> different policies for diferent agents
        "policy_mapping_fn": lambda agent_id: agent_id
    }

    config["output"] = "./nano_world"
    config["output_max_file_size"] = 5000000
    trainer = ppo.PPOTrainer(env=env, config=config)

    # Main training loop
    num_steps = 80
    for i in range(num_steps):
        result = trainer.train()
        print('step:', i)
        print('episode_len_mean', result['episode_len_mean'])
        print('episode_reward_mean', result['episode_reward_mean'])
        print('-------')
        # print(pretty_print(result))
