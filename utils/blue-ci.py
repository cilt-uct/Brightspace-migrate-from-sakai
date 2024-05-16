import argparse
import os
import sys
import logging
import csv

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.config

from lib.d2l import middleware_d2l_api

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

    # 2024 semester = 13128
    # UCT top-level = 6606
    ou_set = get_orgids_by_tree(APP, 6606)

    # All course offerings
    # ou_set = get_orgids_for_type(APP, 3)

    # Lecturer, Tutor, Administrator, Support Staff, LecturerTutor
    role_set = [ 109, 114, 116, 118, 126 ]

    result_set = []

    logging.info(f"Course offerings: {len(ou_set)}")

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

    logging.info("Writing CSV")

    with open('courses-instructors.csv', 'w', newline='') as csv_f:
        w = csv.DictWriter(csv_f, result_set[0].keys(), dialect='unix')
        w.writeheader()
        w.writerows(result_set)

    logging.info("Done.")

if __name__ == '__main__':
    main()
