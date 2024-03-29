#!/usr/bin/python3

## Raise exception for content paths over 230 characters
## https://jira.cilt.uct.ac.za/browse/AMA-748

import sys
import os
import argparse
import lxml.etree as ET
import logging

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *

def run(SITE_ID, APP):
    logging.info('Content: checking path length AMA-748 : {}'.format(SITE_ID))

    src_folder  = r'{}{}-archive/'.format(APP['archive_folder'], SITE_ID)
    xml_src = r'{}/content.xml'.format(src_folder)

    if os.path.isfile(xml_src):
        parser = ET.XMLParser(recover=True)
        content_tree = ET.parse(xml_src, parser)

        # find each resource with an id that contains that extension
        for item in content_tree.xpath(".//resource"):
            file_path = item.get('id')

            if len(file_path) > 230:
                raise Exception(f"Path too long ({len(file_path)} characters): {file_path}")
    else:
        logging.warning(f"No content.xml found for {SITE_ID}")

def main():
    global APP
    parser = argparse.ArgumentParser(description="AMA-748 Content path length",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
