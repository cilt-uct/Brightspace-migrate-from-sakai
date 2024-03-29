#!/usr/bin/python3

## Update access permissions as needed in external systems for LTI Content Item links
## Used for Opencast
## REF: AMA-885

import sys
import os
import argparse

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *
from lib.d2l import *
from lib.opencast import *
from lib.local_auth import *

def run(SITE_ID, APP, import_id, target_site_id = None):

    logging.info(f'Update external system access lists for site LTI Content Items: {import_id} {target_site_id}')

    org_links_ref = get_lti_links(APP, import_id)

    if target_site_id is not None and int(target_site_id) > 0:
        org_links_target = get_lti_links(APP, target_site_id)
    else:
        org_links_target = []

    link_map = {}
    prefixes = APP['lti']['content_item_urls']

    for link in org_links_ref + org_links_target:

        link_url = link['Url']

        for prefix in prefixes.keys():
            if link_url.startswith(prefix):
                link_type = prefixes[prefix]
                if link_type not in link_map:
                    link_map[link_type] = { 'urls' : [] }

                link_map[link_type]['urls'].append(link_url)

    if 'opencast' in link_map:
        opencast_update_acls(APP, link_map['opencast']['urls'], import_id, target_site_id)

    return

def main():
    global APP
    parser = argparse.ArgumentParser(description="This script will create a topic",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID to process")
    parser.add_argument("IMPORT_ID", help="The org unit id of the imported site")
    parser.add_argument("TARGET_SITE_ID", help="The org unit id of the new empty site")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP, args['IMPORT_ID'], args['TARGET_SITE_ID'])

if __name__ == '__main__':
    main()
