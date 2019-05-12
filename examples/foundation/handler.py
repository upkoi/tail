#!/usr/bin/env python3
import os
import sys
from flask import Flask, request, jsonify
import numpy as np
import json
import skypond
from skypond.games.four_keys.four_keys_actions import FourKeysActions
from skypond.games.four_keys.four_keys_board_items import FourKeysBoardItems

'''
    This agent is a quick starting point with all of the observation data
    already split out and labeled.
'''

app = Flask(__name__)

FRAME_SIDE_SIZE = 7
TOTAL_ACTIONS = len(FourKeysActions)
TOTAL_FRAMES = 6
MAX_BREADCRUMB_VALUE = 20

@app.route('/react',methods=['POST'])
def react():

    observation = np.array(request.get_json())
    frames = np.reshape(observation[:-5],(TOTAL_FRAMES,FRAME_SIDE_SIZE*FRAME_SIDE_SIZE))

    # This is the current state of the visible part of the board in 49 Tiles
    # - Every item in this frame is in FourKeysBoardItems
    # - Your agent is always centered in the frame (at index 3,3)
    # - The most helpful frame to use
    current_frame = frames[0]

    # These are the historical frames from earlier timesteps and are previous
    # copies of the current_frame that were provided to the agent. Note that the
    # historical frames are initialized with copies of the starting frame.
    frame_t_minus_one = frames[1]
    frame_t_minus_two = frames[2]
    frame_t_minus_three = frames[3]
    frame_t_minus_four = frames[4]

    # This provides information about how many times the agent has visited a
    # given location, tracking up to 20 visits per tile (values remain constant
    # at 20 after the 20th visit). See pathfinder example for an example of
    # semi-randomly selecting the next movement influenced by breadcrumb values.
    breadcrumbs = frames[5]

    # The supplement contains additional information about player state and location
    supplement = observation[-5:]

    # The X & Y coordinates indicate where your agent is on the the larger
    # board (your agent can only see a small window of this board and is centered
    # in the visible window)
    position_y = supplement[0]
    position_x = supplement[1]

    # The number of keys that your agent holds. When this gets to 4 you win the game.
    # Note that holding one or more keys opens up your agent for attack.
    keys_held = supplement[2]

    # Percent recharges for attacking and movement. These generally increase every turn.
    # Attack recharge starts at zero and takes many (~20) frames to charge.
    # Movement recharge starts full but is emptied if you are holding keys and an
    # opponent attacks you. Your agent will also lose a portion of attack recharge in
    # that case and will be unable to immediately counter-attack.
    attack_recharge = supplement[3]
    movement_recharge = supplement[4]
    can_attack = attack_recharge == 100
    can_move = movement_recharge == 100

    # ===============================================
    # ToDo: Add your code here
    # (Respond to the current state and set action
    # to one of the actions in FourKeysActions)
    action = FourKeysActions.NOTHING
    # ===============================================

    return jsonify(action)

@app.route('/information',methods=['GET'])
def information():
    directory = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(directory,'info.json'), 'r') as file:
        information = file.read().replace('\n', '')
        return information

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
