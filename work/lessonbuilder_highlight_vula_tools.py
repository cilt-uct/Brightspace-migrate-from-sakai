#!/usr/bin/python3

"""
## This script takes as input the 'lessonbuilder.xml' file inside the site-archive folder
## and replaces adds styling to vula tool names.
## REF: AMA-753
"""

import sys
import os
import argparse
import xml.etree.ElementTree as ET

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *


def run(SITE_ID, APP):
    logging.info('Highlight Vula tools : {}'.format(SITE_ID))

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

            for tool in APP['vula_tools']:
                for rep in html.find_all(text=re.compile(tool, re.IGNORECASE)):
                    replacement = BeautifulSoup(r'<span style="color: red; font-weight: bold;">{}</span>'.format(rep))
                    rep.replace_with(replacement.span)
                    item.set('html', str(html))

            tree.write(xml_src, encoding='utf-8', xml_declaration=True)


def main():
    global APP
    parser = argparse.ArgumentParser(description="This script takes as input the 'lessonbuilder.xml' file inside the site-archive folder and replaces adds a class to the ol and removes styling on li",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)


if __name__ == '__main__':
    main()
