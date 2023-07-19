#!/usr/bin/python3

## Check for collections that have a name or a single or double full stop (dot)
## https://jira.cilt.uct.ac.za/browse/AMA-651
## https://sakaiproject.atlassian.net/browse/SAK-49101

import sys
import os
import shutil
import yaml
import argparse
import lxml.etree as ET

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *

def run(SITE_ID, APP):
    logging.info('Content: checking folder names valid AMA-651 : {}'.format(SITE_ID))

    src_folder  = r'{}{}-archive/'.format(APP['archive_folder'], SITE_ID)
    xml_src = r'{}/content.xml'.format(src_folder)

    if os.path.isfile(xml_src):
        with open(xml_src, 'r') as f:
            contents = f.read()

        parser = ET.XMLParser(recover=True)
        content_tree = ET.parse(xml_src, parser)

        # check potential collisions for each folder name
        for item in content_tree.xpath(".//collection"):
            collection_id = item.get('id')
            if collection_id.endswith("/./") or collection_id.endswith("/../"):
                raise Exception(f"AMA-651 Invalid folder name (single or double dot only): {collection_id}")
    else:
        logging.warning(f"No content.xml found for {SITE_ID}")

def main():
    global APP
    parser = argparse.ArgumentParser(description="AMA-651 Check that folder names are valid",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
