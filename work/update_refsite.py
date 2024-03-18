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

# Updates course info
# PUT /d2l/api/lp/(version)/courses/(orgUnitId)
# TODO returns a 404, maybe needs oauth ?
def update_course_info(base_url, org_id, new_info, session):
    api_url = f"{base_url}/d2l/api/le/{D2L_API_LP_VERSION}/courses/{org_id}"
    print(f"Updating course info at {api_ull}")
    r = session.put(api_url, json=new_info, timeout=300)

    print(f"Return code: {r.status_code}")
    return r.text if r.status_code == 200 else None

def run(import_id, APP):

    logging.info(f'Updating site status for Brightspace reference site {import_id}')

    #login_url = f"{brightspace_url}/d2l/lp/auth/login/login.d2l"
    #brightspace_session = web_login(login_url, WEB_AUTH['username'], WEB_AUTH['password'])
    #brightspace_last_login = datetime.now()

    # Get the course offering info
    course_info = get_course_info(APP, import_id)
    print(f"Got course info:\n\n{course_info}\n")

    course_info['IsActive'] = False
    course_info['Semester'] = { "Identifier": "6653", "Name": "Converted", "Code": "sem_converted" }

    print(f"Updating course info to:\n\n{course_info}\n")
    #update_course_info(brightspace_url, import_id, course_info, brightspace_session)

    return

def main():
    global APP
    parser = argparse.ArgumentParser(description="Update reference site status and semester",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("IMPORT_ID", help="The org unit id of the imported site")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['IMPORT_ID'], APP)

if __name__ == '__main__':
    main()
