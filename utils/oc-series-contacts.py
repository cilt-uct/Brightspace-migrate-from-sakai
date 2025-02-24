#! /usr/bin/python3

# Enable captioning for series based on class size
# https://cilt.atlassian.net/browse/OPENCAST-3295

import argparse
import os
import sys
import logging
from datetime import datetime, timedelta

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.config

from lib.local_auth import getAuth
from lib.d2l import middleware_api, middleware_d2l_api
from lib.opencast import Opencast

# D2L Role Id for Student role
ROLE_STUDENT = 110

def setup_logging(logger, log_file):

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

# Convert series metadata to a key/value dict
def metadata_dict(metadata):
    md = {}
    if metadata is not None:
        for mi in metadata:
            md[mi['id']] = mi['value']
    return md

def get_scheduled_series(oc_client, start_date, end_date):

    logging.info(f"Checking events scheduled from {start_date} to {end_date}")

    # Format the dates
    date_filter = f"start:{start_date.strftime('%Y-%m-%dT00:00:00Z')}/{end_date.strftime('%Y-%m-%dT00:00:00Z')}"
    scheduled_events = oc_client.get_filtered_events(date_filter)

    logging.info(f"Got {len(scheduled_events)} scheduled events")

    series_list = {}

    for event in scheduled_events:
        s_id = event['is_part_of']
        if s_id in series_list:
            series_list[s_id]['events'] = series_list[s_id]['events'] + 1
        else:
            series_list[s_id] = { 'events' : 1, 'title': event['series']}

    return series_list

def is_orgid(org_id):

    if len(org_id) > 6:
        return False

    try:
        int(org_id)
    except:
        return False

    return True

def main():

    APP = config.config.APP

    logfile = f"{parent}/log/oc-series-contacts.log"
    print(f"Logging to {logfile}")

    logger = logging.getLogger()
    setup_logging(logger, logfile)

    parser = argparse.ArgumentParser(description="Find series owners for scheduled Opencast events",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('--update', action='store_true')
    args = vars(parser.parse_args())

    if args['debug']:
        logger.setLevel(logging.DEBUG)

    update = args['update'] or False

    ocAuth = getAuth('Opencast', ['username', 'password'])
    if ocAuth['valid']:
        oc_client = Opencast(APP['opencast']['base_url'], ocAuth['username'], ocAuth['password'])
    else:
        raise Exception('Opencast authentication required')

    # Get today's date
    today = datetime.today()

    # Get events scheduled for the next week
    start_date = today + timedelta(days=1)
    end_date = today + timedelta(days=21)
    scheduled_series = get_scheduled_series(oc_client, start_date, end_date)

    logging.info(f"Got {len(scheduled_series)} different series with upcoming scheduled events")

    all_contacts = []
    contacts = {}
    for series_id in scheduled_series.keys():

        # Check the Amathuba site id from extended metadata
        series_name = scheduled_series[series_id]['title']
        series_metadata = metadata_dict(oc_client.get_series_metadata(series_id, "ext/series"))
        series_contacts = series_metadata['notification-list']

        print(f"Series {series_id} {series_name} contact: {series_contacts}")
        all_contacts.append(series_contacts)
        for contact in series_contacts:

            contact = contact.strip().replace(' ', '')
            if ',' in contact:
                contact_list = contact.split(',')
                for c in contact_list:
                    contacts[c] = series_id
            else:
                contacts[contact] = series_id

    print(f"### All contacts:")
    for contact in contacts.keys():
        print(contact)
    logging.info("Done")

if __name__ == '__main__':
    main()
