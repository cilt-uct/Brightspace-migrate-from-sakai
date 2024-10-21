#!/usr/bin/python3

# Workflow that just raises an exception for testing purposes

import sys
import os
import argparse
import logging

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.config
import config.logging_config

def run(SITE_ID, APP):

    logging.info('Error workflow : {}'.format(SITE_ID))

    raise Exception("Test exception raised")

def main():
    APP = config.config.APP
    parser = argparse.ArgumentParser(description="This script takes as input the 'lessonbuilder.xml' file inside the site-archive folder and adds a default banner to the body if it doesn't exist yet",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
