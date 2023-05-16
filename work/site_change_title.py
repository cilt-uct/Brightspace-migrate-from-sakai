#!/usr/bin/python3

## This script adds a prefix to the title of the site
## REF: AMA-131

import sys
import os
import shutil
import argparse
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *

def run(SITE_ID, APP, now_st = None):

    if now_st is None:
        now = datetime.now()
        now_st = now.strftime("%d %b %y %H:%M")
    else:
        now = datetime.strptime(now_st, "%Y-%m-%d_%H%M%S")
        now_st = now.strftime("%d %b %y %H:%M")

    logging.info('Site: Add title prefix to: {} {}'.format(SITE_ID, now_st))

    xml_src = r'{}{}-archive/site.xml'.format(APP['archive_folder'], SITE_ID)
    xml_old = r'{}{}-archive/site.old'.format(APP['archive_folder'], SITE_ID)
    shutil.copyfile(xml_src, xml_old)

    with open(xml_src, 'r', encoding='utf8') as f:
        contents = f.read()

    tree = BeautifulSoup(contents, 'xml')
    site = tree.select_one("site[title]")

    if site:
        if APP['debug']:
            print(site.attrs['title'])

        if not site.attrs['title'].startswith(APP['site']['prefix']):
            original_title = site.attrs['title']
            site.attrs['title'] = "{}{} [{}]".format(APP['site']['prefix'], site.attrs['title'], now_st)
            site.attrs['original-title'] = original_title

            with open(f"{xml_src}", 'w', encoding = 'utf-8') as file:
                file.write(str(tree))

    return True

def main():
    global APP
    parser = argparse.ArgumentParser(description="This script adds a prefix to the title of the site",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
