#!/usr/bin/python3

## This script will upload files from the webdav folder to the server for the site and specified folder
## REF: AMA-440

import sys
import os
import re
import json
import csv
import base64
import argparse
from pathlib import Path

from tqdm import tqdm
from webdav3.client import Client

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *
from lib.local_auth import *

def process_webdav(SITE_ID, target_folder):

    webdav_src = os.path.join(APP['webdav_folder'], SITE_ID)

    # Target folder should be a valid Course Offering Path, e.g.
    # /content/enforced/13323-9da6b86e-15d3-4d29-b6f4-3a129109b869_20221110_1041/

    #if not target_folder or not target_folder.startswith("/content/enforced/"):
    #    raise Exception(f"Missing or invalid target folder {taret_folder}")

    logging.info(f'Webdav: upload files from {webdav_src} to {target_folder}')

    tmp = getAuth('BrightspaceWebdav')
    if (tmp is not None):
        WEBDAV = {'webdav_hostname' : tmp[0], 'webdav_login': tmp[1], 'webdav_password' : tmp[2]}
    else:
        raise Exception("Authentication required")

    webdav = Client(WEBDAV)

    if not webdav:
        raise Exception("Unable to authenticate for webdav")

    logging.info("Starting")

    try:

        webdav_files = webdav.list(target_folder)
        print(json.dumps(webdav_files, indent=4))

        # Upload everything we have
        for f in Path(webdav_src).glob('**/*'):

            if f.is_file():

                relative_path = f.relative_to(webdav_src)
                logging.info(f"Uploading {SITE_ID} content {relative_path}")

                # Upload everything we have

                # Checking existence of the resource we want to replace
                #if webdav.check(remote_file):
                #    before_upload = webdav.info(remote_file)
                #    local_size = os.path.getsize(local_file)

                # if the file size is the same - assume it is there and continue to next file
                #    webdav.upload_sync( remote_path=remote_file, local_path=local_file)
                #    after_upload = webdav.info(remote_file)

    except Exception as e:
        raise Exception(f"Error uploading webdav files: {e}")

def main():
    global APP
    parser = argparse.ArgumentParser(description="This script will upload files from the webdav folder to the server for the Site and Specified Folder",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID to process")
    parser.add_argument("FOLDER", help="The Folder to upload to")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    process_webdav(args['SITE_ID'], args['FOLDER'])

if __name__ == '__main__':
    main()
