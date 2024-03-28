import sys
import os
import re
import shutil
import copy
import json
import bs4
import logging
import time
import requests

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from lib.local_auth import getAuth
from lib.utils import *

# Get a list of LTI links in a site
def get_lti_links(APP, org_id):

    # get existing LTI links
    payload = {
        'url': f"{APP['brightspace_api']['le_url']}/lti/link/{org_id}/",
        'method': 'GET',
    }

    json_response = middleware_d2l_api(APP, payload_data=payload, retries=0)

    if 'status' not in json_response:
        raise Exception(f'Unable to get lti links: {json_response}')

    if json_response['status'] == 'NotFound':
        return []

    if json_response['status'] != 'success':
        raise Exception(f'Unable to get lti links: {json_response}')

    return json_response['data']

# Create a quicklink for an LTI link in a site
def create_lti_quicklink(APP, org_id, lti_data):

    # See if there's an existing LTI link for this URL
    org_links = get_lti_links(APP, org_id)

    link_id = None
    for link in org_links:
        if link['Url'] == lti_data['Url']:
            link_id = link['LtiLinkId']
            break

    if link_id is None:
        # We expect Title, Url, Description, CustomParameters in lti_data
        # https://docs.valence.desire2learn.com/res/lti.html#LTI.CreateLtiLinkData
        required_fields = {
            "UseToolProviderSecuritySettings": True,
            "Key": "",
            "PlainSecret": "",
            "IsVisible": True,
            "SignMessage": True,
            "SignWithTc": True,
            "SendTcInfo": False,
            "SendContextInfo": False,
            "SendUserId": False,
            "SendUserName": False,
            "SendUserEmail": False,
            "SendLinkTitle": False,
            "SendLinkDescription": False,
            "SendD2LUserName": False,
            "SendD2LOrgDefinedId": False,
            "SendD2LOrgRoleId": False,
            "SendSectionCode": False
        }

        for param_key in required_fields.keys():
            if param_key not in lti_data:
                lti_data[param_key] = required_fields[param_key]

        payload = {
            'url': f"{APP['brightspace_api']['le_url']}/lti/link/{org_id}",
            'method': 'POST',
            'payload': json.dumps(lti_data)
        }

        json_response = middleware_d2l_api(APP, payload_data=payload)

        if 'status' in json_response and json_response['status'] == 'success':
            link_id = json_response['data']['LtiLinkId']
        else:
            logging.warning(f"Unexpected response: {json_response}")

    if link_id is None:
        raise Exception(f"Unable to create LTI link for {lti_data['Url']}")

    # Create a quicklink
    # https://docs.valence.desire2learn.com/res/lti.html#LTI.CreateLtiLinkData

    payload = {
        'url': f"{APP['brightspace_api']['le_url']}/lti/quicklink/{org_id}/{link_id}",
        'method': 'POST',
    }

    json_response = middleware_d2l_api(APP, payload_data=payload)

    if 'status' in json_response and json_response['status'] == 'success':
        quicklink_url = json_response['data']['PublicUrl']
        return quicklink_url.replace("{orgUnitId}", str(org_id))

    return
