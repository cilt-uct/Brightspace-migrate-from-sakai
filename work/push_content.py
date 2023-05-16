#!/usr/bin/python3

## Create a D2L import package for files in the content folder
## REF: AMA-440

import sys
import os
import re
import json
import csv
import base64
import argparse
import requests
from pathlib import Path

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *
from lib.local_auth import *

def run(SITE_ID, APP, import_id, transfer_id, title, now_st = None):

    logging.info(f'Push content to orgunitid {import_id} coursecode {transfer_id} title "{title}"')

    content_folder = r'{}{}-content/'.format(APP['output'], SITE_ID)
    logging.info(f'Creating D2L package from {content_folder}')

    manifest_template = APP['import']['manifest']['content']
    manifest_out = f"{content_folder}/imsmanifest.xml"

    # Create a manifest file
    fin = open(manifest_template, "rt")
    data = fin.read()
    fin.close()

    # Replace template values
    data = data.replace("ORGUNITID", str(import_id)).replace("COURSE_OFFERING_NAME", title).replace("COURSE_OFFERING_CODE", transfer_id)

    fin = open(manifest_out, "wt")
    fin.write(data)
    fin.close()

    # Zip it
    max_size = APP['import']['limit']
    if now_st is None:
        now = datetime.datetime.strptime(now_st, "%Y-%m-%d_%H%M%S")
        now_st = now.strftime("%d %b %y %H:%M")

    file_name = r'{}{}_{}.zip'.format(APP['zip']['content'], SITE_ID, now_st)
    zip_file = r'{}{}'.format(APP['output'], file_name)

    if (zipfolder(zip_file, content_folder)):
        zip_size = get_size(zip_file)

        # created file gets logged so it can be used in workflow
        logging.info("\tfile-content-zip: {}".format(zip_file))
        logging.info("\t     content-size: {}".format(format_bytes(zip_size)))

        # check allowed size
        if zip_size > max_size:
            raise Exception(f"Zip size {format_bytes(zip_size)} exceeds maximum {format_bytes(max_size)}")

        # Push it via API for import
        payload = {'org_id': import_id}
        files = [('file', (file_name, zip_file, 'application/zip'))]
        response = requests.post("{}{}".format(APP['middleware']['base_url'], APP['middleware']['import_url']), 
                                 data=payload, files=files)
        response.raise_for_status()

    return

def main():
    global APP
    parser = argparse.ArgumentParser(description="This script will upload files from the webdav folder to the server for the Site and Specified Folder",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID to process")
    parser.add_argument("IMPORT_ID", help="The org unit id of the imported site")
    parser.add_argument("TRANSFER_ID", help="The course code of the imported site")
    parser.add_argument("TITLE", help="The site title")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())
    
    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP, args['IMPORT_ID'], args['TRANSFER_ID'], args['TITLE'])

if __name__ == '__main__':
    main()
