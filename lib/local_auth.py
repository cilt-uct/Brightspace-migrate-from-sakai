#!/usr/bin/python3

import os
import subprocess

from jproperties import Properties
from pathlib import Path

def get_var(varname):
    base = Path(os.path.dirname(os.path.abspath(__file__))).parent / 'base.sh'

    CMD = f'echo $(source {base}; echo $%s)' % varname
    p = subprocess.Popen(CMD, stdout=subprocess.PIPE, shell=True, executable='/bin/bash')
    return p.stdout.readlines()[0].strip().decode("utf-8")

# Dictionary with metadata (.data, .meta)
AUTH_PROP = Properties()

with open(get_var('AUTH_PROPERTIES'), "rb") as f:
    AUTH_PROP.load(f, "utf-8")

# Dictionary without the optional metadata
AUTH = {k: v.data for k, v in AUTH_PROP.items()}

# return a tuple of the dictionary values for keys starting with name_
def getAuth(filter = 'none'):

    # We need to preserve key ordering
    filtered_auth = []
    for (k,v) in AUTH.items():
        if k.startswith(f"{filter}_"):
            filtered_auth.append(v)

    return filtered_auth

# return a tuple of the dictionary values for keys starting with name_
def getAuthDict(filter = 'none'):

    filtered_auth = {}
    for (k,v) in AUTH.items():
        prefix = f"{filter}_"
        if k.startswith(prefix):
            filtered_auth[k.replace(prefix,"")] = v

    return filtered_auth
