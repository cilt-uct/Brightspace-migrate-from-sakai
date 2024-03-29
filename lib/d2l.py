import sys
import os
import json
import time
import requests
import logging

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from lib.utils import middleware_api

# D2L API versions
# See https://docs.valence.desire2learn.com/about.html#principal-version-table

D2L_API_LE_VERSION="1.74"
D2L_API_LP_VERSION="1.45"

# Call a D2L endpoint via middleware proxy
def middleware_d2l_api(APP, payload_data = None, retries = None, retry_delay = None, headers = None):

    api_proxy_url = f"{APP['middleware']['base_url']}{APP['middleware']['api_proxy_url']}"
    return middleware_api(APP, api_proxy_url, method='POST', payload_data = payload_data, retries = retries, retry_delay = retry_delay, headers = headers)

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

# GET /d2l/api/le/(version)/import/(orgUnitId)/imports/(jobToken)
# Status = UPLOADING | IMPORTING | IMPORTFAILED | COMPLETED
def wait_for_job(APP, org_id, job_token, initial_delay = 3, delay = 10, max_tries = 12):

    time.sleep(initial_delay)

    tries = 0

    while tries < max_tries:

        tries += 1

        payload = {
            'url': f"{APP['brightspace_api']['le_url']}/import/{org_id}/imports/{job_token}",
            'method': 'GET'
        }

        # {'data': {'JobToken': '6992', 'Status': 'IMPORTING', 'TargetOrgUnitId': 67143}, 'status': 'success'}
        json_response = middleware_d2l_api(APP, payload_data=payload, retries=0)

        if 'status' in json_response and json_response['status'] == 'success' and 'data' in json_response:
            if 'Status' in json_response['data']:
                import_status = json_response['data']['Status']
                logging.info(f"Import job {job_token} has status {import_status}")

                if import_status == "IMPORTFAILED":
                    return False

                if import_status == "COMPLETED":
                    return True
            else:
                logging.warning(f"Unexpected response {json_response}, will retry")
        else:
            logging.warning(f"Unexpected response {json_response}, will retry")

        time.sleep(delay)

    # Out of tries
    return False

# Login via UI for things we can't do via the APIs
def web_login(login_url, username, password):

    logging.info(f"Web UI login with service account {username}")

    values = {
        'web_loginPath': '/d2l/login',
        'username': username,
        'password': password
    }

    session = requests.Session()
    session.post(login_url, data=values, timeout=30)
    return session

# Gets course info
# See https://docs.valence.desire2learn.com/res/course.html
def get_course_info(APP, org_id):

    info_url_template = "{}{}".format(APP['middleware']['base_url'], APP['middleware']['course_info_url'])
    info_url = info_url_template.format(org_id)

    json_response = middleware_api(APP, info_url)

    if 'status' not in json_response:
        raise Exception(f'Unable to get org unit info: {json_response}')
    else:
        if json_response['status'] != 'success':
            raise Exception(f'Unable to get org unit info: {json_response}')

    return json_response['data']
