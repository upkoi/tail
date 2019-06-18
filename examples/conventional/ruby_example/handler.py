#!/usr/bin/env python3
import os
from flask import Flask, request, jsonify
import json
from skypond.games.four_keys.four_keys_actions import FourKeysActions
import sys
from Naked.toolshed.shell import muterun_rb

app = Flask(__name__)


@app.route('/react', methods=['POST'])
def react():
    observation = str(request.get_json())
    response = muterun_rb('logic.rb', observation)

    if response.exitcode == 0:
        print(response.stdout.decode("utf-8").rstrip())
    else:
        print(response.stderr.decode("utf-8").rstrip())

    return jsonify(response.stdout.decode("utf-8").rstrip())


@app.route('/information', methods=['GET'])
def information():
    directory = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(directory, 'info.json'), 'r') as file:
        information = file.read().replace('\n', '')
        return information


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
