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
from lib.d2l import get_imported_content, update_content_owner, get_brightspace_user
from lib.resources import get_resource_ids, get_content_owner

def find_resource_owner(site_folder, content_ids, filename):

    # There could be multiple videos with the same filename in different parts of the content tree,
    # owned by different users. We only use the first match here.
    for sakai_id in content_ids:
        if sakai_id.endswith("/" + filename):
            owner_info = get_content_owner(site_folder, sakai_id)
            if owner_info:
                return owner_info[1]

    return None

def run(SITE_ID, APP, import_id, started_by):

    logging.info(f'Updating content service ownership of media assets from {SITE_ID} in imported site {import_id}')

    site_folder = f"{APP['archive_folder']}{SITE_ID}-archive"

    # Options for assigning content item ownership
    # 1. The owner of this item in the site's resources
    # 2. The user who created the site
    # 3. The user who started the conversion (resolve from started_by_email)

    site_created_by = get_site_creator(APP, SITE_ID)
    creator_user = get_brightspace_user(APP, site_created_by)
    creator_id = creator_user['UserId'] if creator_user else None

    started_by_eid = get_user_by_email(APP, SITE_ID, started_by)
    started_by_user = get_brightspace_user(APP, started_by_eid)
    started_by_id = started_by_user['UserId'] if started_by_user else None

    default_owner_id = creator_id if creator_id else started_by_id

    logging.info(f"- site created by {site_created_by}:{creator_id}")
    logging.info(f"- conversion started by {started_by_eid}:{started_by_id}")
    logging.info(f"- default owner for content is user id {default_owner_id}")

    # Get the set of files from the Sakai site
    content_src = f'{site_folder}/content.xml'
    content_ids = get_resource_ids(content_src)

    # Get the content items from the Brightspace Content Service
    content_items = get_imported_content(APP, import_id)

    for content_id in content_items.keys():

        content_name = content_items[content_id]
        resource_owner_id = None
        resource_owner_eid = find_resource_owner(site_folder, content_ids, content_name)
        if resource_owner_eid:
            resource_owner_user = get_brightspace_user(APP, resource_owner_eid)
            if resource_owner_user:
                resource_owner_id = resource_owner_user['UserId']

        if resource_owner_id:
            logging.info(f"Updating owner of {content_name} to resource owner {resource_owner_eid}:{resource_owner_id}")
        else:
            logging.info(f"Updating owner of {content_name} to default owner {default_owner_id}")

        new_owner_id = resource_owner_id if resource_owner_id else default_owner_id

        if not update_content_owner(APP, content_id, userid=new_owner_id):
            logging.warning(f"Failed to update owner of {content_id}: {content_name} to {new_owner_id}")

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
