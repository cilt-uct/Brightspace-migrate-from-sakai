import argparse
import os
import sys
import logging
import csv
from datetime import datetime

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.config

from lib.local_auth import getAuth
from lib.d2l import middleware_d2l_api
from lib.explorance import PushDataSource

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

def get_orgids_for_type(APP, ou_type_id):

    items = []
    has_more_items = True
    bookmark = None

    while has_more_items:
        payload = {
            'url': f"{APP['brightspace_api']['lp_url']}/orgstructure/?orgUnitType={ou_type_id}",
            'method': 'GET'
        }

        if bookmark:
            payload['url'] += f"&bookmark={bookmark}"

        # print(f"Getting courses: {payload['url']}")

        json_response = middleware_d2l_api(APP, payload_data=payload, retries=0)

        if 'status' not in json_response:
            raise Exception(f'Unable to update org unit info: {json_response}')
        else:
            if json_response['status'] != 'success':
                raise Exception(f'Unable to update org unit info: {json_response}')

        has_more_items = json_response['data']['PagingInfo']['HasMoreItems']
        bookmark = json_response['data']['PagingInfo']['Bookmark']
        items += json_response['data']['Items']

    return items


def get_orgids_by_tree(APP, parent_org_id):

    payload = {
        'url': f"{APP['brightspace_api']['lp_url']}/orgstructure/{parent_org_id}/descendants/?ouTypeId=3",
        'method': 'GET'
    }

    json_response = middleware_d2l_api(APP, payload_data=payload, retries=0)

    if 'status' not in json_response:
        raise Exception(f'Unable to update org unit info: {json_response}')
    else:
        if json_response['status'] != 'success':
            raise Exception(f'Unable to update org unit info: {json_response}')

    return json_response['data']

def get_enrolment_page1(APP, org_id):

    payload = {
        'url': f"{APP['brightspace_api']['lp_url']}//enrollments/orgUnits/{org_id}/users/?isActive=1",
        'method': 'GET'
    }

    json_response = middleware_d2l_api(APP, payload_data=payload, retries=0)

    if 'status' not in json_response:
        raise Exception(f'Unable to update org unit info: {json_response}')
    else:
        if json_response['status'] != 'success':
            raise Exception(f'Unable to update org unit info: {json_response}')

    return json_response['data']

def get_filtered_enrolment(APP, org_id, role_set):

    items = []

    page1 = get_enrolment_page1(APP, org_id)

    if not page1['PagingInfo']['HasMoreItems']:
        logging.debug("Using single query")
        # Single query is fine, filter this result set

        if 'Items' in page1:
            for member in page1['Items']:
                if member['Role']['Id'] in role_set:
                    items.append(member)

        return items

    # Check role by role because it may be faster than paging through a large enrolment

    logging.debug("role-by-role query")
    for role in role_set:

        has_more_items = True
        bookmark = None

        while has_more_items:

            payload = {
                'url': f"{APP['brightspace_api']['lp_url']}//enrollments/orgUnits/{org_id}/users/?roleId={role}&isActive=1",
                'method': 'GET'
            }

            if bookmark:
                payload['url'] += f"&bookmark={bookmark}"

            # print(f"URL: {payload['url']}")

            json_response = middleware_d2l_api(APP, payload_data=payload, retries=0)

            if 'status' not in json_response:
                raise Exception(f'Unable to update org unit info: {json_response}')
            else:
                if json_response['status'] != 'success':
                    raise Exception(f'Unable to update org unit info: {json_response}')

            has_more_items = json_response['data']['PagingInfo']['HasMoreItems']
            bookmark = json_response['data']['PagingInfo']['Bookmark']

            # print(f"More: {has_more_items} bookmark {bookmark}")
            items += json_response['data']['Items']

    return items

def main():

    APP = config.config.APP

    logger = logging.getLogger()
    setup_logging(APP, logger, "blue-ci.log")

    parser = argparse.ArgumentParser(description="This script gets Brightspace import statuses",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('--dev', action='store_true')
    args = vars(parser.parse_args())

    if args['debug']:
        logger.setLevel(logging.DEBUG)

    now = datetime.now()
    now_st = now.strftime("%Y%m%d_%H%M")

    # 2024 semester = 13128
    # UCT top-level = 6606
    ou_2023 = get_orgids_by_tree(APP, 8585)
    ou_2024 = get_orgids_by_tree(APP, 13128)
    ou_other = get_orgids_by_tree(APP, 12144)

    ou_set = ou_2023 + ou_2024 + ou_other

    # All course offerings
    # ou_set = get_orgids_for_type(APP, 3)

    # Lecturer, Tutor, Administrator, Support Staff, LecturerTutor
    role_set = [ 109, 114, 116, 118, 126 ]

    result_set = []

    logging.info(f"Course offerings: {len(ou_set)} 2023={len(ou_2023)} 2024={len(ou_2024)} other={len(ou_other)}")

    for ou in ou_set:
        org_id = ou['Identifier']
        org_name = ou['Name']

        ou_enrolled = get_filtered_enrolment(APP, org_id, role_set)

        logging.info(f"got {len(ou_enrolled)} members matching roleset for org_id {org_id} name {org_name}")
        sys.stdout.flush()

        for member in ou_enrolled:
            item = {}
            item['Identifier'] = org_id
            item['User_UserName'] = member['User']['UserName']
            item['User_DisplayName'] = member['User']['DisplayName']
            item['Role_Id'] = member['Role']['Id']
            item['Role_Name'] = member['Role']['Name']
            logging.debug(f"adding {item}")
            result_set.append(item)

        sys.stdout.flush()

    csv_file = f"courses-instructors.{now_st}.csv"
    logging.info(f"Writing CSV to {csv_file} with {len(result_set)} rows")

    with open(csv_file, 'w', newline='') as csv_f:
        w = csv.DictWriter(csv_f, result_set[0].keys(), dialect='unix')
        w.writeheader()
        w.writerows(result_set)

    logging.info("Finished CSV export")

    # Now push into Blue Data Source
    blue_source = "BlueTest" if args['dev'] else "Blue"
    ds_name = "Courses Instructors"

    blue_api = getAuth(blue_source, ['apikey', 'url'])

    if not blue_api['valid']:
        raise Exception("Missing configuration")

    logging.info(f"Explorance endpoint {blue_api['url']}")
    PDS = PushDataSource(blue_api['url'], blue_api['apikey'])

    ds_id = PDS.getDataSourceId(ds_name)
    push_result = PDS.PushCSV(ds_id, csv_file)

    logging.info(f"Done, success={push_result}")

if __name__ == '__main__':
    main()
