#!/usr/bin/python3

## This script takes as input the 'lessonbuilder.xml' file inside the site-archive folder
## and replaces the h3 tags with h2 for specific headings
# Applies to:​
# - Reading Title​
# - Video Title​
# - Assignment Title​
# - Discussion Forum​
## REF: AMA-85

import sys
import os
import re
import shutil
import argparse
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *

def run(SITE_ID, APP):
    logging.info('Lessons: Fix headings : {}'.format(SITE_ID))

    xml_src = r'{}{}-archive/lessonbuilder.xml'.format(APP['archive_folder'], SITE_ID)
    xml_old = r'{}{}-archive/lessonbuilder.old'.format(APP['archive_folder'], SITE_ID)
    shutil.copyfile(xml_src, xml_old)

    remove_unwanted_characters(xml_src)

    tree = ET.parse(xml_src)
    root = tree.getroot()

    if root.tag == 'archive':

        for item in root.findall(".//item[@type='5']"):

            title = None
            parent = root.findall('.//item[@id="{}"]...'.format(item.attrib['id']))
            if len(parent) > 0:
                title = parent[0].attrib['title']

            html = BeautifulSoup(item.attrib['html'], 'html.parser')
            html = make_well_formed(html, title)

            for el in html.find_all(class_ = re.compile(r'(fa-book)|(fa-play-circle)|(fa-file-alt)​|(fa-file-text)|(fa-comments)')):
                if el.parent.name == 'h3':
                    el.parent.name = 'h2'

            for el in html.find_all(string = re.compile(r'(Reading Title)|(Video Title)|(Assignment Title)​|(Discussion Forum)')):
                if el.parent.name == 'h3':
                    el.parent.name = 'h2'

            # write_test_case(html)
            item.set('html', str(html))
            # print(ET.tostring(item))

        tree.write(xml_src, encoding='utf-8', xml_declaration=True)

def main():
    global APP
    parser = argparse.ArgumentParser(description="This script takes as input the 'lessonbuilder.xml' file inside the site-archive folder and replaces the h3 tags with h2 for specific headings",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
