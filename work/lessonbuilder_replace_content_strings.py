import sys
import os
import re
import shutil
import copy
import argparse
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import cssutils

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *

current = os.path.dirname(os.path.realpath(__file__)) 

# Function that replaces node text with app content: lesson_replace strings
def replace_with_text(st):
    for key, value in APP['content']['lesson_replace'].items():
        st = st.replace(key, value)
    return st

def run(SITE_ID, APP):
    logging.info('Lessons: Replace content strings with strings set in config : {}'.format(SITE_ID))

    xml_src = r'{}{}-archive/lessonbuilder.xml'.format(APP['archive_folder'], SITE_ID)
    xml_old = r'{}{}-archive/lessonbuilder.old'.format(APP['archive_folder'], SITE_ID)
    shutil.copyfile(xml_src, xml_old)

    tree = ET.parse(xml_src)
    root = tree.getroot()

    if root.tag == 'archive':
        for item in root.findall(".//item[@type='5']"):
            # pass the html here
            html = BeautifulSoup(replace_with_text(str(item.attrib['html'])), 'html.parser')
            
        item.set('html', str(html))
        tree.write(xml_src, encoding='utf-8', xml_declaration=True)

def main():
    global APP
    parser = argparse.ArgumentParser(description="Replace content strings with strings set in config ",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
