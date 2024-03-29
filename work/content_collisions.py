#!/usr/bin/python3

## Check for collections named the same as files
## https://jira.cilt.uct.ac.za/browse/AMA-321

import sys
import os
import argparse
import lxml.etree as ET
import logging

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *

def run(SITE_ID, APP):
    logging.info('Content: checking collisions AMA-321 : {}'.format(SITE_ID))

    src_folder  = r'{}{}-archive/'.format(APP['archive_folder'], SITE_ID)
    xml_src = r'{}/content.xml'.format(src_folder)

    if os.path.isfile(xml_src):

        parser = ET.XMLParser(recover=True)
        content_tree = ET.parse(xml_src, parser)

        # check potential collisions for each folder name
        for item in content_tree.xpath(".//collection"):
            collection_id = item.get('id')[:-1]
            find = ET.XPath(".//resource[@id = $collection_id]")
            if find(content_tree, collection_id = collection_id):
                raise Exception(f"File/folder name collision: {collection_id}")
    else:
        logging.warning(f"No content.xml found for {SITE_ID}")

def main():
    global APP
    parser = argparse.ArgumentParser(description="Force the mime-types for specific extentions",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
