#!/usr/bin/python3

## Raise an exception if an attachment has a restricted extension
## REF: AMA-316

import sys
import os
import argparse
import lxml.etree as ET
import logging

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import read_yaml

def run(SITE_ID, APP):
    logging.info('Content: check restricted extensions : {}'.format(SITE_ID))

    # restricted extensions
    restricted_ext = read_yaml(APP['content']['restricted-ext'])
    disallowed = restricted_ext['RESTRICTED_EXT']

    # restricted content types
    disallowed_type = { "text/url" : "web links" }

    src_folder  = r'{}{}-archive/'.format(APP['archive_folder'], SITE_ID)
    xml_src = os.path.join(src_folder, "attachment.xml")

    if not os.path.exists(xml_src):
        logging.info(f"No attachments in {SITE_ID}")
        return

    parser = ET.XMLParser(recover=True)
    content_tree = ET.parse(xml_src, parser)

    # find each resource with an id that contains that extension
    for item in content_tree.xpath(".//resource"):

        # Extensions
        file_name, file_extension = os.path.splitext(item.get('id'))
        if file_extension and file_extension.upper().replace(".","") in disallowed:
            raise Exception(f"Attachment {item.get('id')} has restricted extension {file_extension}")

        # Content-type
        content_type = item.get('content-type')
        if content_type and content_type in disallowed_type and file_extension == "":
            raise Exception(f"Attachment '{item.get('id')}' is {content_type} without .URL extension: AMA-451")

def main():
    global APP
    parser = argparse.ArgumentParser(description="Check for restricted exensions in attachments",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
