# Update ownership of newly imported audio and video in Content Service
# AMA-810 AMA-836

import argparse
import os
import sys
import logging

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.logging_config
from lib.utils import get_site_creator, get_user_by_email
from lib.d2l import get_imported_content, update_content_owner

def run(SITE_ID, APP, import_id, started_by):

    logging.info(f'Updating content service ownership of media assets from {SITE_ID} in imported site {import_id}')

    # Options for assigning content item ownership
    # 1. The owner of this item in the site's resources
    # 2. The user who created the site
    # 3. The user who started the conversion (resolve from started_by_email)

    site_created_by = get_site_creator(APP, SITE_ID)
    started_by_eid = get_user_by_email(APP, SITE_ID, started_by)
    logging.info(f"- site {SITE_ID} created by {site_created_by}; conversion started by {started_by_eid}")

    # Get the content items
    content_items = get_imported_content(APP, import_id)

    default_owner = site_created_by if site_created_by else started_by_eid

    for content_id in content_items.keys():
        # TODO resolve content owner
        new_owner = default_owner

        if new_owner:
            if update_content_owner(APP, content_id, new_owner):
                logging.info(f"Updated owner of {content_id}: {content_items[content_id]} to {new_owner}")
            else:
                logging.warning(f"Could not update owner of {content_id}: {content_items[content_id]} to {new_owner}")

    return False

def main():
    APP = config.config.APP
    parser = argparse.ArgumentParser(description="Update ownership of imported content service items",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID to process")
    parser.add_argument("IMPORT_ID", help="The org unit id of the imported site")
    parser.add_argument("STARTED_BY", help="The email address of the user who started the site conversion")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP, args['IMPORT_ID'], args['STARTED_BY'])

if __name__ == '__main__':
    main()
