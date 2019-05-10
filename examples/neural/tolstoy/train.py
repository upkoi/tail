import os
import gym
import time
import datetime
import torch
import torch_ac
import sys
import math
import numpy as np

import skypond
from skypond.games.base.multi_agent_coordinator import MultiAgentCoordinator
from skypond.games.four_keys.agents.random_agent import RandomAgent
from gym.envs.registration import register

from model import FourKeysAgentModel
from sparklines import sparklines

WORKERS = 16
TRAINING_FRAMES = 1000000
ENVIRONMENT = 'FourKeys-v1'
MODEL_PATH = 'model.pt'
CLEAR_ON_LOG = True # If the screen should be cleared at each log line
RETURN_GRAPH_HEIGHT = 5 # The height of the average return graph in lines
FULL_EVALUATION_STEPS = 10 # The number of steps between full evaluations (on large game board)
FULL_EVALUATION_RENDER = True # If the full evaluation should be visualized

# Game Configuration
# Smaller and less-dense environments with fewer agents are easier to learn on
SIDE_LENGTH = 10
SEED_WALLS = 4
WALL_GROWTH_FACTOR = 3
RANDOM_AGENTS = 1

register(
    id=ENVIRONMENT,
    entry_point='skypond.games.base.multi_agent_coordinator:MultiAgentCoordinator',
)

def add_agents(coordinator):
    for i in range(RANDOM_AGENTS):
        coordinator.add_agent(RandomAgent('Random Agent [%i]' % i))

def configure_board(coordinator):
    coordinator.shared_state_initialization = dict(side_length=SIDE_LENGTH,num_seed_walls=SEED_WALLS,wall_growth_factor=WALL_GROWTH_FACTOR)

envs = []

for i in range(WORKERS):
    env = gym.make(ENVIRONMENT)
    env.seed(42*i)

    add_agents(env)
    env.on_reset = add_agents
    env.before_reset = configure_board

    envs.append(env)

try:
    model = torch.load(MODEL_PATH)
    model.eval()
    print('Loaded Model (%s)' % MODEL_PATH)
except:
    model = FourKeysAgentModel(envs[0].action_space)
    print('New Model Created')

observation_preprocessor = model.get_observation_preprocessor()
algo = torch_ac.PPOAlgo(envs, model, preprocess_obss=observation_preprocessor)

def full_evaluation(model,visualize=False,evaluation_opponents=3,rounds=1):
    env = gym.make(ENVIRONMENT)
    env.seed(42)

    def eval_add_agents(coordinator):
        for i in range(evaluation_opponents):
            coordinator.add_agent(RandomAgent('Random Agent [%i]' % i))

    def eval_configure_board(coordinator):
        coordinator.shared_state_initialization = dict(side_length=15,num_seed_walls=6,wall_growth_factor=4)

    eval_add_agents(env)
    env.on_reset = eval_add_agents
    env.before_reset = eval_configure_board

    rewards = []

    keys_held = 0
    pickups = 0

    for i in range(rounds):
        observation = env.reset()
        done = False

        cumulative_reward = 0

        while not done:

            memory_blank = torch.tensor([np.zeros(128)])

            input = observation_preprocessor([observation])

            dist, _, memories = model(input,memory_blank)

            action = np.squeeze(dist.sample())

            observation, reward, done, _ = env.step(action.item())
            cumulative_reward += reward

            if visualize:
                env.render(label='\33[90mLegend: K = Key, 1 = Current Agent, [2-8] = Practice Opponents\033[0m')

        meta = env.get_agent_meta(0)
        pickups += meta['pickups']
        keys_held += meta['keys']
        rewards.append(cumulative_reward)

    return round(keys_held/rounds,2), round(pickups/rounds,2), np.mean(rewards)

def display_training_summary(average_return_per_episode,average_frames_per_episode,total_frames,fps):
    total_frames_display = "{:,}".format(total_frames)
    fps_display = "{:,}".format(round(fps))
    latest_average_return = round(average_return_per_episode[-1],2)
    latest_average_frames = average_frames_per_episode[-1]
    return_lines = sparklines(average_return_per_episode[-80:],num_lines=RETURN_GRAPH_HEIGHT)

    if CLEAR_ON_LOG:
        os.system('cls' if os.name=='nt' else 'clear')

    print('%s Frames | %s FPS | \33[7m %.2f Avg Episode Return \033[0m | %i Avg Frames / Episode' % (total_frames_display, fps_display, latest_average_return, latest_average_frames))

    print('\33[90m')
    print('Average Return')
    for line in return_lines:
        print(line)
    print('\033[0m')

total_frames = 0
total_updates = 0

average_return_per_episode = []
average_frames_per_episode = []
full_evaluation_reward = []
fps = 0

print('Training...')

while total_frames < TRAINING_FRAMES:
    total_updates += 1

    start = time.time()
    experiences, logs = algo.collect_experiences()
    algo.update_parameters(experiences)
    end = time.time()

    processed_frames = logs["num_frames"]
    process_duration_seconds = (end - start)
    fps = processed_frames/process_duration_seconds
    total_frames += processed_frames

    average_return_per_episode.append(np.mean(logs['return_per_episode']))
    average_frames_per_episode.append(np.mean(logs['num_frames_per_episode']))

    display_training_summary(average_return_per_episode,average_frames_per_episode,total_frames,fps)

    if total_updates % FULL_EVALUATION_STEPS == 0:
        keys,pickups,reward = full_evaluation(model,visualize=FULL_EVALUATION_RENDER)

    if total_updates % 10 == 0:
        torch.save(model, MODEL_PATH)
