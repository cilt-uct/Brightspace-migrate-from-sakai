#!/usr/bin/python3

## Workflow operation to enrol site owners of converted site into reference and teaching site
## REF: AMA-375

import sys
import os
import argparse
import time
import json
import requests
import lxml.etree as ET

from requests.exceptions import HTTPError

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *
from lib.local_auth import *


def run(SITE_ID, APP, import_id):
    logging.info(f'Enroll users for {SITE_ID}')
    dir = r'{}{}-archive'.format(APP['archive_folder'], SITE_ID)
    site_xml_src = f'{dir}/site.xml'
    user_xml_src = f'{dir}/user.xml'

    # it would be beter to split this out into the original workflow and
    # create a column entry for this field so that even if the archive folder disapears
    # it can still be processed
    if os.path.exists(site_xml_src) and os.path.exists(user_xml_src):
        site_tree = ET.parse(site_xml_src)
        user_tree = ET.parse(user_xml_src)

        try:
            # get a array of role abilities for which the role is 'Support staff' or 'Site owner'
            # return the userId's in a list
            user_ids = list(map( lambda el: el.get('userId'), site_tree.xpath(".//ability[@roleId='Support staff']") + \
                                                            site_tree.xpath(".//ability[@roleId='Site owner']")))
            for user_id in user_ids:
                details = user_tree.xpath(".//user[@id='{}']".format(user_id))

                if len(details) > 0:
                    _eid = details[0].get('eid')
                    _type = details[0].get('type')
                    if (_type in APP['course']['enroll_user_type']):
                        find_user_and_enroll_in_site(APP, _eid, import_id, APP['course']['enroll_user_role'])

        except Exception as e:
            raise Exception(f'Could not enroll users from {SITE_ID} in Brightspacd site {import_id}') from e
    else:
        raise Exception(f'XML file does not exist anymore {dir}/site.xml or user.xml')

def main():
    global APP
    parser = argparse.ArgumentParser(description="Workflow operation to enrol site owners of converted site into reference and teaching site",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument("IMPORT_ID", help="The Brightspace ID to enroll the users into")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP, args['IMPORT_ID'])

if __name__ == '__main__':
    main()
