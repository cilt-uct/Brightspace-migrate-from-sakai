#!/usr/bin/python3

## REF: AMA-367 Embedded multimedia from other sites
# Move attachments from attachment.xml to content.xml

import sys
import os
import re
import shutil
import copy
import argparse
import xml.etree.ElementTree as ET

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *

def run(SITE_ID, APP):
    logging.info('Lessons: Cross-site resources : {}'.format(SITE_ID))

    src_folder  = '{}{}-archive/'.format(APP['archive_folder'], SITE_ID)

    # Lessons tree
    lb_src = r'{}/lessonbuilder.xml'.format(src_folder)
    remove_unwanted_characters(lb_src)
    lb_tree = ET.parse(lb_src)
    lb_root = lb_tree.getroot()

    # Attachments tree
    attach_root = None
    attach_container = None

    attach_src = r'{}/attachment.xml'.format(src_folder)
    if os.path.exists(attach_src):
        attach_tree = ET.parse(attach_src)
        attach_root = attach_tree.getroot()
        attach_container = attach_root.find("org.sakaiproject.content.api.ContentHostingService")

    # Content tree
    content_src = r'{}/content.xml'.format(src_folder)
    content_tree = ET.parse(content_src)
    content_root = content_tree.getroot()

    content_container = content_root.find("org.sakaiproject.content.api.ContentHostingService")

    updating = False

    # Cross-site embedded multimedia
    for item in lb_root.findall(".//item[@type='7']") + lb_root.findall(".//item[@type='1']"):

        itemId = item.get('id')
        sakaiId = item.get('sakaiid')

        if sakaiId.startswith("/group/"):
            resourceSiteId = sakaiId.split('/')[2]
            filename = sakaiId.split('/', 3)[3]

            if resourceSiteId != SITE_ID:

                if attach_root:
                    attachment_el = attach_root.find(f".//resource[@id='{sakaiId}']")
                else:
                    attachment_el = None

                if attachment_el:
                    embedItem = copy.deepcopy(attachment_el)

                    # Remove from attachments
                    attach_container.remove(attachment_el)

                    # Rewrite the id and add to content
                    newSakaiId = f"/group/{SITE_ID}/Lessons/{resourceSiteId}/{filename}"
                    embedItem.set('id', newSakaiId)
                    embedItem.set('rel-id', f"Lessons/{resourceSiteId}/{filename}")
                    content_container.append(embedItem)

                    # Update in Lessons
                    item.set('sakaiid', newSakaiId)

                    # Save
                    updating = True
                else:
                    raise Exception(f"Lessons item {itemId} embeds resource {sakaiId} which is not in the archive")

    if updating:
        logging.info("Updating Lessons, Attachments and Content for embedded multimedia items")
        lb_tree.write(lb_src, encoding='utf-8', xml_declaration=True)
        content_tree.write(content_src, encoding='utf-8', xml_declaration=True)
        attach_tree.write(attach_src, encoding='utf-8', xml_declaration=True)

    logging.info("Done")


def main():
    global APP
    parser = argparse.ArgumentParser(description="AMA-367 Cross-site Lessons resources",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
