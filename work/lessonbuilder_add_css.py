#!/usr/bin/python3

## This script takes as input the 'lessonbuilder.xml' file inside the site-archive folder
## and makes sure that the HTML lesson item has the appropriate header (from templates/styled.html)
## REF: AMA-58

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
    logging.info('Lessons: Add CSS to : {}'.format(SITE_ID))

    xml_src = r'{}{}-archive/lessonbuilder.xml'.format(APP['archive_folder'], SITE_ID)
    xml_old = r'{}{}-archive/lessonbuilder.old'.format(APP['archive_folder'], SITE_ID)
    shutil.copyfile(xml_src, xml_old)

    remove_unwanted_characters(xml_src)

    tree = ET.parse(xml_src)
    root = tree.getroot()

    if root.tag == 'archive':

        for item in root.findall(".//item[@type='5']"):
            # print(item.attrib['html'])

            title = None
            parent = root.findall('.//item[@id="{}"]...'.format(item.attrib['id']))
            if len(parent) > 0:
                title = parent[0].attrib['title']

            html = BeautifulSoup(item.attrib['html'], 'html.parser')
            html = make_well_formed(html, title)
            # print(str(html))

            # remove background colours from p tags
            for p in html.find_all('p', style=re.compile(r'(d9edf7)|(ffefd6)|(255,239,214)|(217,237,247)')):
                style = cssutils.parseStyle( p['style'] )
                style.removeProperty('background-color')

                if (style.length > 0):
                    p['style'] = style.cssText
                else:
                    del p['style']

            # write_test_case(html)
            item.set('html', str(html))
            # print(ET.tostring(item))

        tree.write(xml_src, encoding='utf-8', xml_declaration=True)

def main():
    APP = config.config.APP
    parser = argparse.ArgumentParser(description="This script takes as input the 'lessonbuilder.xml' file inside the site-archive folder and makes sure that the HTML lesson item has the appropriate header (from templates/styled.html)",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
