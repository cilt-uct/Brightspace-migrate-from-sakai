#!/usr/bin/python3

## Stub operation to export assessments in QTI format from Mneme or other third-party tool

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

    logging.info(f'QTI: export {SITE_ID}')

    output_folder = r'{}{}-qti/'.format(APP['output'], SITE_ID)
    if not os.path.exists(output_folder):
        os.mkdir(output_folder)

    # TODO export the assessments QTI .zip file from the Sakai site

    # TODO unzip the assessments QTI into output_folder

    # TODO make any changes to the QTI XML in output_folder prior to import


def main():

    APP = config.config.APP

    parser = argparse.ArgumentParser(description="This script exports QTI assessments from a Sakai site.",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID from which to export the QTI package")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    if APP['debug']:
        config.logging_config.logger.setLevel(logging.DEBUG)

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
