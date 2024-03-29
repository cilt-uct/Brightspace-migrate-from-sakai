#!/usr/bin/python3

## This script takes as input the 'lessonbuilder.xml' file inside the site-archive folder
## and adds a default banner to the body if it doesn't exist yet
## REF: AMA-85

import sys
import os
import shutil
import argparse
import xml.etree.ElementTree as ET
import logging

from bs4 import BeautifulSoup

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import remove_unwanted_characters, make_well_formed

def run(SITE_ID, APP):
    logging.info('Lessons: Add Banner : {}'.format(SITE_ID))

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

            rows = html.select('body > div[class="container-fluid"] > div[class="row"]')
            if (len(rows) >= 1):
                # we have the first row in the body
                row = rows[0]

                banner = html.select('body div[class="col-12 banner-img"]')
                if (len(banner) == 0):
                    # there is no banner
                    col_tag = html.new_tag('div', **{"class":"col-12 banner-img"})
                    p_tag = html.new_tag('p')
                    img_tag = html.new_tag('img', alt="banner", src='/shared/HTML-Template-Library/HTML-Templates-V3/_assets/img/banner_03.jpg')

                    p_tag.append(img_tag)
                    col_tag.append(p_tag)
                    row.insert(0, col_tag)

            # write_test_case(html)
            item.set('html', str(html))
            # print(ET.tostring(item))

        tree.write(xml_src, encoding='utf-8', xml_declaration=True)

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
