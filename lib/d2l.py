import sys
import os
import json
import time
import requests
import re
import logging

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from lib.utils import middleware_api

# D2L API versions
# See https://docs.valence.desire2learn.com/about.html#principal-version-table

# Call a D2L endpoint via middleware proxy
def middleware_d2l_api(APP, payload_data = None, retries = None, retry_delay = None, headers = None):

    api_proxy_url = f"{APP['middleware']['base_url']}{APP['middleware']['api_proxy_url']}"
    return middleware_api(APP, api_proxy_url, method='POST', payload_data = payload_data, retries = retries, retry_delay = retry_delay, headers = headers)

# Get product version. This doesn't require authentication but will verify basic URL and connection
def d2l_api_version(APP, product):

    # get existing LTI links
    payload = {
        'url': f"{APP['brightspace_api']['base_url']}/d2l/api/{product}/versions/",
        'method': 'GET',
    }

    json_response = middleware_d2l_api(APP, payload_data=payload, retries=0)

    if not json_response:
        raise Exception(f'Unable to get product {product} version')

    if 'status' not in json_response:
        raise Exception(f'Unable to get product {product} version: {json_response}')

    if json_response['status'] != 'success':
        raise Exception(f'Unable to get product {product} version: {json_response}')

    if 'data' not in json_response or 'LatestVersion' not in json_response['data']:
        raise Exception(f'Unable to get product {product} version: {json_response}')

    return json_response['data']['LatestVersion']

# Get a list of Legacy LTI tool providers (LTI 1.1.x)
# Shown in External Learning Tools / Manage Tool Providers
#  /d2l/lms/lti/manage/tp_list.d2l?ou=6606
# https://docs.valence.desire2learn.com/res/lti.html
# GET /d2l/api/le/(version)/lti/link/(orgUnitId)/
def get_lti_tool_providers(APP, org_id):

    payload = {
        'url': f"{APP['brightspace_api']['le_url']}/lti/tp/{org_id}/",
        'method': 'GET',
    }

    json_response = middleware_d2l_api(APP, payload_data=payload, retries=0)

    if 'status' not in json_response:
        raise Exception(f'Unable to get lti links: {json_response}')

    if json_response['status'] != 'success':
        raise Exception(f'Unable to get lti links: {json_response}')

    return json_response['data']

def lti_available(launch_url, lti1x_providers):

    if lti1x_providers is None:
        return False

    for provider in lti1x_providers:
        if provider['LaunchPoint'] in launch_url:
            return True

    return False

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
        raise Exception(f"Unable to create LTI link: {lti_data}")

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
    resp = session.post(login_url, data=values, allow_redirects = False, timeout=30)

    if resp.is_redirect and resp.headers['Location'] == "/d2l/home":
        return session

    logging.error(f"Authentication failed logging in to {login_url} with {username}")
    return None

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

# Course package import history
def get_import_history(brightspace_url, org_unit, session):
    url = f'{brightspace_url}/d2l/le/conversion/import/{org_unit}/history/display?ou={org_unit}'
    r = session.get(url, timeout=30)
    return r.text

def get_first_import_status(content):
    pattern = re.compile('<d2l-status-indicator state="(.*?)" text="(.*?)"(.*?)>')
    if pattern.search(content):
        return pattern.search(content).group(2)

def get_first_import_job_log(content):
    pattern = re.compile('<a class=(.*?) href=(.*?)logs/(.*?)/Display">View Import Log(.*?)')
    if pattern.search(content):
        return pattern.search(content).group(3)

# Content modules and topics
# Returns ToC as JSON
# See https://docs.valence.desire2learn.com/res/content.html
# https://docs.valence.desire2learn.com/res/content.html#get--d2l-api-le-(version)-(orgUnitId)-content-toc
def get_toc(APP, org_id, session):
    api_url = f"{APP['brightspace_api']['le_url']}/{org_id}/content/toc"
    r = session.get(api_url, timeout=300)
    return r.text if r.status_code == 200 else None

