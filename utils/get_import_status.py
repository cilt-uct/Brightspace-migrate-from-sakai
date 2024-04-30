import argparse
import os
import sys
import logging

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.config
import config.logging_config
from lib.d2l import web_login, get_import_history, get_first_import_status, get_first_import_job_log
from lib.local_auth import getAuth


def main():

    APP = config.config.APP

    parser = argparse.ArgumentParser(description="This script gets Brightspace import statuses",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-org_ids', help="comma seperated list of org ids")
    args = vars(parser.parse_args())

    if not args['org_ids']:
        raise Exception("Please specify -org_ids parameter")

    org_ids = args['org_ids'].replace(' ', '').split(',')

    WEB = getAuth('BrightspaceWeb', ['username', 'password'])
    if not WEB['valid']:
        raise Exception('Web Authentication required [BrightspaceWeb]')

    brightspace_url = APP['brightspace_url']
    logging.info(f"Checking import status for orgids {org_ids} on {brightspace_url}")

    url = f'{brightspace_url}/d2l/lp/auth/login/login.d2l'
    logging.info(f"Checking import status at {url} username {WEB['username']}")
    session = web_login(url, WEB['username'], WEB['password'])

    status_list = { }
    for org_id in org_ids:
        content = get_import_history(brightspace_url, org_id, session)
        status_list[org_id] = {
                'status': get_first_import_status(content),
                'job_id': get_first_import_job_log(content)
            }

    logging.info(f"Result: {status_list}")

if __name__ == '__main__':
    main()
