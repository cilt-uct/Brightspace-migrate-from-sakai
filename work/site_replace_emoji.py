#!/usr/bin/python3

## This script replaces emoji's lessons/announcements/discussions/Q&A/Assignments/overview
## REF: AMA-119

import sys
import os
import shutil
import argparse

from datetime import datetime, timedelta
from bs4 import BeautifulSoup

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *

def run(SITE_ID, APP):
    logging.info('Site: Updating Emoji\'s path: {}'.format(SITE_ID))
    sakai_url = APP['sakai_url']

    xml_src = r'{}{}-archive/site.xml'.format(APP['archive_folder'], SITE_ID)
    with open(xml_src, 'r', encoding='utf8') as f:
        contents = f.read()

    tree = BeautifulSoup(contents, 'xml')
    root = tree.select_one("archive")
    
    if root:
        if APP['debug']:
            print("{} run: {}".format(root.attrs['site'], root.attrs['site'] == SITE_ID))

        xml_folder = "{}{}-archive/".format(APP['archive_folder'], SITE_ID)
        xml_files = [entry for entry in os.scandir(xml_folder) if entry.name.endswith('.xml')] + \
                        [entry for entry in os.scandir(f"{xml_folder}/qti") if entry.name.endswith('.xml')]

        for file in xml_files:
            if APP['debug']:
                print(file.path)

            with open(f'{file.path}', 'r+', encoding='utf8') as f:
                # read and replace content
                content = f.read().replace('/library/editor/ckeditor/plugins/smiley/images/', '/shared/HTML-Template-Library/HTML-Templates-V3/_assets/img/smiley/')
                content = content.replace(f'{sakai_url}/shared/','/shared/')
                # reset file cursor and write to file
                f.seek(0)
                f.write(content)
                f.truncate()
    return True
    
def main():
    global APP
    parser = argparse.ArgumentParser(description="This script replaces emoji's lessons/announcements/discussions/Q&A/Assignments/overview",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())
    
    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
