#!/usr/bin/python3

## Create a D2L import package for files in the rubrics folder
## REF: AMA-440

import sys
import os
import argparse
import requests
import logging

from xml.sax.saxutils import escape

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.logging_config
from lib.utils import format_bytes, get_size, zipfolder
from lib.local_auth import getAuth
from lib.d2l import wait_for_job

def run(SITE_ID, APP, import_id, transfer_id, title):

    AUTH = getAuth(APP['auth']['middleware'], ['username', 'password'])
    if not AUTH['valid']:
        raise Exception("Middleware Authentication required")

    logging.info(f'Push rubrics to orgunitid {import_id} coursecode {transfer_id} title "{title}"')

    # Rubrics XML file
    output_folder = r'{}{}-rubrics/'.format(APP['output'], SITE_ID)
    rubrics_file = os.path.join(output_folder, "rubrics_d2l.xml")

    if os.path.exists(rubrics_file):
        logging.info(f"Rubrics XML is {rubrics_file}")
    else:
        logging.info("No rubrics file, nothing to do")
        return

    # Output zip file
    file_name = r'{}{}.zip'.format(APP['zip']['rubrics'], SITE_ID)
    zip_file = r'{}{}'.format(APP['output'], file_name)

    logging.info(f"Rubrics package zip is {zip_file}")

    # Create a manifest file and zipfile
    manifest_template = APP['import']['manifest']['rubrics']
    manifest_out = f"{output_folder}/imsmanifest.xml"

    # Create a manifest file
    fin = open(manifest_template, "rt")
    data = fin.read()
    fin.close()

    # Replace template values
    data = data.replace("ORGUNITID", str(import_id)).replace("COURSE_OFFERING_NAME", escape(title)).replace("COURSE_OFFERING_CODE", transfer_id)

    fin = open(manifest_out, "wt")
    fin.write(data)
    fin.close()

    # Zip it
    max_size = APP['import']['limit']

    file_name = r'{}{}.zip'.format(APP['zip']['rubrics'], SITE_ID)
    zip_file = r'{}{}'.format(APP['output'], file_name)

    zipfolder(zip_file, output_folder)

    if not os.path.exists(zip_file):
        raise Exception(f"Error creating rubrics zip {zip_file} from {output_folder}")

    zip_size = get_size(zip_file)

    # created file gets logged so it can be used in workflow
    logging.info("\tfile-rubrics-zip: {}".format(zip_file))
    logging.info("\t     rubrics-size: {}".format(format_bytes(zip_size)))

    # check allowed size
    max_size = APP['import']['limit']
    if zip_size > max_size:
        raise Exception(f"Zip size {format_bytes(zip_size)} exceeds maximum {format_bytes(max_size)}")

    # Push it via API for import
    # TODO replace with middleware_api method after extending that to support files
    payload = {'org_id': import_id}
    files = [('file', (file_name, open(zip_file, 'rb'), 'application/zip'))]
    response = requests.post("{}{}".format(APP['middleware']['base_url'], APP['middleware']['import_url']),
                             data=payload, files=files, auth=(AUTH['username'], AUTH['password']))

    response.raise_for_status()
    response_json = response.json()
    job_token = response_json['data']['JobToken']

    logging.info(f"Importing rubrics with job {job_token}")

    if wait_for_job(APP, import_id, job_token):
        logging.info(f"Rubric import {job_token} successful")
    else:
        raise Exception(f"Rubric import {job_token} failed")

    return

def main():
    APP = config.config.APP
    parser = argparse.ArgumentParser(description="This script uploads rubrics",
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
