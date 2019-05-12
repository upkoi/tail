#!/usr/bin/env python3
import os
import sys
from flask import Flask, request, jsonify
import random
import numpy as np
import json
import math
import skypond
import operator
from skypond.games.four_keys.four_keys_actions import FourKeysActions
from skypond.games.four_keys.four_keys_board_items import FourKeysBoardItems

app = Flask(__name__)

FRAME_SIDE_SIZE = 7
TOTAL_ACTIONS = len(FourKeysActions)
MAX_BREADCRUMB_VALUE = 20

test_mode = False

# Runs a self-contained test instead of serving - see below
if '--test' in sys.argv:
    test_mode = True

def get_action_for_smallest_breadcrumb(breadcrumbs,board,coordinate):
    directions = [(-1,0),(1,0),(0,-1),(0,1)]
    actions = [FourKeysActions.UP,FourKeysActions.DOWN,FourKeysActions.LEFT,FourKeysActions.RIGHT]

    max_offset = breadcrumbs.shape[0]-1
    action_breadcrumb_values = np.array([0,0,0,0],dtype='float')

    candidate_index = 0
    for direction in directions:
        candidate = tuple(map(operator.add, coordinate, direction))

        if candidate[0] < 0 or candidate[0] > max_offset or candidate[1] < 0 or candidate[1] > max_offset:
            candidate_index += 1
            continue

        tile = board[candidate[0]][candidate[1]]

        if tile == FourKeysBoardItems.EMPTY:
            # Note: the +10 ensures that the probability below will always be > 0 for fully saturated tiles
            breadcrumb_weighting = 4
            breadcrumb_value = breadcrumbs[candidate[0]][candidate[1]]*breadcrumb_weighting
            action_breadcrumb_values[candidate_index] = min(breadcrumb_value,20) / (MAX_BREADCRUMB_VALUE+10)

        else:
            # EX: wall or player - take movement in that direction out of options
            action_breadcrumb_values[candidate_index] = 1

        candidate_index += 1

    action_probabilities = (1 - action_breadcrumb_values)
    total_values = np.sum(action_probabilities)

    normalized_probabilities = action_probabilities / total_values

    action = np.random.choice(actions, 1, p=normalized_probabilities)
    return np.squeeze(action)

def get_allowable_movements(board,coordinate):
    directions = [(-1,0),(1,0),(0,-1),(0,1)]
    actions = [FourKeysActions.UP,FourKeysActions.DOWN,FourKeysActions.LEFT,FourKeysActions.RIGHT]

    allowed_coordinates = []
    action_map = []

    max_offset = board.shape[0]-1
    candidate_index = 0

    for direction in directions:
        candidate = tuple(map(operator.add, coordinate, direction))

        if candidate[0] < 0 or candidate[0] > max_offset or candidate[1] < 0 or candidate[1] > max_offset:
            candidate_index += 1
            continue

        tile = board[candidate[0]][candidate[1]]

        if tile == FourKeysBoardItems.EMPTY or tile == FourKeysBoardItems.KEY:
            allowed_coordinates.append(candidate)
            action_map.append(actions[candidate_index])

        candidate_index += 1

    return allowed_coordinates, action_map

def explore_path_bfs(board,mask,point,distance,destination):

    queue = []
    queue.append(point)

    while queue:

        point = queue.pop(0)
        reachable_points,_ = get_allowable_movements(board,point)
        distance = mask[point[0],point[1]] + 1

        for new_point in reachable_points:

            if new_point == destination:
                return True

            mask_value = mask[new_point[0],new_point[1]]

            if mask_value == 999:
                # Unexplored
                mask[new_point[0],new_point[1]] = distance
                queue.append(new_point)


# Builds a path planning mask indicating possible routes
def build_path_mask(board,destination,current_location):
    side_size = board.shape[0]
    mask = np.full((side_size,side_size),999)
    mask[destination[0],destination[1]] = 0
    mask[current_location[0],current_location[1]] = 99
    explore_path_bfs(board,mask,destination,1,current_location)
    return mask

# Returns the coordinate with the smallest mask value
def get_shortest_path_action(board,mask,coordinate):
    reachable_points,actions = get_allowable_movements(board,coordinate)

    shortest_path = 999
    shortest_action = None

    for i in range(len(reachable_points)):
        point = reachable_points[i]
        mask_value = mask[point[0],point[1]]

        if mask_value < shortest_path:

            shortest_action = actions[i]
            shortest_path = mask_value

    return shortest_action,shortest_path

def get_action(observation):

        board_section = FRAME_SIDE_SIZE**2
        board = observation[0:board_section]

        position = (3,3)

        square_board = board.reshape((FRAME_SIDE_SIZE,FRAME_SIDE_SIZE))
        breadcrumbs = observation[-board_section-5:-5]
        square_breadcrumbs = breadcrumbs.reshape((FRAME_SIDE_SIZE,FRAME_SIDE_SIZE))
        current_breadcrumb = square_breadcrumbs[position[0],position[1]]

        keys = []

        closest_key_action = -1
        closest_key_distance = -1
        closest_key_index = -1

        # Find closest key (if exists)
        for x in range(square_board.shape[1]):
            for y in range(square_board.shape[0]):
                if square_board[y][x] == FourKeysBoardItems.KEY:

                    keys.append((y,x))
                    key_index = len(keys)-1

                    mask = build_path_mask(square_board,keys[key_index],position)
                    action,distance = get_shortest_path_action(square_board,mask,position)

                    if distance < 999 and (distance < closest_key_distance or closest_key_distance == -1):
                        closest_key_index = key_index
                        closest_key_distance = distance
                        closest_key_action = action
                        last_path_mask = mask # Helpful to explain behavior

        if closest_key_index != -1:
            return closest_key_action
        else:
            # No keys found, stochastically step towards least explored area
            action = get_action_for_smallest_breadcrumb(square_breadcrumbs,square_board,position)
            return int(np.squeeze(action))

if test_mode:
    from skypond.games.base.multi_agent_coordinator import MultiAgentCoordinator
    from skypond.games.base.callback_agent import CallbackAgent
    from skypond.games.four_keys.agents.random_agent import RandomAgent
    import time

    for i in range(1000):

        coordinator = MultiAgentCoordinator('four_keys',gym_compatibility=False)
        coordinator.debug_messages = True
        coordinator.seed(42)

        coordinator.shared_state_initialization = dict(side_length=7,num_seed_walls=4,wall_growth_factor=2)

        coordinator.start_new_game()

        coordinator.add_agent(CallbackAgent(get_action))

        coordinator.add_agent(RandomAgent('Random Agent [%i]' % i))

        while not coordinator.shared_state.any_agent_won:

            coordinator.process_turn(True)
            time.sleep(0.01)

    exit()

@app.route('/react',methods=['POST'])
def react():

    observation = np.array(request.get_json())
    return jsonify(get_action(observation))

@app.route('/information',methods=['GET'])
def information():
    directory = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(directory,'info.json'), 'r') as file:
        information = file.read().replace('\n', '')
        return information

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
