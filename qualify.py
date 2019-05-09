'''
     _________  ________  ___  ___
    |\___   ___\\   __  \|\  \|\  \
    \|___ \  \_\ \  \|\  \ \  \ \  \
         \ \  \ \ \   __  \ \  \ \  \
          \ \  \ \ \  \ \  \ \  \ \  \____
           \ \__\ \ \__\ \__\ \__\ \_______\
            \|__|  \|__|\|__|\|__|\|_______|

    Tampa AI League Official Qualification Tool
    https://midnightfight.ai
    Copyright 2019 Rob Venables

'''

from skypond.games.base.multi_agent_coordinator import MultiAgentCoordinator
from skypond.games.four_keys.agents.random_agent import RandomAgent
from skypond.games.four_keys.agents.random_accumulating_agent import RandomAccumulatingAgent

from qualification.output import pass_check, fail_check, warn_check

import argparse
import json
import os
import random
import string
import shutil
import tempfile
import time

parser = argparse.ArgumentParser(description='T[AI]L Submission Qualification Tool')

parser.add_argument("--agent", required=False, help="directory to load agent from (required if not running self-test)")
parser.add_argument("--unrestrict-networking", required=False, action='store_true', help="relax networking restrictions to simplify debugging")
parser.add_argument("--self-test", required=False, action='store_true', help="runs a simple single agent self-test of the execution environment by loading a known agent")
parser.add_argument("--game", required=False, default='four_keys', help="the game identifier (default is four_keys)")
parser.add_argument("--visualize", required=False, action='store_true', help="simple visualization of agent on qualification rounds")
parser.add_argument("--visualization-delay", required=False, default=0.01, type=float, help="controls the speed of the visualization by adding a delay after each agent turn. Increase delay to slow down visualization.")
parser.add_argument("--seed", required=False, default=42, help="seed to use for some of randomization behavior (not applied to docker agents)")
parser.add_argument("--round", required=False, default=None, help="target a specific qualification round by code")
parser.add_argument("--round-ls", required=False, action='store_true', help="list all qualification rounds (codes and names)")
parser.add_argument("--use-accumulating-opponents", required=False, action='store_true', help="controls random action opponent drop behavior (set to true to have random agents hold keys)")
parser.add_argument("--output", required=False, default=None, help="specify a target path to write the qualified submission")
parser.add_argument("--verify", required=False, default=None, help="specify a target path to a qualified submission to verify it would be accepted. Includes checking files, running agent, and verifying qualification token.")

args = parser.parse_args()

try:
    import docker
except:
    fail_check('Docker / pydocker not installed. Please install docker (https://docs.docker.com/install/) and then install the python docker API with pip install docker.')

try:
    import gym
except:
    fail_check('OpenAI gym missing. Please install this library with pip install gym.')

try:
    from profanity import profanity
except:
    fail_check('Profanity library missing. Please install this library with pip install profanity.')

try:
    import numpy as np
except:
    fail_check('Numpy library missing. Please install this library with pip install numpy.')

try:
    from tqdm import tqdm, trange
except:
    fail_check('tqdm library missing. Please install this library with pip install tqdm.')


from qualification.core import check_name, copytree, sanity_check_address

SELF_TEST_AGENT = os.path.join('tests','test_agent')

# Note that this does not make the entire game and qualification experience deterministic
# There are still areas - like docker instances - that do not yet receive the same seed

np.random.seed(args.seed)
random.seed(args.seed)

def check_environment():

    print('Checking Host Platform...')
    if os.name == 'nt':
        warn_check('It appears that you are running an operating system that the tool has not been tested on.')

    # Quick docker test
    print('Checking Docker API...')
    id = None
    try:
        client = docker.from_env()
        info = client.info()
        id = info['ID']
    except:
        fail_check('Failed to connect to docker client. Please make sure that docker and the docker API are installed correctly and that the current user has permission to interact with docker.')

    if id is None or id == '':
        warn_check('Unable to find docker engine ID. This might indicate an issue interacting with the docker API environment. Make sure the python docker API is installed correctly.')

