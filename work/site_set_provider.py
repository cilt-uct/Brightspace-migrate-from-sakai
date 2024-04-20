#!/usr/bin/python3
# -*- coding: iso-8859-15 -*-

## This script accesses a Sakai DB (config.py) and exports the rubrics of a site to a packaged zip file.
## REF: AMA-37

import sys
import os
import argparse
import re
import logging

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.logging_config
from lib.utils import get_site_providers
from lib.local_auth import getAuth
from lib.db import update_providers

def run(SITE_ID, APP, link_id):
    logging.info('Update site provider : {}'.format(SITE_ID))

    tmp = getAuth(APP['auth']['db'])
    if (tmp is not None):
        RUN_DB = {'host' : tmp[0], 'database': tmp[1], 'user': tmp[2], 'password' : tmp[3]}
    else:
        logging.error("Authentication required (Target)")
        return 0

    # Site providers (course or program codes) without the year attached
    provider_set = [ re.sub(',\d{4}', '', p) for p in get_site_providers(APP, SITE_ID) ]

    if update_providers(RUN_DB, link_id, SITE_ID, provider_set):
        logging.info('\tDone')

def main():
    APP = config.config.APP
    parser = argparse.ArgumentParser(description="This script runs the workflow for a site",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("LINK_ID", help="The Link ID to run the workflow for")
    parser.add_argument("SITE_ID", help="The Site ID to run the workflow for")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())
    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP, args['LINK_ID'])

if __name__ == '__main__':
    main()
