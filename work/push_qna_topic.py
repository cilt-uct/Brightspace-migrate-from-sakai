import argparse
import os
import sys
import json

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *
from lib.local_auth import *
from lib.lessons import *
from lib.resources import *

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


def run(SITE_ID, APP, import_id):

    site_folder = f"{APP['archive_folder']}{SITE_ID}-archive"

    if not os.path.exists(f"{site_folder}/qna.html"):
        logging.info("No Q&A output, skipping")
        return

    logging.info(f"Adding Q&A module and topic for site {import_id}")

    # Get the course offering info
    site_data = get_course_info(APP, import_id)

    # Create a top-level module
    # https://docs.valence.desire2learn.com/res/content.html
    # POST /d2l/api/le/(version)/(orgUnitId)/content/root/¶

    new_module = {
        "Title": "Q&A",
        "ShortTitle": "Q&A",
        "Type": 0,
        "ModuleStartDate": None,
        "ModuleEndDate": None,
        "ModuleDueDate": None,
        "IsHidden": True,
        "IsLocked": False
    }

    root_module = add_module(APP, import_id, new_module)
    module_id = root_module['Id']

    # Upload the file

    # Add a topic
    # https://docs.valence.desire2learn.com/res/content.html#post--d2l-api-le-(version)-(orgUnitId)-content-modules-(moduleId)-structure-
    # POST /d2l/api/le/(version)/(orgUnitId)/content/modules/(moduleId)/structure/¶

    co_path = site_data['Path']

    new_topic = {
        "Title": "Questions & Answers",
        "ShortTitle": "Q&A",
        "Type": 1,
        "TopicType": 1,
        "Url": f"{co_path}qna/qna.html",
        "StartDate": None,
        "EndDate": None,
        "DueDate": None,
        "IsHidden": False,
        "IsLocked": False,
        "OpenAsExternalResource": None,
        "Description": None,
        "MajorUpdate": None,
        "MajorUpdateText": "",
        "ResetCompletionTracking": None,
        "Duration": None
    }
    add_topic(APP, import_id, module_id, new_topic)

    return False

def main():
    global APP
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
