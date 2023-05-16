#!/usr/bin/python3

## This script takes as input the 'lessonbuilder.xml' file inside the site-archive folder
## and strips out custom formatting
## REF: AMA-106
import json
import sys
import os
import re
import shutil
import copy
import argparse
import xml.etree.ElementTree as ET

import cssutils
from bs4 import BeautifulSoup

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *

def run(SITE_ID, APP):

    with open(APP['lessons']['styles']) as json_file:
        config = json.load(json_file)

        logging.info('Lessons: Strip custom formatting : {}'.format(SITE_ID))

        xml_src = r'{}{}-archive/lessonbuilder.xml'.format(APP['archive_folder'], SITE_ID)
        xml_old = r'{}{}-archive/lessonbuilder.old'.format(APP['archive_folder'], SITE_ID)
        shutil.copyfile(xml_src, xml_old)

        remove_unwanted_characters(xml_src)

        tree = ET.parse(xml_src)
        root = tree.getroot()

        if root.tag == 'archive':

            for item in root.findall(".//item[@type='5']"):
                html_soup = BeautifulSoup(item.attrib['html'], 'html.parser')
                tags_to_search = config["general"]['tags.to.search']
                bad_attr = config["general"]["bad.attr"]
                for tag in html_soup.find_all(tags_to_search, style=lambda value: value and any(v in value for v in bad_attr)):
                    style = cssutils.parseStyle(tag['style'])
                    for attr in bad_attr:
                        style.removeProperty(attr)

                    if style.length > 0:
                        tag['style'] = style.cssText
                    else:
                        del tag['style']

                item.set('html', str(html_soup))

            tree.write(xml_src, encoding='utf-8', xml_declaration=True)

        logging.info(f'\tDone')


def main():
    global APP
    parser = argparse.ArgumentParser(description="This script takes as input the 'lessonbuilder.xml' file inside the site-archive folder and replace all the wiris math components with something Brightspace can use",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']
    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
