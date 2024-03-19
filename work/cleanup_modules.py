import argparse
import os
import sys
import pprint
import json
import base64
from jsonpath_ng.ext import parse

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *
from lib.local_auth import *
from lib.lessons import *
from lib.resources import *

# Returns ToC as JSON
# See https://docs.valence.desire2learn.com/res/content.html
# https://docs.valence.desire2learn.com/res/content.html#get--d2l-api-le-(version)-(orgUnitId)-content-toc
def get_toc(base_url, org_id, session):
    api_url = f"{base_url}/d2l/api/le/{D2L_API_LE_VERSION}/{org_id}/content/toc"
    print(f"TOC from: {api_url}")
    r = session.get(api_url, timeout=300)
    return r.text if r.status_code == 200 else None

# Deletes module
# https://docs.valence.desire2learn.com/res/content.html#delete--d2l-api-le-(version)-(orgUnitId)-content-modules-(moduleId)
# DELETE /d2l/api/le/(version)/(orgUnitId)/content/modules/(moduleId)¶
def delete_module(base_url, org_id, module_id, session):
    api_url = f"{base_url}/d2l/api/le/{D2L_API_LE_VERSION}/{org_id}/content/modules/{module_id}"
    print(f"Deleting {api_url}")
    r = session.delete(api_url, timeout=300)
    return r.text if r.status_code == 200 else None

def get_module_id(content_toc, module_title):

    toplevel_resources = list(filter(lambda x: x['Title'] == 'Resources', content_toc['Modules']))

    jpe = f'$..Modules[?(@.Title=="{module_title}")]'
    jsonpath_expression = parse(jpe)
    module_matches = jsonpath_expression.find(toplevel_resources)

    if not module_matches:
        return None

    # There could be multiple matches
    for match in module_matches:
        return match.value['ModuleId']

    return Npone


def run(SITE_ID, APP, import_id):

    logging.info(f'Cleanup topics for site {SITE_ID} import_id: {import_id}')

    # Login to fetch files directly
    webAuth = getAuth('BrightspaceWeb')
    if (webAuth is not None):
        WEB_AUTH = {'username': webAuth[0], 'password' : webAuth[1]}
    else:
        raise Exception(f'Web Authentication required [BrightspaceWeb]')

    brightspace_url = APP['brightspace_url']

    login_url = f"{brightspace_url}/d2l/lp/auth/login/login.d2l"
    brightspace_session = web_login(login_url, WEB_AUTH['username'], WEB_AUTH['password'])
    brightspace_last_login = datetime.now()

    # Get the ToC
    content_toc = json.loads(get_toc(brightspace_url, import_id, brightspace_session))

    # Quiz Images
    module_title = APP['quizzes']['image_collection']
    module_id = get_module_id(content_toc, module_title)
    print(f"ModuleID for {module_title}: {module_id}")
    if module_id:
        delete_module(brightspace_url, import_id, module_id, brightspace_session)

    # QNA
    module_title = APP['qna']['collection']
    module_id = get_module_id(content_toc, module_title)
    print(f"ModuleID for {module_title}: {module_id}")
    if module_id:
        delete_module(brightspace_url, import_id, module_id, brightspace_session)

    return

def main():
    global APP
    parser = argparse.ArgumentParser(description="Check for placeholders in lessons and embed multimedia file",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID to process")
    parser.add_argument("IMPORT_ID", help="The org unit id of the imported site")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP, args['IMPORT_ID'])

if __name__ == '__main__':
    main()
