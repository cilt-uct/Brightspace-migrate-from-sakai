# Opencast API support
# See also https://github.com/cilt-uct/Brightspace-Middleware/blob/main/d2l/services/web/project/opencast/opencast.py

import sys
import os
import logging
import requests
import json
import xmltodict
import tempfile
import zipfile
from requests.auth import HTTPDigestAuth
from urllib.parse import quote

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from lib.local_auth import getAuth

class Opencast(object):

    def __init__(
        self,
        server: str,
        username: str,
        password: str,
    ) -> None:
        """Instantiates library.

        Args:
            server (str): The URL of the Opencast Server
            username (str): The username to use
            password (str): The password to use
        """
        self.server = server
        self.username = username
        self.password = password

    # get asset properties
    def get_asset(self, eventId):
        url = f'{self.server}/assets/episode/{eventId}'

        response = requests.get(url, auth=HTTPDigestAuth(self.username, self.password), headers={'X-Requested-Auth':'Digest'})

        if response.status_code == 200:
            json = xmltodict.parse(response.text)
            return json

        return None

    # get a named file within an asset .zip file
    def get_asset_zip_contents(self, url, filename):
        url = url
        response = requests.get(url, auth=HTTPDigestAuth(self.username, self.password), headers={'X-Requested-Auth':'Digest'})

        json_s = ""

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            print(f"Saving zip to {tmp.name}")
            tmp.write(response.content)
            tmp.close()
            zip_in = zipfile.ZipFile(tmp.name, 'r')
            json_s = zip_in.read(filename)
            zip_in.close()
            os.unlink(tmp.name)

        return json_s

    # get a set of events
    def get_events(self, seriesId):
        url = f'{self.server}/api/events?filter=series:{seriesId}&sort=date:ASC&withpublications=true'

        response = requests.get(url, auth=HTTPDigestAuth(self.username, self.password), headers={'X-Requested-Auth':'Digest'})

        if response.status_code == 200:
            json = response.json()
            return json

        return None

    # get event data
    def get_event(self, eventId):
        url = f'{self.server}/api/events/{eventId}'
        response = requests.get(url, auth=HTTPDigestAuth(self.username, self.password), headers={'X-Requested-Auth':'Digest'})

        if response.status_code == 200:
            json = response.json()
            return json

        return None

    # get series id
    def get_series_acl(self, seriesId):
        url = f'{self.server}/api/series/{seriesId}/acl'
        response = requests.get(url, auth=HTTPDigestAuth(self.username, self.password), headers={'X-Requested-Auth':'Digest'})

        if response.status_code == 200:
            json = response.json()
            return json

        return None

    # update series id
    def update_series_acl(self, series_id, new_acls):

        json_data = json.dumps(new_acls)
        url_encoded_data = quote(json_data)
        payload = f"acl={url_encoded_data}"

        response = requests.put(url = f'{self.server}/api/series/{series_id}/acl',
                                auth=HTTPDigestAuth(self.username, self.password),
                                headers={'Content-Type': 'application/x-www-form-urlencoded',
                                         'X-REQUESTED-AUTH': 'Digest',
                                         'Accept': 'application/v1.3.0+json'},
                                data=payload)

        if response.status_code == 200:
            logging.debug("ACL updated successfully: " + response.text)
            return {'status': 'success', 'data': response.text}
        else:
            logging.debug("ACL update failed. Status code: " + response.text)
            return {'status': 'ERR', 'data': response.text}


# Extend the existing ACL for users in org_id
def extend_acl(existing_ACLs, org_id):

    # As these are for embedded LTI Content Items, we only need to add read permission
    new_acls_update = [
        {
            "allow": True,
            "action": "read",
            "role": f'{org_id}_Instructor'
        },
        {
            "allow": True,
            "action": "read",
            "role": f'{org_id}_Learner',
        }
    ]

    # check if new acls exists in data
    values_exist = all(item in existing_ACLs for item in new_acls_update)
    if values_exist:
        return False

    existing_ACLs.extend(new_acls_update)
    return True

# Called from workflow operation
def opencast_update_acls(APP, urls, import_id, target_site_id):

    if len(urls) == 0:
        return

    # Handle URLs of the form
    # https://media.uct.ac.za/lti/player/968e3f4e-f624-4506-a463-7f7729481381

    logging.info(f"Updating Opencast ACLs for sites {import_id},{target_site_id} for {len(urls)} items")

    ocAuth = getAuth('Opencast', ['username', 'password'])
    if ocAuth['valid']:
        oc_client = Opencast(APP['opencast']['base_url'], ocAuth['username'], ocAuth['password'])
    else:
        raise Exception('Opencast authentication required')

    series_ids = set()

    # Construct the set of series related to the events
    for url in urls:
        event_id = url.replace(f"{APP['opencast']['base_url']}{APP['opencast']['content_item_path']}", "")
        event_json = oc_client.get_event(event_id)
        if event_json is None:
            logging.warn(f"No Opencast series found for event {event_id}")
            continue

        series_ids.add(event_json['is_part_of'])

    # Update the ACLs for each series
    for series_id in series_ids:

        # Get ACL
        series_acl = oc_client.get_series_acl(series_id)

        logging.debug(f"Series {series_id} has ACL: {series_acl}")

        # Update if needed (if not anonymous or ROLE_AUTH)
        update = extend_acl(series_acl, import_id)
        if target_site_id is not None and int(target_site_id) > 0:
            update = update or extend_acl(series_acl, target_site_id)

        if update:
            logging.info(f"Updating Opencast Series ACL for series {series_id}")
            json_response = oc_client.update_series_acl(series_id, series_acl)
            if 'status' not in json_response or json_response['status'] != "success":
                raise Exception(f"Unable to update Opencast series {series_id} ACL: {json_response}")

    return
