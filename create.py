'''
     _________  ________  ___  ___
    |\___   ___\\   __  \|\  \|\  \
    \|___ \  \_\ \  \|\  \ \  \ \  \
         \ \  \ \ \   __  \ \  \ \  \
          \ \  \ \ \  \ \  \ \  \ \  \____
           \ \__\ \ \__\ \__\ \__\ \_______\
            \|__|  \|__|\|__|\|__|\|_______|

    Tampa AI League New Agent Creation Tool
    https://midnightfight.ai
    Copyright 2019 Rob Venables

'''

import argparse
import json
import os
import random
import string
import shutil
import tempfile
import time

from qualification.output import pass_check, fail_check, warn_check

parser = argparse.ArgumentParser(description='T[AI]L Agent Creation Tool')

parser.add_argument("--template", required=False, help="template to use to create agent")
parser.add_argument("--ls", action='store_true',required=False, help="list available templates")

args = parser.parse_args()

try:
    from profanity import profanity
except:
    fail_check('Profanity library missing. Please install this library with pip install profanity.')

from qualification.core import check_name,copytree,sanity_check_address

templates = []
template_info = {}

def has_handler(folder):
    handler_path = os.path.join(folder,'handler.py')
    return os.path.isfile(handler_path)

for subdir, dirs, files in os.walk('examples'):
    if has_handler(subdir):
        template_name = subdir[len('examples/'):]
        templates.append(template_name)

        info_path = os.path.join('examples',template_name,'info.json')

        if os.path.isfile(info_path):
            with open(info_path, "r") as info_file:
                info = json.load(info_file)
                template_info[template_name] = info

if args.ls:
    print('Available Templates (use --template to specify):\n')

    for template_name in templates:

        info = {}
        info_path = os.path.join('examples',template_name,'info.json')
        with open(info_path, "r") as info_file:
            info = json.load(info_file)
            template_info[template_name] = info

        print('%s [%s]' % (template_name,info['description']))

    exit()

if not args.template and not args.ls:
    parser.error('Template is required. Use --ls for a list of templates.')

if args.template not in templates:
    parser.error('Specify an existing template. Use --ls for a list of templates.')

try:
    input = raw_input
except NameError:
    pass

valid_name = False
name = ''

template = args.template
template_path = os.path.join('examples',template)

while not valid_name:
    print('Select a name for the new agent.')
    print('This will be used for the starting agent display name as well as the directory name.')
    print('[Lowercase Only, <12 Characters, No Spaces]')
    name = input('Name: ')
    valid_name,error = check_name(name)

    if not valid_name:
        warn_check(error)

pass_check('Name [%s] Accepted' % name)

ethereum_input_complete = False
ethereum_address = ''

while not ethereum_input_complete:
    print('Enter your ethereum address.')
    print('This is used to transfer funds to your agent if you win. Please [Enter] to skip.')
    print('New Wallet Suggestions: https://www.myetherwallet.com or https://gemini.com/. See docs for more.')
    ethereum_address = input('Ethereum Address: ')

    if ethereum_address == '':
        warn_check('Ethereum address skipped. Your agent will not qualify for a prize. To qualify for prizes, please update your agent info.json to include a valid ethereum address.')
        ethereum_input_complete = True
        break

    appears_valid = sanity_check_address(ethereum_address)

    if not appears_valid:
        warn_check('Ethereum address did not pass validation. Please supply a valid ethereum address (matching ^0x[a-fA-F0-9]{40}$) or remove the address entirely.')
    else:
        pass_check('Agent Ethereum Address [%s] Passes Format Validation' % ethereum_address)
        ethereum_input_complete = True

try:
    os.mkdir(name)
except OSError:
    fail_check("Creation of agent directory %s failed" % name)

copytree(template_path, name)

info = template_info[template]
info['username'] = name
info['eth_address'] = ethereum_address

import json
with open(os.path.join(name,'info.json'), 'w') as outfile:
    json.dump(info, outfile)

pass_check('Agent %s Created (/%s)' % (name,name))

print('------------------------------------------------------------')

if info['type'] == 'neural':
    print('Nice! The next step is train your example neural network agent.')
    print('cd %s; python3 train.py' % name)

if info['type'] == 'conventional/random':
    print('Your random agent is a good starting point but will need some modification to qualify.')

if info['type'] == 'conventional':
    print('The conventional agent you selected is a good starting point.')
    print('Use the built-in visualization feature in this example to quickly evaluate changes without re-qualifying.')
    print('python3 %s/handler.py --test' % name)

if info['type'] == 'foundation':
    print('The foundation agent you selected is a great blank slate. See comments in handler.py file for next steps.')

print('------------------------------------------------------------')

print('Tip: Check your progress at any time by running the qualification tool.')
print('(Ex: python3 qualify.py --agent %s --visualize)' % name)
