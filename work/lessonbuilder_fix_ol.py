#!/usr/bin/python3

## This script takes as input the 'lessonbuilder.xml' file inside the site-archive folder
## and replaces adds a class to the ol and removes styling on li
# OLD: <ol>
# NEW: <ol class="large-number">
# OLD: <li style="margin-left: 40.0px;">
# NEW: <li>
## REF: AMA-85

import sys
import os
import re
import shutil
import argparse
import xml.etree.ElementTree as ET
import logging

from bs4 import BeautifulSoup
import cssutils

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.logging_config
from lib.utils import remove_unwanted_characters, make_well_formed

def run(SITE_ID, APP):
    logging.info('Lessons: Fix OL and LI : {}'.format(SITE_ID))

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

            for ol in html.select('div[class="col-sm-10 offset-sm-1"] ol'):
                # we don't add the class to list elements inside other lists
                if ol.parent.name in ['ol', 'ul', 'li']:
                    continue
                ol['class'] = 'large-number'

            for li in html.find_all('li', style=re.compile(r'(40.0px)')):
                style = cssutils.parseStyle( li['style'] )
                style.removeProperty('margin-left')

                if (style.length > 0):
                    li['style'] = style.cssText
                else:
                    del li['style']

            # write_test_case(html)
            item.set('html', str(html))
            # print(ET.tostring(item))

        tree.write(xml_src, encoding='utf-8', xml_declaration=True)

def main():
    APP = config.config.APP
    parser = argparse.ArgumentParser(description="This script takes as input the 'lessonbuilder.xml' file inside the site-archive folder and replaces adds a class to the ol and removes styling on li",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
