import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions.categorical import Categorical
import torch_ac
import numpy as np
from skypond.games.four_keys.four_keys_constants import HISTORY_QUEUE_LENGTH

# Observation input side length
# Eventuallly this will be refactored into a shared constant
SIDE_LENGTH = 7

# initialize_parameters method from...
# https://github.com/ikostrikov/pytorch-a2c-ppo-acktr/blob/master/model.py
# ...via https://github.com/lcswillems/rl-starter-files/blob/master/model.py
def initialize_parameters(m):
    classname = m.__class__.__name__
    if classname.find('Linear') != -1:
        m.weight.data.normal_(0, 1)
        m.weight.data *= 1 / torch.sqrt(m.weight.data.pow(2).sum(1, keepdim=True))
        if m.bias is not None:
            m.bias.data.fill_(0)

class FourKeysAgentModel(nn.Module, torch_ac.RecurrentACModel):
    def __init__(self, action_space):
        super().__init__()

        self.use_memory = False
        self.use_text = False

        observation_space = {"input": (SIDE_LENGTH,SIDE_LENGTH,2)}

        self.image_conv = nn.Sequential(
            nn.Conv2d(2, 32, (2, 2)),
            nn.ReLU(),
            nn.Conv2d(32, 32, (1, 1)),
            nn.MaxPool2d((2, 2)),
            nn.Conv2d(32, 32, (2, 2)),
            nn.ReLU(),
            nn.Conv2d(32, 128, (2, 2)),
            nn.ReLU()
        )
        n = observation_space["input"][0]
        m = observation_space["input"][1]

        self.embedding_size = ((n-1)//2-2)*((m-1)//2-2)*128

        self.actor = nn.Sequential(
            nn.Linear(self.embedding_size, 512),
            nn.Tanh(),
            nn.Linear(512, action_space.n)
        )

        self.critic = nn.Sequential(
            nn.Linear(self.embedding_size, 512),
            nn.Tanh(),
            nn.Linear(512, 1)
        )

        self.apply(initialize_parameters)

    @property
    def memory_size(self):
        return 2*self.embedding_size

    def forward(self, obs, memory):
        x = torch.transpose(torch.transpose(obs.input, 1, 3), 2, 3)
        x = self.image_conv(x)
        x = x.reshape(x.shape[0], -1)

        embedding = x

        x = self.actor(embedding)
        dist = Categorical(logits=F.log_softmax(x, dim=1))

        x = self.critic(embedding)
        value = x.squeeze(1)

        return dist, value, memory

    def get_observation_preprocessor(self):
        current_frame = 1
        breadcrumb_frames = 1
        
        def preprocess_observation(observation_set, device=None):

            selected_frame_stacks = []

            for observation in observation_set:

                frames = np.reshape(observation[:-5],(1+HISTORY_QUEUE_LENGTH+breadcrumb_frames,SIDE_LENGTH*SIDE_LENGTH))

                current_frame = np.reshape(frames[0],(SIDE_LENGTH,SIDE_LENGTH))

                current_frame[current_frame == 3] = 0
                current_frame[current_frame == 1] = 66
                current_frame[current_frame == 2] = 100
                current_frame[current_frame == 11] == 33

                current_frame = current_frame/100

                breadcrumbs = np.reshape(frames[-1],(SIDE_LENGTH,SIDE_LENGTH))/20

                selected_frame_stacks.append(np.stack((current_frame,breadcrumbs),axis=-1))

                input_array = np.array(selected_frame_stacks)
                input_tensor = torch.tensor(input_array, device='cpu', dtype=torch.float)

            return torch_ac.DictList({
                "input": input_tensor,
            })

        return preprocess_observation
