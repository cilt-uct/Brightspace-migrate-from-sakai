#!/usr/bin/python3

## This script will get statistics on the zip files for this site
## REF:

import sys
import os
import glob
import argparse
import re

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *

def run(SITE_ID, APP, now_st = None):

    if now_st is None:
        now_st = ""

    logging.info('Stats: {} at {}'.format(SITE_ID, now_st if now_st != "" else "any and all dates" ))

    fixed = '.*_fixed_.*.zip$'
    rubric = '.*_rubrics.*.zip$'
    file_type = "Main"
    for py in glob.glob('{}/*{}*{}.zip'.format(APP['output'], SITE_ID, now_st)):
        if re.match(fixed, py):
            file_type = "Fixed"
        if re.match(rubric, py):
            file_type = "Rubric"

        logging.info("\t{}: {}".format(file_type.ljust(6), format_bytes(int(get_size(py)))))

def main():
    global APP
    parser = argparse.ArgumentParser(description="This script will get statistics on the zip files for this site",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID to get stats for")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())
    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP,"2022-09-26_201902")

if __name__ == '__main__':
    main()
