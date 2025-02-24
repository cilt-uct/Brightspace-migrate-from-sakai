#!/usr/bin/python3

## https://cilt.atlassian.net/browse/AMA-1209
## Migrate user profile data to user attributes for users created by Course Merchant

import sys
import os
import argparse
import json
import logging
from datetime import datetime

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.config
import config.logging_config
from lib.d2l import middleware_d2l_api, get_brightspace_user

# Map of user profile fields to user attribute ids
# https://amathuba.uct.ac.za/d2l/api/lp/1.45/attributes/schemas/

profile_attrib_map = {
    'Company' : '_companyname',
    'Address1' : 'addressline1',
    'Address2' : 'addressline2',
    'City' : 'city',
    'Province' : 'stateprovinceregion',
    'PostalCode' : 'zippostcode',
    'Country' : 'country',
    'HomePhone' : 'phone',
    'University' : 'dateofbirth',
    'Hobbies' : 'uctstudentnumber'
}

# Fields to clear in the profile
profile_clear_fields = [ 'Email' ]

# Get profile
def get_profile(APP, username):

    payload = {
        'url': f"{APP['brightspace_api']['lp_url']}/profile/user/{username}",
        'method': 'GET'
    }

    json_response = middleware_d2l_api(APP, payload_data=payload, retries=0)

    if 'status' not in json_response:
        raise Exception(f'Unable to get user profile: {json_response}')
    else:
        if json_response['status'] != 'success':
            raise Exception(f'Unable to get user profile: {json_response}')

    return json_response['data']

# Clear fields in the profile
def sanitize_profile(profile):

    new_profile = profile.copy()

    for pf in profile_attrib_map.keys():
        if pf in new_profile:
            new_profile[pf] = None

    for pf in profile_clear_fields:
        if pf in new_profile:
            new_profile[pf] = None

    return new_profile

# Push profile update
def update_profile(APP, userid, new_profile):

    profileId = new_profile['ProfileIdentifier']
    payload = {
        'url': f"{APP['brightspace_api']['lp_url']}/profile/{profileId}",
        'method': 'PUT',
        'payload' : json.dumps(new_profile)
    }

    json_response = middleware_d2l_api(APP, payload_data=payload, retries=0)

    if 'status' not in json_response:
        raise Exception(f'Unable to update user profile: {json_response}')
    else:
        if json_response['status'] != 'success':
            raise Exception(f'Unable to update user profile: {json_response}')

    return json_response['data']

def set_attributes(APP, userId, attribs):

    attr_block = {
        'UserId' : userId,
        'Attributes'  : []
    }

    for ak in attribs.keys():
        a_block = {
            'AttributeId' : ak,
            'Value' : [ attribs[ak]]
        }

        attr_block['Attributes'].append(a_block)

    payload = {
        'url': f"{APP['brightspace_api']['lp_url']}/attributes/users/{userId}",
        'method': 'PUT',
        'payload' : json.dumps(attr_block)
    }

    # print(f"payload: {payload}")

    json_response = middleware_d2l_api(APP, payload_data=payload, retries=0)

    if 'status' not in json_response:
        raise Exception(f'Unable to update user attributes: {json_response}')
    else:
        if json_response['status'] != 'success':
            raise Exception(f'Unable to update user attributes: {json_response}')

    return json_response['data']

def convert_to_iso8601(date_str):
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    iso8601_date_str = date_obj.strftime('%Y-%m-%d')
    return iso8601_date_str

def profile_to_attrib(profile):

    attribs = {}

    for pf in profile.keys():
        if pf in profile_attrib_map and profile[pf] is not None:
            target = profile_attrib_map[pf]

            if target is not None and profile[pf]:
                if target == 'dateofbirth':
                    attribs[target] = convert_to_iso8601(profile[pf])
                else:
                    attribs[target] = profile[pf]

                print(f"Setting attrib {target} to value '{profile[pf]}'")

    return attribs

def migrate_user(APP, username, set_attrib, clear_profile):
    logging.info(f'Migrating user profile for {username}')

    user = get_brightspace_user(APP, username)

    if user is None:
        logging.warning(f"User {username} not found")
        return False

    userid = user['UserId']
    profile = get_profile(APP, userid)
    print(f"User {username} has profile {profile}")

    new_profile = sanitize_profile(profile)
    print(f"Sanitized profile: {new_profile}")

    attribs = profile_to_attrib(profile)

    if set_attrib and len(attribs) > 0:
        print(f"Attribute set: {attribs}")

        set_attributes(APP, userid, attribs)

        if clear_profile:
            update_profile(APP, userid, new_profile)
    else:
        logging.info(f"User {username} has no profile fields to migrate to attributes")

def main():
    APP = config.config.APP
    parser = argparse.ArgumentParser(description="Check for restricted exensions in attachments",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--user", help="The username to migrate")
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('--update', action='store_true')

    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']
    if APP['debug']:
        config.logging_config.logger.setLevel(logging.DEBUG)

    logging.info('Migrate CM user profile data to user attributes')

    username = args['user']
    update = args['update']
    if not username:
        logging.error("Please specify username")
    else:
        migrate_user(APP, username, update, update)

if __name__ == '__main__':
    main()