def get_content_toc(APP, org_id):

    payload = {
        'url': f"{APP['brightspace_api']['le_url']}/{org_id}/content/toc",
        'method': 'GET',
    }

    json_response = middleware_d2l_api(APP, payload_data=payload)
    if 'status' not in json_response or json_response['status'] != 'success':
        raise Exception(f"API call {payload} failed: {json_response}")

    toc = json_response['data']

    return toc

# Top-level org id for this instance
# TODO could get this via API call
# GET /d2l/api/lp/(version)/organization/info¶
def get_instance_org_id(APP):

    if 'orgId' in APP['brightspace_api']:
        return APP['brightspace_api']['orgId']

    return None


# Content Service
def get_contentservice_endpoint(APP):

    # Get the Content Service endpoint
    payload = {
        'url': f"{APP['brightspace_api']['le_url']}/contentservice/config/endpoint",
        'method': 'GET',
    }

    json_response = middleware_d2l_api(APP, payload_data=payload)
    if 'status' not in json_response or json_response['status'] != 'success':
        raise Exception(f"API call {payload} failed: {json_response}")

    cs_endpoint = json_response['data']['Endpoint']

    return cs_endpoint

# TODO get via API
def get_tenant_id(APP):

    if 'tenantId' in APP['brightspace_api']:
        return APP['brightspace_api']['tenantId']

    return None

# Get a dict of imported content service ids and filenames for org_id
def get_imported_content(APP, org_id):

     # Get this from config
    tenantId = get_tenant_id(APP)

    # Endpoint
    cs_endpoint = get_contentservice_endpoint(APP)

    # Users owned by D2L Support for BCI imports
    # https://amathuba.uct.ac.za//d2l/api/lp/1.45//users/169

    # Search
    # Could also limit by clientApps=LmsCourseImport
    payload = {
        'url': f"{cs_endpoint}/api/{tenantId}/search/content?searchLocations=ou:{org_id}&size=1000&sort=createdAt:asc",
        'method': 'GET',
    }

    json_response = middleware_d2l_api(APP, payload_data=payload)
    if 'status' not in json_response or json_response['status'] != 'success':
        raise Exception(f"API call {payload} failed: {json_response}")

    search_result = json_response['data']

    if search_result['timed_out']:
        raise Exception("Search for content for org id {org_id} timed out")

    imported_content = {}

    for result in search_result['hits']['hits']:
        content_id = result['_source']['id']
        content_filename = result['_source']['lastRevTitle']
        imported_content[content_id] = content_filename

    return imported_content

# Get Brightspace roles
# https://docs.valence.desire2learn.com/res/user.html#get--d2l-api-lp-(version)-roles-
# Return a dictionary of role name to id
def get_brightspace_roles(APP):

    payload = {
        'url': f"{APP['brightspace_api']['lp_url']}/roles/",
        'method': 'GET',
    }

    json_response = middleware_d2l_api(APP, payload_data=payload)

    if 'status' in json_response and json_response['status'] == "NotFound":
        return None

    if 'status' not in json_response or json_response['status'] != 'success':
        raise Exception(f"API call {payload} failed: {json_response}")

    role_set = json_response['data']

    role_dict = {}
    for role in role_set:
        role_dict[role['DisplayName']] = role['Identifier']

    return role_dict

# Map username to internal Brightspace id
def get_brightspace_user(APP, username):

    if username is None:
        return None

    payload = {
        'url': f"{APP['brightspace_api']['lp_url']}/users/?userName={username}",
        'method': 'GET',
    }

    json_response = middleware_d2l_api(APP, payload_data=payload)

    if 'status' in json_response and json_response['status'] == "NotFound":
        return None

    if 'status' not in json_response or json_response['status'] != 'success':
        raise Exception(f"API call {payload} failed: {json_response}")

    return json_response['data']