def get_size(start_path = '.'):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size

def validate_agent_is_directory(directory):
    is_directory = os.path.isdir(directory)

    if is_directory:
        pass_check('Agent Path is Directory')
    else:
        fail_check('Agent Path Not Directory (please pass directory to --agent)')

def validate_agent_handler(directory):
    file_path = os.path.join(directory,'handler.py')
    exists = os.path.isfile(file_path)

    if exists:
        pass_check('Required Agent Handler Found')
    else:
        fail_check('Agent Handler Not Found (please add handler.py to agent directory)')

def validate_agent_size(directory):
    threshold = 1440000
    size = get_size(directory)

    if size < threshold:
        pass_check('Agent Size OK (%s Bytes)' % "{:,}".format(size))
    else:
        fail_check('Agent Too Large (%s Bytes, Threshold: %s Bytes, Overage: %s Bytes)' % ("{:,}".format(size),"{:,}".format(threshold),"{:,}".format(size-threshold)))

def get_verification_path(directory):
    return os.path.join(directory,'qualification.dat')

def check_agent_meta(coordinator):
    status = coordinator.get_agent_meta(0)

    name = status['name']

    name_ok,name_issue = check_name(name)

    if not name_ok:
        fail_check(name_issue)

    pass_check('Agent Name [%s] Passes Minimum Qualifications' % name)

    address = status['address']

    if address == None or address == '':
        warn_check('Ethereum address is missing. Your agent will not qualify for a prize. To qualify for prizes, please update your agent to include a valid ethereum address.')
    else:
        appears_valid = sanity_check_address(address)

        if not appears_valid:
            fail_check('Ethereum address did not pass the format check. Please supply a valid ethereum address matching ^0x[a-fA-F0-9]{40}$ or remove the address entirely.')
        else:
            pass_check('Agent Ethereum Address [%s] Passes Format Validation' % address)

    if status['pic'] == None or status['pic'] == '':
        warn_check('No usable e-mail address was provided. Your bot will not feature a gravatar. Provide an e-mail address to load a gravatar during the competition.')
    else:
        pass_check('Gravatar [%s] Loaded From E-Mail Address Supplied' % status['pic'])

def load_qualification_config(game):

    dir_path = os.path.dirname(os.path.realpath(__file__))

    qualification_detail_path = os.path.join(dir_path,'qualification',game,'qualification.json')

    qualification_rounds = []

    try:
        with open(qualification_detail_path) as file:
            qualification_rounds = json.load(file)
    except:
        fail_check('Unable to load qualification data. Please verify qualification configuration file exists at %s' % qualification_detail_path)

    return qualification_rounds

def qualify(coordinator,current_round,agent_path,cutoff=1000,trials=15,visualize=False,visualization_delay=False):

    coordinator.shared_state_initialization = current_round['shared_config']

    with tempfile.TemporaryDirectory() as temp_path:

        wins = 0
        score = current_round['passing_score']

        steps_to_finish = []

        t = trange(trials, desc=str(score) + " Score / " + str(wins) + " Wins")
        for trial in t:

            coordinator.start_new_game()

            try:
                # Reload agent without reloading docker instance
                coordinator.add_isolated_agent(args.agent,staging_path=temp_path,reuse_loaded_instance=True)
            except:
                fail_check('Failed to add agent. Check handler for syntax errors. Also, check your docker configuration or try --unrestrict-networking')

            for i in range(current_round['random_agents']):

                if args.use_accumulating_opponents:
                    coordinator.add_agent(RandomAccumulatingAgent('Random Acc Agent [%i]' % i))
                else:
                    coordinator.add_agent(RandomAgent('Random Agent [%i]' % i))

            agent_env_steps = 0

            while not coordinator.shared_state.any_agent_won:

                keys = coordinator.environments[0].keys
                pickups = coordinator.environments[0].status['pickups']
                attacks = coordinator.environments[0].status['attacks']

                label = '%s\nTrial %i/%i, Step %i\nScore %s [Maximum to Pass: %s]\n%i Keys, %i Attacks, %i Pickups' %(current_round['name'],trial+1,trials,agent_env_steps, score,current_round['passing_score'],keys,attacks, pickups)

                coordinator.process_turn(visualize,visualization_label=label)

                if visualize:
                    time.sleep(visualization_delay)

                agent_env_steps = coordinator.environments[0].total_steps

                if agent_env_steps > cutoff:
                    break;

            trial_steps = coordinator.environments[0].total_steps
            steps_to_finish.append(trial_steps)

            score = round(np.mean(steps_to_finish),2)

            won = coordinator.environments[0].keys
            if won:
                wins += 1

            t.set_description(str(score) + " Score [Below " + str(current_round['passing_score']) +" to Pass] / " + str(wins) + " Total Wins")

        ok = score <= current_round['passing_score']
        return ok,score

