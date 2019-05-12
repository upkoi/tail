#!/usr/bin/env python3
import os
from flask import Flask, request, jsonify
import numpy as np
import json
from skypond.games.four_keys.four_keys_actions import FourKeysActions

app = Flask(__name__)

@app.route('/react',methods=['POST'])
def react():
    actions = [FourKeysActions.UP,FourKeysActions.DOWN,FourKeysActions.LEFT,FourKeysActions.RIGHT,FourKeysActions.ATTACK,FourKeysActions.NOTHING]

    # Randomly (weighted) pick an action out of the above
    action_probabilities = [0.2,0.2,0.2,0.2,0.15,0.05]
    action = np.random.choice(actions, 1, p=action_probabilities)
    return jsonify(int(np.squeeze(action)))

@app.route('/information',methods=['GET'])
def information():
    directory = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(directory,'info.json'), 'r') as file:
        information = file.read().replace('\n', '')
        return information

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
