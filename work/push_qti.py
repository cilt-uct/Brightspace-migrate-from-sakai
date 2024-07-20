#!/usr/bin/python3

## Push a complete QTI package including manifest as a zip import
## REF: AMA-625

import sys
import os
import argparse
import requests
import logging

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.logging_config
from lib.utils import format_bytes, get_size, zipfolder
from lib.local_auth import getAuth
from lib.d2l import wait_for_job

def run(SITE_ID, APP, import_id):

    AUTH = getAuth(APP['auth']['middleware'], ['username', 'password'])
    if not AUTH['valid']:
        raise Exception("Middleware Authentication required")

    logging.info(f'Push QTI package to orgunitid {import_id}')

    package_folder = r'{}{}-{}/'.format(APP['output'], SITE_ID, "qti")

    if not os.path.exists(package_folder):
        # Nothing to do
        logging.info(f"No package folder {package_folder}")
        return

    if len(os.listdir(package_folder)) == 0:
        # Nothing to do
        logging.info(f"Package folder {package_folder} is empty")
        return

    if not os.path.exists(f"{package_folder}/imsmanifest.xml"):
        # No manifest
        logging.warning(f"Package folder {package_folder} does not contain an imsmanifest.xml file - skipping import")
        return

    logging.info(f'Pushing import package from {package_folder}')

    # Zip it
    max_size = APP['import']['limit']
    file_name = r'{}{}.zip'.format(APP['zip']['qti'], SITE_ID)
    zip_file = r'{}{}'.format(APP['output'], file_name)

    if (zipfolder(zip_file, package_folder)):
        zip_size = get_size(zip_file)

        # created file gets logged so it can be used in workflow
        logging.info("\tfile-qti-zip: {}".format(zip_file))
        logging.info("\t     qti-size: {}".format(format_bytes(zip_size)))

        # check allowed size
        if zip_size > max_size:
            raise Exception(f"Zip size {format_bytes(zip_size)} exceeds maximum {format_bytes(max_size)}")

        # Push it via API for import
        payload = {'org_id': import_id}
        files = [('file', (file_name, open(zip_file, 'rb'), 'application/zip'))]
        response = requests.post("{}{}".format(APP['middleware']['base_url'], APP['middleware']['import_url']),
                                 data=payload, files=files, auth=(AUTH['username'], AUTH['password']))
        response.raise_for_status()

        response_json = response.json()
        job_token = response_json['data']['JobToken']

        logging.info(f"Importing package with job {job_token}")

        if wait_for_job(APP, import_id, job_token, delay=30, max_tries=20):
            logging.info(f"Package import {job_token} successful")
        else:
            raise Exception(f"Package import {job_token} failed")

    return

def main():
    APP = config.config.APP
    parser = argparse.ArgumentParser(description="This script imports a QTI package",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID to process")
    parser.add_argument("IMPORT_ID", help="The org unit id of the imported site")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP, args['IMPORT_ID'])

if __name__ == '__main__':
    main()
