#!/usr/bin/python3

## Check for zero-byte files
## https://jira.cilt.uct.ac.za/browse/AMA-419

import sys
import os
import argparse
import lxml.etree as ET

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *

def check_resources(src_folder, collection):

    xml_src = os.path.join(src_folder, collection)
    if not os.path.isfile(xml_src):
        logging.info(f"Collection {xml_src} not found")
        return None

    rewrite = False

    if os.path.isfile(xml_src):
        with open(xml_src, 'r') as f:
            contents = f.read()

        parser = ET.XMLParser(recover=True)
        content_tree = ET.parse(xml_src, parser)

        # Find zero-byte files
        for item in content_tree.xpath(".//resource[@content-length='0']"):
            resource_id = item.get('id')
            resource_body = item.get('body-location')
            resource_type = item.get('content-type')

            # Ignore text/url files which are redirects
            if resource_type != 'text/url':
                file_body_path = os.path.join(src_folder, resource_body)
                with open(file_body_path, 'wb') as binfile:
                        binfile.write(b'\x00')
                item.set('content-length', '1')
                rewrite = True
                logging.info(f"Replaced zero-byte {resource_id} body {resource_body} with single-byte file")

    if rewrite:
        # Update file
        xml_old = xml_src.replace(".xml",".old")
        shutil.copyfile(xml_src, xml_old)
        content_tree.write(xml_src, encoding='utf-8', xml_declaration=True)

    return True

def run(SITE_ID, APP):
    logging.info('Content: checking zero-byte files AMA-419 : {}'.format(SITE_ID))

    src_folder  = r'{}{}-archive/'.format(APP['archive_folder'], SITE_ID)

    check_resources(src_folder, 'attachment.xml')
    check_resources(src_folder, 'content.xml')

def main():
    global APP
    parser = argparse.ArgumentParser(description="Check for zero-byte files",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
