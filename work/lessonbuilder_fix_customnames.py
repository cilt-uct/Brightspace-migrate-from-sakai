#!/usr/bin/python3

## AMA-350 Embedded video files fail with custom name element without mp4 extension

import sys
import os
import shutil
import argparse
import xml.etree.ElementTree as ET
import logging

from pathlib import Path

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.logging_config
from lib.utils import remove_unwanted_characters

def run(SITE_ID, APP):
    logging.info(f'Lessons: AMA-350 : {SITE_ID}')

    xml_src = r'{}{}-archive/lessonbuilder.xml'.format(APP['archive_folder'], SITE_ID)
    remove_unwanted_characters(xml_src)

    tree = ET.parse(xml_src)
    root = tree.getroot()

    rewrite = False

    for item in root.findall(".//item[@type='7']"):

        if item.get('html') == "video/mp4" and not item.get('sakaiid').endswith(item.get('name')):
            filename = Path(item.get('sakaiid')).name
            print(f"item filename={filename} name={item.get('name')} sakaiid={item.get('sakaiid')}")
            item.set('name', filename)
            rewrite = True

    # Update the lessonbuilder XML
    if rewrite:
        logging.info(f"Updating {xml_src}")
        xml_old = r'{}{}-archive/lessonbuilder.old'.format(APP['archive_folder'], SITE_ID)
        shutil.copyfile(xml_src, xml_old)
        tree.write(xml_src, encoding='utf-8', xml_declaration=True)

def main():
    APP = config.config.APP
    parser = argparse.ArgumentParser(description="This script fixes AMA-350",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
