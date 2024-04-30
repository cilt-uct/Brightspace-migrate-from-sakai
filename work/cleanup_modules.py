import argparse
import os
import sys
import json
import logging
from jsonpath_ng.ext import parse

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.logging_config
from lib.local_auth import getAuth
from lib.d2l import web_login, get_toc

# Deletes module
# https://docs.valence.desire2learn.com/res/content.html#delete--d2l-api-le-(version)-(orgUnitId)-content-modules-(moduleId)
# DELETE /d2l/api/le/(version)/(orgUnitId)/content/modules/(moduleId)¶
def delete_module(APP, org_id, module_id, session):
    api_url = f"{APP['brightspace_api']['le_url']}/{org_id}/content/modules/{module_id}"
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

    return None


def run(SITE_ID, APP, import_id):

    logging.info(f'Cleanup topics for site {SITE_ID} import_id: {import_id}')

    # Login to fetch files directly
    WEB_AUTH = getAuth('BrightspaceWeb', ['username', 'password'])
    if not WEB_AUTH['valid']:
        raise Exception('Web Authentication required [BrightspaceWeb]')

    brightspace_url = APP['brightspace_url']

    login_url = f"{brightspace_url}/d2l/lp/auth/login/login.d2l"
    brightspace_session = web_login(login_url, WEB_AUTH['username'], WEB_AUTH['password'])

    # Get the ToC
    content_toc = json.loads(get_toc(APP, import_id, brightspace_session))

    # Quiz Images
    module_title = APP['quizzes']['image_collection']
    module_id = get_module_id(content_toc, module_title)
    if module_id:
        delete_module(APP, import_id, module_id, brightspace_session)

    # QNA
    module_title = APP['qna']['collection']
    module_id = get_module_id(content_toc, module_title)
    if module_id:
        delete_module(APP, import_id, module_id, brightspace_session)

    return

def main():
    APP = config.config.APP
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