qualification_rounds = load_qualification_config(args.game)

if args.output:
    if not os.path.isdir(args.output):
        fail_check('Specified output path is not a directory. Please specify a writable directory for output.')
    else:
        if len(os.listdir(args.output) ) != 0:
            fail_check('Specified output path contains existing files. Please specify blank target directory.')

if args.round_ls:

    print('Available Qualification Rounds\n(use --round to target individual round, ex: --round=%s)' % qualification_rounds[0]['code'])

    for round in qualification_rounds:
        print(round['code'] + ': ' + round['name'])

    exit()

if not args.self_test and not args.agent and not args.verify:
    parser.error('Agent directory is required. Use --agent to specify.')

print('Checking Environment & Prerequisites...')
check_environment()

# Run a self-test of the current platform
if args.self_test:

    print('Running Self-Test of Execution Environment...')

    coordinator = None

    try:
        coordinator = MultiAgentCoordinator(args.game,gym_compatibility=False)
        coordinator.seed(args.seed)
        pass_check('Agent Coordinator Loaded Successfully')
    except:
        fail_check('Failed to start MultiAgentCoordinator. Try pulling down a different (newer or previous) version of TAIL.')

    if args.unrestrict_networking:
        warn_check('Network Restrictions Relaxed - Environment Has Network Connectivity (Unlike Competition Environment)')
        coordinator.restrict_network = False


    file_path = os.path.join(SELF_TEST_AGENT,'handler.py')
    exists = os.path.isfile(file_path)

    if not exists:
        fail_check('Self-Test Agent Handler Not Found (Looking at %s)' % file_path)

    with tempfile.TemporaryDirectory() as temp_path:
        try:
            print('Trying To Add Isolated Agent (This May Take a Few Seconds)...')
            coordinator.add_isolated_agent(SELF_TEST_AGENT,staging_path=temp_path)
        except:
            fail_check('Failed to add agent. Check your docker configuration or try --unrestrict-networking')

        try:
            status = coordinator.get_agent_meta(0)

            if status['name'] != 'self_test':
                fail_check('Failed to verify reference agent name. This could indicate a problem with your execution environment version.')

            if status['address'] == '':
                fail_check('Failed to find ETH destination address. This could indicate a problem with your execution environment version.')

            if status['pic'] == '':
                warn_check('Failed to find photo. This could indicate a problem with your execution environment version.')

            pass_check('Reference Agent Started Successfully')

            try:
                coordinator.process_turn()
                pass_check('Agent Turn Cycled Without Exception')

            except:
                fail_check('Failed to get cycle agent turn. This could indicate a problem with your execution environment version.')

            pass_check('Execution Environment Self-Test Passed')
        except:
            fail_check('Failed to get reference agent. Check your docker configuration or try --unrestrict-networking')

    exit()

