#!/usr/bin/python3

## Workflow operation to enroll users into the converted site
## REF: AMA-375

import sys
import os
import argparse
import lxml.etree as ET
import logging

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.logging_config
from lib.utils import enroll_in_site


def run(SITE_ID, APP, import_id):
    logging.info(f'Enroll users for {SITE_ID}')
    dir = r'{}{}-archive'.format(APP['archive_folder'], SITE_ID)
    site_xml_src = f'{dir}/site.xml'
    user_xml_src = f'{dir}/user.xml'

    # Types to enroll
    enroll_types = APP['users']['enroll_account_type']

    # Sakai to Brightspace role map
    enroll_map = APP['users']['enroll_role_map']

    if os.path.exists(site_xml_src) and os.path.exists(user_xml_src):
        site_tree = ET.parse(site_xml_src)
        user_tree = ET.parse(user_xml_src)

        try:
            # Enroll users whose role is in enroll_map and account_type in enroll_types
            for user_el in site_tree.xpath(".//ability"):
                user_id = user_el.get('userId')
                user_role = user_el.get('roleId')

                if user_role in enroll_map.keys():
                    details = user_tree.xpath(".//user[@id='{}']".format(user_id))

                    if len(details) > 0:
                        _eid = details[0].get('eid')
                        _type = details[0].get('type')
                        if (_type in enroll_types):
                            target_role = enroll_map[user_role]
                            logging.info(f"Enrolling user eid {_eid} (type={_type}, role={user_role}) in Brightspace site {import_id} (role={target_role})")
                            enroll_in_site(APP, _eid, import_id, target_role)

        except Exception as e:
            raise Exception(f'Could not enroll users from {SITE_ID} in Brightspacd site {import_id}') from e
    else:
        raise Exception(f'XML file does not exist anymore {dir}/site.xml or user.xml')

def main():
    APP = config.config.APP
    parser = argparse.ArgumentParser(description="Workflow operation to enroll users in the converted site",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument("IMPORT_ID", help="The Brightspace ID to enroll the users into")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP, args['IMPORT_ID'])

if __name__ == '__main__':
    main()
