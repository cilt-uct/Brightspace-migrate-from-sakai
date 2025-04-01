#!/usr/bin/python3

## Update site providers

import sys
import os
import argparse
import re
import logging

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.logging_config
import lib.db
from lib.utils import get_site_providers

def run(SITE_ID, APP, link_id):
    logging.info('Update site provider : {}'.format(SITE_ID))

    # Site providers (course or program codes) without the year attached
    provider_set = [ re.sub(r',\d{4}', '', p) for p in get_site_providers(APP, SITE_ID) ]

    mdb = lib.db.MigrationDb(APP)
    if mdb.update_providers(link_id, SITE_ID, provider_set):
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
