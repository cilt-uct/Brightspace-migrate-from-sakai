#!/usr/bin/python3

## This is here for testing convenience, and is not a workflow operation itself

import sys
import os
import argparse

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.logging_config
import lib.sakai

def main():
    APP = config.config.APP
    parser = argparse.ArgumentParser(description="This script will try and archive a Sakai site - this will create a ZIP file and return True if success",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID for which to transfer fixed file")
    parser.add_argument('-f', '--force', help="Archive the site by ignoring size restrictions", action='store_true')
    parser.add_argument('-d', '--debug', action='store_true')

    args = vars(parser.parse_args())
    APP['debug'] = APP['debug'] or args['debug']

    # Sakai webservices
    sakai_ws = lib.sakai.Sakai(APP)

    # Archive site
    sakai_ws.archive_site_retry(args['SITE_ID'], args['force'])

if __name__ == '__main__':
    main()
