#!/usr/bin/python3

"""
## This script takes as input the 'lessonbuilder.xml' file inside the site-archive folder
## and replaces adds styling to Sakai tool names.
## REF: AMA-753
"""

import sys
import os
import argparse
import xml.etree.ElementTree as ET
import re
import shutil
import logging

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.logging_config
from lib.utils import remove_unwanted_characters, make_well_formed
from bs4 import BeautifulSoup


def run(SITE_ID, APP):
    logging.info('Highlight Sakai tools : {}'.format(SITE_ID))

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

            for tool in APP['lessons']['highlight_names']:
                pattern = re.compile(r'\b{}\b'.format(tool), re.IGNORECASE)
                occurrences = html.find_all(string=pattern)
                for rep in occurrences:
                    replacement = r'<span style="color: red; font-weight: bold;" data-type="tool">{}</span>'.format(tool)
                    highlighted = pattern.sub(replacement, rep)
                    highlighted_html = BeautifulSoup(highlighted, 'html.parser')
                    rep.replace_with(highlighted_html)
                    item.set('html', str(html))

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
