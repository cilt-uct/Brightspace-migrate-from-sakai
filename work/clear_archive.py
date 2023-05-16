#!/usr/bin/python3

# Remove the archive folder for a site id

import sys
import os
import re
import shutil
import copy
import argparse
from bs4 import BeautifulSoup

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *

def run(SITE_ID, APP):
    logging.info('Clearing archive folder for site: {}'.format(SITE_ID))

    archive = "{}{}-archive/".format(APP['archive_folder'], SITE_ID)
    shutil.rmtree(archive)
    return True

def main():
    global APP
    parser = argparse.ArgumentParser(description="This script clears the archive folder for a site)",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
