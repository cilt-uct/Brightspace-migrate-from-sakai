#!/usr/bin/python3

## Push content files from the content folder into Brightspace topics
## REF: AMA-440

import sys
import os
import argparse
import requests

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *
from lib.local_auth import *

def run(SITE_ID, APP, import_id, transfer_id, title):

    tmp = getAuth(APP['auth']['middleware'])
    if (tmp is not None):
        AUTH = {'host' : tmp[0], 'user': tmp[1], 'password': tmp[2]}
    else:
        raise Exception("Middleware Authentication required")

    logging.info(f'Push content to orgunitid {import_id} coursecode {transfer_id} title "{title}"')

    content_folder = r'{}{}-content/'.format(APP['output'], SITE_ID)

    if not os.path.exists(content_folder):
        # Nothing to do
        logging.info(f"No content folder {content_folder}")
        return

    if len(os.listdir(content_folder)) == 0:
        # Nothing to do
        logging.info(f"Content folder {content_folder} is empty")
        return

    logging.info(f'Pushing content from {content_folder}')

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
    file_name = r'{}{}.zip'.format(APP['zip']['content'], SITE_ID)
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
        files = [('file', (file_name, open(zip_file, 'rb'), 'application/zip'))]
        response = requests.post("{}{}".format(APP['middleware']['base_url'], APP['middleware']['import_url']),
                                 data=payload, files=files, auth=(AUTH['user'], AUTH['password']))
        response.raise_for_status()

    return

def main():
    global APP
    parser = argparse.ArgumentParser(description="This script will create a topic",
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
