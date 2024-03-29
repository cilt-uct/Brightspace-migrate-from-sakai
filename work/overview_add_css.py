#!/usr/bin/python3

## This script searches for 'Site Information.html' in context.xml and if found
## will add the the appropriate header (from templates/styled.html)
## REF: AMA-84

import sys
import os
import re
import argparse
import logging

from bs4 import BeautifulSoup

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import make_well_formed

def do_work(site_info_file, title):
    # print(site_info_file)

    with open(site_info_file, "r", encoding="utf8") as f:
        src_contents = f.read()

    with open(f'{parent}/templates/styled.html', 'r') as f:
        tmpl_contents = f.read()

    html = BeautifulSoup(src_contents, 'html.parser')
    tmpl = BeautifulSoup(tmpl_contents, 'html.parser')

    # remove previous meta and style links
    for rm in html.head.find_all(['meta', 'link']):
        rm.decompose()

    # add the appropriate meta and style links
    for tag in tmpl.head.find_all(['meta', 'link']):
        html.head.append(tag)

    body = html.find('body')
    contents = [str(tag) for tag in body.contents if tag.name is not None]
    body_contents = ''.join(contents)
    body_soup = BeautifulSoup(body_contents, 'html.parser')

    new_html = make_well_formed(body_soup, title)

    for rep in new_html.find_all(text=re.compile('Site Information.html')):
        rep.replace_with('Site Information')

    with open(f"{site_info_file}", "w", encoding='utf-8') as file:
        return file.write(str(new_html.prettify()))

    return 0

def run(SITE_ID, APP):
    logging.info('Overview: Add CSS to: {}'.format(SITE_ID))

    xml_src = r'{}{}-archive/content.xml'.format(APP['archive_folder'], SITE_ID)

    with open(xml_src, 'r', encoding='utf8') as f:
        contents = f.read()

    tree = BeautifulSoup(contents, 'xml')
    for item in tree.find_all('resource', {'rel-id': 'Site Information.html'}):
        # item['id'] = "/group/{}/Site Information".format(SITE_ID)
        # item['file-path'] = "/tmp/Site Information"
        # item['rel-id'] = "Site Information"
        item['content-length'] = do_work(
            r'{}{}-archive/{}'.format(APP['archive_folder'], SITE_ID, item['body-location']), item['rel-id'])

    with open(f"{xml_src}", 'w', encoding = 'utf-8') as file:
        file.write(str(tree))

    return True

def main():
    global APP
    parser = argparse.ArgumentParser(description="This script searches for 'Site Information.html' in context.xml and if found will add the the appropriate header (from templates/styled.html)",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
