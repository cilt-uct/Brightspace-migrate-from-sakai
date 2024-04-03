import argparse
import os
import sys
import json
import logging

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.logging_config
from lib.d2l import middleware_d2l_api, get_course_info

# Updates course info
# PUT /d2l/api/lp/(version)/courses/(orgUnitId)
def update_course_info(APP, org_id, new_info):

    payload = {
        'url': f"{APP['brightspace_api']['lp_url']}/courses/{org_id}",
        'method': 'PUT',
        'payload': json.dumps(new_info)
    }

    json_response = middleware_d2l_api(APP, payload_data=payload, retries=0)

    if 'status' not in json_response:
        raise Exception(f'Unable to update org unit info: {json_response}')
    else:
        if json_response['status'] != 'success':
            raise Exception(f'Unable to update org unit info: {json_response}')

    return True

# Update the Semester
def add_semester_to_course(APP, org_id, semester_id):

    # Get Parents - Filter on Semester Types - SHOULD only have 1 semester
    payload = {
        'url': f"{APP['brightspace_api']['lp_url']}/orgstructure/{org_id}/parents/?ouTypeId=5",
        'method': 'GET',
        'payload': None
    }

    parents = middleware_d2l_api(APP, payload_data=payload, retries=0)

    if parents['status'] in ('success', 'NotFound'):

        if len(parents['data']) > 0:
            # There is more than one semester so remove the old ones first
            for parent in parents['data']:

                # if it is not the one we want to add
                if int(parent['Identifier']) != int(semester_id):
                    payload = {
                        'url': f"{APP['brightspace_api']['lp_url']}/orgstructure/{org_id}/parents/{parent['Identifier']}",
                        'method': 'DELETE',
                        'payload': None
                    }

                    result = middleware_d2l_api(APP, payload_data=payload)
                    if 'status' not in result or result['status'] != 'success':
                        raise Exception(f"Failed removing semester from org id {org_id}")

        # add new Semester
        payload = {
            'url': f"{APP['brightspace_api']['lp_url']}/orgstructure/{org_id}/parents/",
            'method': 'POST',
            'payload': f'{semester_id}'
        }

        result = middleware_d2l_api(APP, payload_data=payload)
        if 'status' not in result or result['status'] != 'success':
            raise Exception(f"Failed adding semester to org id {org_id}")

    else:
        raise Exception(f"Cannot get parents: {parents}")

def run(SITE_ID, APP, import_id):

    semester_id = APP['site']['semester']

    logging.info(f'Updating site status for Brightspace reference site {import_id}: semester {semester_id}')

    # Get the course offering info
    site_data = get_course_info(APP, import_id)

    # The API accepts these fields only
    new_course_info = {
        "IsActive": False,
        "Name": site_data['Name'],
        "Code": site_data['Code'],
        "StartDate": site_data['StartDate'],
        "EndDate": site_data['EndDate'],
        "Description": { "Content": site_data['Description']['Text'], "Type": "Text" },
        "CanSelfRegister": site_data['CanSelfRegister'],
    }

    if update_course_info(APP, import_id, new_course_info):
        return add_semester_to_course(APP, import_id, semester_id)

    return False

def main():
    APP = config.config.APP
    parser = argparse.ArgumentParser(description="Update reference site status and semester",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID to process")
    parser.add_argument("IMPORT_ID", help="The org unit id of the imported site")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP, args['IMPORT_ID'])

if __name__ == '__main__':
    main()
