#!/usr/bin/python3

## This script takes as input the 'lessonbuilder.xml' file inside the site-archive folder
## and adds a default banner to the body if it doesn't exist yet
## REF: AMA-85

import sys
import os
import argparse
import xml.etree.ElementTree as ET
import logging

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.config import *
from config.logging_config import *
from lib.utils import *

def run(SITE_ID, APP):
    logging.info('XML: Parseable : {}'.format(SITE_ID))

    xml_folder = "{}{}-archive/".format(APP['archive_folder'], SITE_ID)
    qti_folder = "{}{}-archive/qti/".format(APP['archive_folder'], SITE_ID)

    archive_files = [entry for entry in os.scandir(xml_folder) if entry.name.endswith('.xml')]
    qti_files = [entry for entry in os.scandir(qti_folder) if entry.name.endswith('.xml')]
    xml_files = archive_files + qti_files

    for xml_file in xml_files:
        try:
            ET.parse(xml_file)
        except Exception as e:
            logging.error(f"Parse error for {xml_file.name}: {str(e)}")
            raise e

def main():
    global APP
    parser = argparse.ArgumentParser(description="This script takes as input the 'lessonbuilder.xml' file inside the site-archive folder and adds a default banner to the body if it doesn't exist yet",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
