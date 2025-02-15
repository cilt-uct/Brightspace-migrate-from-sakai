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
from lib.d2l import middleware_d2l_api
from lib.opencast import Opencast

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

def get_enrolment_count(APP, org_id, role_id):

    items = []

    # Check role by role because it may be faster than paging through a large enrolment

    has_more_items = True
    bookmark = None

    while has_more_items:

        payload = {
            'url': f"{APP['brightspace_api']['lp_url']}//enrollments/orgUnits/{org_id}/users/?roleId={role_id}&isActive=1",
            'method': 'GET'
        }

        if bookmark:
            payload['url'] += f"&bookmark={bookmark}"

        json_response = middleware_d2l_api(APP, payload_data=payload, retries=0)

        if 'status' not in json_response:
            raise Exception(f'Unable to get org unit info: {json_response}')
        else:
            if json_response['status'] != 'success':
                raise Exception(f'Unable to get org unit info: {json_response}')

        has_more_items = json_response['data']['PagingInfo']['HasMoreItems']
        bookmark = json_response['data']['PagingInfo']['Bookmark']
        items += json_response['data']['Items']

    return len(items)

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

def main():

    APP = config.config.APP

    logfile = f"{parent}/log/oc-captions.log"
    print(f"Logging to {logfile}")

    logger = logging.getLogger()
    setup_logging(logger, logfile)

    parser = argparse.ArgumentParser(description="OPENCAST-3295 Enable captions",
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

    # Enable captions for series above this audience size
    size_threshold = 250

    # D2L Role Id for Student role
    ROLE_STUDENT = 110

    # Caption Provider
    CAPTION_ID = 'nibity'

    # Get today's date
    today = datetime.today()

    # Get events scheduled for the next week
    start_date = today + timedelta(days=1)
    end_date = today + timedelta(days=8)
    scheduled_series = get_scheduled_series(oc_client, start_date, end_date)

    logging.info(f"Got {len(scheduled_series)} different series with upcoming scheduled events")

    for series_id in scheduled_series.keys():

        # Check the Amathuba site id from extended metadata
        series_name = scheduled_series[series_id]['title']
        series_metadata = metadata_dict(oc_client.get_series_metadata(series_id, "ext/series"))

        series_captions = series_metadata['caption-type']
        series_orgid = series_metadata['site-id']
        series_events = scheduled_series[series_id]['events']

        if series_captions == CAPTION_ID:
            logging.debug(f"Series {series_id} '{series_name}' events {series_events} captions '{series_captions}' already enabled")
        else:
            enrolled = get_enrolment_count(APP, series_orgid, ROLE_STUDENT)
            logging.debug(f"Series {series_id} '{series_name}' events {series_events} has orgid {series_orgid} captions '{series_captions}' enrollment {enrolled}")
            if enrolled >= size_threshold:
                if update:
                    logging.info(f"Enabling captions for series {series_id} '{series_name}' with {enrolled} students in Amathuba site {series_orgid}")
                    oc_client.update_series_metadata(series_id, "ext/series", {'caption-type' : CAPTION_ID})
                else:
                    logging.info(f"Series {series_id} '{series_name}' has {enrolled} students in Amathuba site {series_orgid}")

    logging.info("Done")

if __name__ == '__main__':
    main()
