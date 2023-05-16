#!/usr/bin/python3

## This script takes as input the 'lessonbuilder.xml' file inside the site-archive folder
## and replace personalize text in Lessons {{firstname}}, {{lastname}}, and {{fullname}}
## REF: AMA-58

import sys
import os
import re
import shutil
import copy
import argparse 
# import xml.etree.ElementTree as ET
import lxml.etree as ET
from bs4 import BeautifulSoup

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *

REPLACE_DICT = [', {{firstname}}', 
                ', {{fullname}}',
                '{{firstname}}, ',
                '{{fullname}}, ',
                'for {{firstname}}',
                'for {{fullname}}',
                '{{firstname}} {{lastname}}, ',
                '{{fullname}}\'s', 
                '{{firstname}}\'s',
                '{{firstname}}, {{lastname}}',
                '{{firstname}}, {{lastname}}, {{fullname}}', 
                '{{firstname}}', '{{lastname}}', '{{fullname}}']

def run(SITE_ID, APP):
    logging.info('Lessons: Remove Personalization from : {}'.format(SITE_ID))

    xml_src = r'{}{}-archive/lessonbuilder.xml'.format(APP['archive_folder'], SITE_ID)
    xml_old = r'{}{}-archive/lessonbuilder.old'.format(APP['archive_folder'], SITE_ID)
    shutil.copyfile(xml_src, xml_old)

    remove_unwanted_characters(xml_src)

    # ET.register_namespace("sakai", "https://www.sakailms.org/")
    # parser = ET.XMLParser(recover=True)

    lesson_tree = ET.parse(xml_src)

    # in name attribute
    for item in lesson_tree.xpath(".//*[contains(@name,'firstname')]") + \
                lesson_tree.xpath(".//*[contains(@name,'lastname')]") + \
                lesson_tree.xpath(".//*[contains(@name,'fullname')]"):
        item.set('name', re.sub("|".join(sorted(REPLACE_DICT, key = len, reverse = True)), '', item.get('name')).strip())
        
        if APP['debug']:
            print(item.get('name'))

    # in description attribute
    for item in lesson_tree.xpath(".//*[contains(@description,'firstname')]") + \
                lesson_tree.xpath(".//*[contains(@description,'lastname')]") + \
                lesson_tree.xpath(".//*[contains(@description,'fullname')]"):
        item.set('description', re.sub("|".join(sorted(REPLACE_DICT, key = len, reverse = True)), '', item.get('description')).strip())

        if APP['debug']:
            print(item.get('description'))   

    # let's handle the html body
    for item in lesson_tree.xpath(".//item[@type='5' and contains(@html,'firstname')]") + \
                lesson_tree.xpath(".//item[@type='5' and contains(@html,'lastname')]") + \
                lesson_tree.xpath(".//item[@type='5' and contains(@html,'fullname')]"):

        html = BeautifulSoup(item.get('html'), 'html.parser')
        html = make_well_formed(html)

        new_html = re.sub("|".join(sorted(REPLACE_DICT, key = len, reverse = True)), '', str(html))

        item.set('html', str(new_html))

    lesson_tree.write(xml_src, encoding='utf-8', xml_declaration=True)
    logging.info(f'\tDone')
    
def main():
    global APP
    parser = argparse.ArgumentParser(description="This script takes as input the 'lessonbuilder.xml' file inside the site-archive folder and replace personalize text in Lessons {{firstname}}, {{lastname}}, and {{fullname}}",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())
    
    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