# Verify existing qualified submission
if args.verify:
    if not os.path.isdir(args.verify):
        fail_check('Specified verify path is not a directory. Please specify a readable directory for verification.')

    token_path = get_verification_path(args.verify)
    if not os.path.isfile(token_path):
        fail_check('Unable to find qualification token. The verification tool is intended to be used on qualified submissions only. Try qualifying your submission first and specify --output to save your qualified submission.')

    token = ''

    with open(token_path, 'r') as file:
        token = file.read()

    if not token:
        fail_check('Unable to read qualification token (possibly empty, invalid, or unreadable). Try re-qualifying your submission.')

    print('Starting Game Execution Environment for Verification...')
    coordinator = MultiAgentCoordinator('four_keys',gym_compatibility=False)

    print('[TAIL] Verifying Agent Prior to Load...')
    validate_agent_is_directory(args.verify)
    validate_agent_size(args.verify)
    validate_agent_handler(args.verify)

    agent = None

    print('[TAIL] Launching Agent for Verification (This May Take a Few Seconds)...')
    with tempfile.TemporaryDirectory() as temp_path:
        try:
            agent = coordinator.add_isolated_agent(args.verify,staging_path=temp_path)
        except:
            fail_check('Failed to add agent. Check your docker configuration or try --unrestrict-networking')

        print('[TAIL] Verifying Agent Information...')
        check_agent_meta(coordinator)

        generated_token = coordinator.get_agent_verification_code(agent)

        if generated_token == token:
            pass_check('Qualification Verified (Token Matches). Ready for Competition.')
        else:
            fail_check('Verification token is invalid. This submission cannot be validated (it might have been generated with an older version or you may have changed the name). Please qualify your submission again before submitting.')

        exit()

with tempfile.TemporaryDirectory() as temp_path:

    print('Starting Game Execution Environment...')
    coordinator = MultiAgentCoordinator('four_keys',gym_compatibility=False)

    if args.unrestrict_networking:
        warn_check('Network Restrictions Relaxed. Environment Has Network Connectivity (Unlike Competition)')
        coordinator.restrict_network = False

    print('Verifying Agent Prior to Load...')
    validate_agent_is_directory(args.agent)
    validate_agent_size(args.agent)
    validate_agent_handler(args.agent)

    agent = None

    print('Launching Agent (This May Take a Few Seconds)...')
    try:
        agent = coordinator.add_isolated_agent(args.agent,staging_path=temp_path)
    except:
        fail_check('Failed to add agent. Check handler for syntax errors and check your docker configuration. If problem persists try --unrestrict-networking')

    print('Verifying Agent Information...')
    check_agent_meta(coordinator)

    current_round = 1
    max_rounds = len(qualification_rounds)

    if not args.output:
        warn_check('No Output Path Supplied. Qualification Token Will Not Be Written.')
        warn_check('Reminder: You need a self-qualification token to enter the competition. Supply an output path to save your prepared submission (with token).')

    print('Qualification Starting. Lower Scores Are Better.')
    for round_detail in qualification_rounds:

        if args.round is not None:
            if round_detail['code'] != args.round:
                continue

        is_final = current_round == len(qualification_rounds)

        print('Starting Qualification Round %i/%i [%s]...' % (current_round,max_rounds,round_detail['name']))
        ok,score = qualify(coordinator,round_detail,args.agent,visualize=args.visualize,visualization_delay=args.visualization_delay)

        if not ok:
            fail_check('Qualification Round %i/%i [%s] Below Goal. Try Improving Your Agent & Qualify Again! :)' % (current_round,max_rounds,round_detail['name']))

        if args.round is not None:
            print('Targeted Qualification Complete - Please Re-Run Full Qualification')

        if is_final:

            if not args.output:
                print('Submission Would Likely Qualify')
                warn_check('No Output Path Supplied. Qualification Token Will Not Be Written.')
                warn_check('Reminder: You need a self-qualification token to enter the competition. Supply an output path with --output and rerun qualification.')
            else:

                copytree(args.agent, args.output)

                token_path = get_verification_path(args.output)
                generated_token = coordinator.get_agent_verification_code(agent)

                with open(token_path, "w") as token_file:
                    token_file.write(generated_token)

                pass_check('Qualification Complete - Submission Ready for Battle')
                print('Congratulations on Passing - Sign up for the next Competition!')
                print('Visit https://midnightfight.ai')

        current_round += 1
