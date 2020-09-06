from gym.spaces import Dict
from ray.rllib.models.preprocessors import DictFlatteningPreprocessor
from ray.rllib.models.torch.torch_modelv2 import TorchModelV2 as TorchModel
from ray.rllib.models.torch.fcnet import FullyConnectedNetwork
from ray.rllib.utils.numpy import LARGE_INTEGER
import torch.nn


class ValidActionsModel(TorchModel, torch.nn.Module):
    def __init__(self,
                 obs_space,
                 action_space,
                 num_outputs,
                 model_config,
                 name):
        super(ValidActionsModel, self).__init__(
            obs_space, action_space, num_outputs, model_config, name)
        torch.nn.Module.__init__(self)
        self.fcnet = FullyConnectedNetwork(
            obs_space,
            action_space,
            num_outputs,
            model_config,
            name='fcnet')

    def forward(self, input_dict, state, seq_lens):
        # Extract the available actions tensor from the observation.
        action_mask = input_dict["obs"]["action_mask"]

        # Compute what the model would do before masking
        input_dict['obs'] = input_dict['obs_flat']
        intent_vector, state = self.fcnet(input_dict)

        action_mask = torch.clamp(
            torch.log(action_mask), -float(LARGE_INTEGER), float("inf"))
        action_logits = intent_vector + action_mask

        return action_logits, state

    def value_function(self):
        return self.fcnet.value_function()
