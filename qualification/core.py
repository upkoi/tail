import os
import random
import string
import shutil
from profanity import profanity

# Reserved names that will fail the name check
error_names = ['self_test','pathfinder','pacifist']

def check_name(name):
    if name == None or name == '':
        return False, 'Agent name not found. Please configure an agent name that is at least two characters long.'

    if len(name) < 2:
        return False, 'Agent name too short. Please select an agent name that is between two and twelve characters long.'

    if len(name) > 12:
        return False, 'Agent name too long. Please select an agent name that is between two and twelve characters long.'

    if name.translate({ord(c): None for c in string.whitespace}) != name:
        return False, 'Agent name must not contain whitespace or newline characters.'

    if name.lower() != name:
        return False, 'Agent name must be lowercase. Please change your agent name to all lowercase characters.'

    if name in error_names:
        return False, 'Agent name, "%s", is one of several reserved names. Please customize your agent name.' % name

    if profanity.contains_profanity(name):
        return False, 'Agent name appears to be overtly offensive. Please use a more creative name.'

    return True,''

def copytree(src, dst, symlinks=False, ignore=None):

    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)

        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)
