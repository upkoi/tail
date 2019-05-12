#!/usr/bin/env python3
import os
from flask import Flask, request, jsonify
import random
import numpy as np
import torch
import json
import math
import torch_ac
import skypond

app = Flask(__name__)

def load_model():
    base_path = os.path.dirname(os.path.abspath(__file__))
    model = torch.load(os.path.join(base_path,'model.pt'))
    model.eval()
    return model

model = load_model()
preprocess_observation = model.get_observation_preprocessor()

@app.route('/react',methods=['POST'])
def react():
    global model;

    try:
        observation = request.get_json()
        memory_blank = torch.tensor([np.zeros(128)])
        input = preprocess_observation([observation])
        dist, _, memories = model(input,memory_blank)
        action = np.squeeze(dist.sample())

        return jsonify(action.item())

    except Exception as e:
        return jsonify(e)

@app.route('/information',methods=['GET'])
def information():
    directory = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(directory,'info.json'), 'r') as file:
        information = file.read().replace('\n', '')
        return information

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
