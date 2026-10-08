import argparse
import os
import sys
import logging
import csv
import re
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
    args = vars(parser.parse_args())

    if args['debug']:
        logger.setLevel(logging.DEBUG)

    now = datetime.now()
    now_st = now.strftime("%Y%m%d_%H%M")

    ou_2026 = get_orgids_by_tree(APP, 46037)

    ou_set = ou_2026

    # All course offerings
    # ou_set = get_orgids_for_type(APP, 3)

    # Lecturer, LecturerTutor
    role_set = [ 109, 126 ]

    result_set = []

    logging.info(f"Course offerings: {len(ou_set)}")

    for ou in ou_set:
        org_id = ou['Identifier']
        org_name = ou['Name']
        org_code = ou['Code']

        #print(f"Got: {ou}")

        ou_enrolled = get_filtered_enrolment(APP, org_id, role_set)

        logging.info(f"got {len(ou_enrolled)} members matching roleset for org_id {org_id} name {org_name}")
        sys.stdout.flush()

        for member in ou_enrolled:
            #print(f"user: {member['User']}")
            item = {}
            item['Identifier'] = org_id
            item['User_UserName'] = member['User']['UserName']
            item['User_DisplayName'] = member['User']['DisplayName']
            item['Email'] = member['User']['EmailAddress']
            item['Role_Id'] = member['Role']['Id']
            item['Role_Name'] = member['Role']['Name']
            item['Site_Name'] = org_name
            item['Site_Code'] = org_code
            logging.debug(f"adding {item}")
            result_set.append(item)

        sys.stdout.flush()

    csv_file = f"dec-lecturers.{now_st}.csv"
    logging.info(f"Writing CSV to {csv_file} with {len(result_set)} rows")

    with open(csv_file, 'w', newline='') as csv_f:
        w = csv.DictWriter(csv_f, result_set[0].keys(), dialect='unix')
        w.writeheader()
        w.writerows(result_set)

    # Regex pattern: 3 uppercase letters, then 1/2/3, then 3 digits, then 1 alpha
    pattern = re.compile(r'[A-Z]{3}[123]\d{3}[A-Za-z]')

    email_map = {}
    username_map = {}

    for row in result_set:
        site_name = row["Site_Name"]
        site_code = row["Site_Code"]
        username = row["User_UserName"]
        display_name = row["User_DisplayName"]
        email = row["Email"]

        if pattern.match(site_name) or pattern.match(site_code):
            if len(username) == 8 and username.isdigit():
                email_map[email] = display_name
                username_map[username] = display_name

    csv_file = f"dec-lecturers-emails.{now_st}.csv"
    logging.info(f"Writing CSV to {csv_file} with {len(email_map)} rows")
    with open(csv_file, 'w', newline='') as csv_f:
        writer = csv.writer(csv_f)
        writer.writerow(["Email", "Name"])
        for email, name in email_map.items():
            writer.writerow([email, name])

    csv_file = f"dec-lecturers-users.{now_st}.csv"
    logging.info(f"Writing CSV to {csv_file}")
    with open(csv_file, 'w', newline='') as csv_f:
        writer = csv.writer(csv_f)
        writer.writerow(["Username", "Name"])
        for username, name in username_map.items():
            writer.writerow([username, name])

    logging.info("Finished CSV export")

if __name__ == '__main__':
    main()
