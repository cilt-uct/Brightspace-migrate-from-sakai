#!/usr/bin/python3

## This script will create a new zip file for the site in the site-archive folder (SITE_ID-fixed.zip)
## REF: AMA-61

import sys
import os
import glob
import argparse
from datetime import datetime
from pathlib import Path

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *

def run(SITE_ID, APP, now_st = None):

    if now_st is None:
        now = datetime.now()
        now_st = now.strftime("%Y-%m-%d-%H%M%S")

    logging.info('Zip: {} at {}'.format(SITE_ID, now_st))

    # Max allowed size for upload (bytes)
    max_size = APP['ftp']['limit']

    src_folder = r'{}{}-archive/'.format(APP['archive_folder'], SITE_ID)
    zip_file = r'{}{}{}_fixed_{}.zip'.format(APP['output'], APP['zip']['site'], SITE_ID, now_st)

    if not os.path.exists(src_folder):
        raise Exception(f"Archive folder {src_folder} not found")

    # Check folder size
    src_path = Path(src_folder)
    folder_size = sum(f.stat().st_size for f in src_path.glob('**/*') if f.is_file())
    logging.debug(f"Folder size for {SITE_ID} is {format_bytes(folder_size)}")

    if folder_size > max_size:
        raise Exception(f"Folder size {format_bytes(folder_size)} exceeds maximum {format_bytes(max_size)}")

    # print(f'{src_folder}\n{zip_file}')
    for py in glob.glob('{}/*{}_fixed*.zip'.format(APP['output'], SITE_ID)):
        os.remove(py)

    zipfolder(zip_file, src_folder)

    if not os.path.exists(zip_file):
        raise Exception(f"Error creating zip file {zip_file}")

    zip_size = get_size(zip_file)

    # created file gets logged so it can be used in workflow
    logging.info("\tfile-fixed-zip: {}".format(zip_file))
    logging.info("\t     fixed-size: {}".format(format_bytes(zip_size)))

    # check allowed size
    if zip_size > max_size:
        raise Exception(f"Zip size {format_bytes(zip_size)} exceeds maximum {format_bytes(max_size)}")

def main():
    global APP
    parser = argparse.ArgumentParser(description="This script will create a new zip file for the site in the site-archive folder (SITE_ID-fixed.zip)",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID to create a zip for")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
