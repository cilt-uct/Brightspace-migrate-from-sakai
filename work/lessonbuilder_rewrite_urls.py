#!/usr/bin/python3

# Rewrite embedded URLs

import sys
import os
import re
import shutil
import copy
import argparse
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import cssutils
from pathlib import Path
from urllib.parse import urlparse

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *

def fix_unwanted_url_chars(currenturl, url_prefix):
    parsed_url = urlparse(url_prefix)

    if url_prefix in currenturl:
        urlparts = [s.strip(".") for s in currenturl.split("/") if s != 'https:']
        joined_link = "/".join(urlparts).replace("/", "", 1)
        joined_link = joined_link.replace(parsed_url.netloc + parsed_url.path, "..").replace("%3A", '').replace("!", "")
    elif currenturl.startswith('../'):
        joined_link = currenturl.replace("%3A", '').replace("!", "")
    else:
        joined_link = currenturl

    return joined_link

def run(SITE_ID, APP):
    logging.info(f'Lessons: Rewriting embedded URLs to relative paths : {SITE_ID}')

    xml_src = r'{}{}-archive/lessonbuilder.xml'.format(APP['archive_folder'], SITE_ID)
    remove_unwanted_characters(xml_src)

    tree = ET.parse(xml_src)
    root = tree.getroot()

    rewrite = False

    sakai_url = APP['sakai_url']
    url_prefix = f"{sakai_url}/access/content/group/{SITE_ID}"

    for item in root.findall(".//item[@type='5']"):

        html = BeautifulSoup(item.attrib['html'], 'html.parser')
        for attr in ['src', 'href']:
            for element in html.find_all(attrs={attr: True}):
                 element[attr] = fix_unwanted_url_chars(element.get(attr), url_prefix)
                 rewrite = True

        item.set('html', str(html))

    # Update the lessonbuilder XML
    if rewrite:
        logging.info(f"Updating {xml_src}")
        xml_old = r'{}{}-archive/lessonbuilder.old'.format(APP['archive_folder'], SITE_ID)
        shutil.copyfile(xml_src, xml_old)
        tree.write(xml_src, encoding='utf-8', xml_declaration=True)

def main():
    global APP
    parser = argparse.ArgumentParser(description="This script fixes embedded URLs in Lessons content",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
