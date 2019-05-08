import os
from flask import Flask, request, jsonify
from skypond.games.four_keys.four_keys_actions import FourKeysActions

app = Flask(__name__)

@app.route('/react',methods=['POST'])
def react():
    return jsonify(FourKeysActions.NOTHING)

@app.route('/information',methods=['GET'])
def information():
    directory = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(directory,'info.json'), 'r') as file:
        information = file.read().replace('\n', '')
        return information

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
