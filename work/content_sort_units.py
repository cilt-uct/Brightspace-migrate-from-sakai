#!/usr/bin/python3

import sys
import os
import argparse
import lib.db
import lib.local_auth
import logging

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.config
import config.logging_config
import lib.db
from lib.d2l import middleware_api

def run(SITE_ID, LINK_ID, APP):

    mdb = lib.db.MigrationDb(APP)
    site = mdb.get_record(link_id=LINK_ID, site_id=SITE_ID)
    org_id = site['transfer_site_id']

    course_info = "{}{}?org_id={}".format(APP['middleware']['base_url'],
                                          APP['middleware']['course_info_order_url'], org_id)
    json_response = middleware_api(APP, course_info)

    if 'status' in json_response:
        if json_response['status'] == 'success':
            logging.info('Course Info has been moved to the top of the content page')

    course_outline = "{}{}?org_id={}".format(APP['middleware']['base_url'],
                                             APP['middleware']['course_outline_order_url'], org_id)
    json_response = middleware_api(APP, course_outline)

    if 'status' in json_response:
        if json_response['status'] == 'success':
            logging.info('Course Info has been moved to the top of the content page')


def main():
    APP = config.config.APP
    parser = argparse.ArgumentParser(description="This script sorts the order of units on the content page",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("LINK_ID", help="The Link ID to run the workflow for")
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], args['LINK_ID'], APP)


if __name__ == '__main__':
    main()
