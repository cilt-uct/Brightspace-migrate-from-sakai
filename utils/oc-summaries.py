#! /usr/bin/python3

# Create Amathuba content page with lecture summaries from Opencast

import argparse
import os
import sys
import logging
import json
from datetime import datetime

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.config

from lib.local_auth import getAuth
from lib.d2l import middleware_d2l_api
from lib.opencast import Opencast

def setup_logging(APP, logger, log_file):

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(process)d %(filename)s(%(lineno)d) %(message)s')

    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # create stream handler (logging in the console)
    sh = logging.StreamHandler()
    sh.setLevel(logging.DEBUG)
    sh.setFormatter(formatter)
    logger.addHandler(sh)

def is_published(event):
    return 'publication_status' in event and "engage-player" in event['publication_status']

def has_captions(event):

    if 'publications' in event:
        for pub in event['publications']:
            if 'attachments' in pub:
                for attach in pub['attachments']:
                    if attach['mediatype'] == "text/vtt":
                        return True

    return False

def create_summaries(APP, series_id, org_id):

    ocAuth = getAuth('Opencast', ['username', 'password'])
    if ocAuth['valid']:
        oc_client = Opencast(APP['opencast']['base_url'], ocAuth['username'], ocAuth['password'])
    else:
        raise Exception('Opencast authentication required')

    events = oc_client.get_events(series_id)
    if events is None:
        print(f"No events for series {series_id}")
        return

    for event in events:

        if is_published(event) and has_captions(event):

            # Published event
            eventId = event['identifier']
            print(f"Published event with captions: {eventId} {event['start']}")

            # Get this from published json in due course
            # https://jira.cilt.uct.ac.za/browse/OPENCAST-3254
            asset = oc_client.get_asset(eventId)

            # Extract the URL containing "nibity"
            attachments = asset['mediapackage']['attachments']['attachment']
            for attachment in attachments:
                if 'nibity' in attachment['@id']:
                    nibity_url = attachment['url']
                    print("URL of the nibity file:", nibity_url)
                    nibity_json = json.loads(oc_client.get_asset_zip_contents(nibity_url, f"{eventId}.json"))
                    print(f"got: {nibity_json}")

    return

def main():

    APP = config.config.APP

    logger = logging.getLogger()
    setup_logging(APP, logger, "summaries.log")

    parser = argparse.ArgumentParser(description="This script gets Brightspace import statuses",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("SERIES_ID", help="The Opencast series on which to work")
    parser.add_argument("ORG_ID", help="The Brightspace course (org unit id)")

    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    if args['debug']:
        logger.setLevel(logging.DEBUG)

    create_summaries(APP, args['SERIES_ID'], args['ORG_ID'])

    logging.info("Done")

if __name__ == '__main__':
    main()