# Update content item owner
def update_content_owner(APP, content_id, username = None, userid = None):

    # Convert the username to a Brightspace id
    if userid is None and username is not None:
        user = get_brightspace_user(APP, username)
        userid = user['UserId']

    if not userid:
        logging.warn(f"Skipping ownership update for content id {content_id}: {username} does not exist")
        return None

    logging.debug(f"Updating {content_id} ownership to owner {username}:{userid}")

    # Content Service identifiers
    tenantId = get_tenant_id(APP)
    cs_endpoint = get_contentservice_endpoint(APP)

    # Fields to update
    content_info = {
        'ownerId' : str(userid)
    }

    # Update
    payload = {
        'url': f"{cs_endpoint}/api/{tenantId}/content/{content_id}",
        'method': 'PUT',
        'payload': json.dumps(content_info)
    }

    json_response = middleware_d2l_api(APP, payload_data=payload)
    if 'status' not in json_response or json_response['status'] != 'success':
        raise Exception(f"API call {payload} failed: {json_response}")

    return json_response['data']

# Add user to this
def enroll_in_site(APP, eid, import_id, role_id):

    logging.info(f"enroll_in_site: {import_id} {eid} with role id {role_id}")

    # Resolve the user to a Brightspace user id
    user = get_brightspace_user(APP, eid)
    if not user:
        logging.warn(f"No Brightspace user found for {eid}")
        return True

    user_id = user['UserId']

    payload_data = {
            "OrgUnitId": int(import_id),
            "UserId": int(user_id),
            "RoleId": int(role_id),
            "IsCascading": False
        }

    payload = {
        'url': f"{APP['brightspace_api']['lp_url']}/enrollments/",
        'method': 'POST',
        'payload': json.dumps(payload_data)
    }

    json_response = middleware_d2l_api(APP, payload_data=payload)

    logging.info(f"Enrollment: got {json_response}")

    if 'status' not in json_response or json_response['status'] != 'success':
        raise Exception(f"API call {payload} failed: {json_response}")

    if json_response is not None and 'data' in json_response and 'UserId' in json_response['data']:
        # Success
        user_id = json_response['data']['UserId']
        logging.info(f"Enrolled username {eid} userid {user_id} in {import_id}")
        return True

    # {'data': 'User NNN (###) is Inactive', 'status': 'ERR'}
    valid_return = json_response is not None
    status_error = valid_return and 'status' in json_response and json_response['status'] == 'ERR' and 'data' in json_response
    user_inactive = status_error and 'is Inactive' in json_response['data']

    if user_inactive:
        logging.warning(f"Ignoring enrolment for {eid}, user is inactive in Brightspace")
        return True

    raise Exception(f"Could not enroll user {eid} in {import_id}: {json_response}")

# Adds a root module
# POST /d2l/api/le/(version)/(orgUnitId)/content/root/¶
def add_module(APP, org_id, new_module):

    payload = {
        'url': f"{APP['brightspace_api']['le_url']}/{org_id}/content/root/",
        'method': 'POST',
        'payload': json.dumps(new_module)
    }

    json_response = middleware_d2l_api(APP, payload_data=payload, retries=0)

    if 'status' not in json_response:
        raise Exception(f'Unable to update org unit info: {json_response}')
    else:
        if json_response['status'] != 'success':
            raise Exception(f'Unable to update org unit info: {json_response}')

    return json_response['data']

# Add a topic
# https://docs.valence.desire2learn.com/res/content.html#post--d2l-api-le-(version)-(orgUnitId)-content-modules-(moduleId)-structure-
# POST /d2l/api/le/(version)/(orgUnitId)/content/modules/(moduleId)/structure/¶
def add_topic(APP, org_id, module_id, new_topic):

    payload = {
        'url': f"{APP['brightspace_api']['le_url']}/{org_id}/content/modules/{module_id}/structure/",
        'method': 'POST',
        'payload': json.dumps(new_topic)
    }

    print(f"payload: {payload}")

    json_response = middleware_d2l_api(APP, payload_data=payload, retries=0)

    if 'status' not in json_response:
        raise Exception(f'Unable to update org unit info: {json_response}')
    else:
        if json_response['status'] != 'success':
            raise Exception(f'Unable to update org unit info: {json_response}')

    return json_response['data']
