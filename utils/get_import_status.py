import requests
import re
import argparse
import os
import sys

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.config import *
from config.logging_config import *
from lib.utils import *
from lib.local_auth import *

def login(url, username, password):
    values = {
        'loginPath': '/d2l/login',
        'username': username,
        'password': password
    }

    session = requests.Session()
    session.post(url, data=values)
    return session


def get_org(brightspace_url, org_unit, session):
    url = f'{brightspace_url}/d2l/le/conversion/import/{org_unit}/history/display?ou={org_unit}'
    r = session.get(url)
    return r.text


def get_status(content):
    logging.debug(f"looking in {content}")

    pattern = re.compile('<d2l-status-indicator state="(.*?)" text="(.*?)"(.*?)>')
    return pattern.search(content).group(2)


def get_import_job_log(content):
    pattern = re.compile('<a class=(.*?) href=(.*?)logs/(.*?)/Display">View Import Log(.*?)')
    return pattern.search(content).group(3)


def main():

    global APP

    parser = argparse.ArgumentParser(description="This script gets Amathuba import statuses",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-org_ids', help="comma seperated list of org ids")
    args = vars(parser.parse_args())

    if not args['org_ids']:
        raise Exception("Please specify -org_ids parameter")

    org_ids = args['org_ids'].replace(' ', '').split(',')

    webAuth = getAuth('BrightspaceWeb')
    if (webAuth is not None):
        WEB = {'username': webAuth[0], 'password' : webAuth[1]}
    else:
        raise Exception(f'Web Authentication required [getBrightspaceWebAuth]')

    brightspace_url = APP['brightspace_url']
    logging.info(f"Checking import status for orgids {org_ids} on {brightspace_url}")

    url = f'{brightspace_url}/d2l/lp/auth/login/login.d2l'
    logging.info(f"Checking import status at {url} username {WEB['username']}")
    session = login(url, WEB['username'], WEB['password'])

    status_list = { }
    for org_id in org_ids:
        content = get_org(brightspace_url, org_id, session)
        status_list[org_id] = {
                'status': get_status(content),
                'job_id': get_import_job_log(content)
            }

    logging.info(f"Result: {status_list}")

if __name__ == '__main__':
    main()
