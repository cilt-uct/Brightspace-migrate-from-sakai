#!/usr/bin/python3

## This script adds a prefix to the ID of the site - to differentiate imports
## REF: AMA-146

import sys
import os
import argparse
import logging

from datetime import datetime
from bs4 import BeautifulSoup

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *

def run(SITE_ID, APP, new_id):
    logging.info('Site: Changing site ID to: {}'.format(new_id))

    if APP['debug']:
        print(f'{SITE_ID} > {new_id}')

    xml_src = r'{}{}-archive/site.xml'.format(APP['archive_folder'], SITE_ID)
    with open(xml_src, 'r', encoding='utf8') as f:
        contents = f.read()

    tree = BeautifulSoup(contents, 'xml')
    root = tree.select_one("archive")

    if root:
        if APP['debug']:
            print("{} run: {}".format(root.attrs['site'], root.attrs['site'] == SITE_ID))

        # we have not run this script before - the site id is intact
        if root.attrs['site'] == SITE_ID:
            # root.attrs['site'] = new_id

            # with open(f"{xml_src}", 'w', encoding = 'utf-8') as file:
            #     file.write(str(tree))

            xml_folder = "{}{}-archive/".format(APP['archive_folder'], SITE_ID)
            qti_folder = "{}{}-archive/qti/".format(APP['archive_folder'], SITE_ID)

            archive_files = [entry for entry in os.scandir(xml_folder) if entry.name.endswith('.xml')]
            qti_files = [entry for entry in os.scandir(qti_folder) if entry.name.endswith('.xml')]

            xml_files = archive_files + qti_files

            for file in xml_files:
                if APP['debug']:
                    print(file.path)

                with open(f'{file.path}', 'r+', encoding='utf8') as f:
                    # read and replace content
                    content = f.read().replace(SITE_ID, new_id)
                    # reset file cursor and write to file
                    f.seek(0)
                    f.write(content)
                    f.truncate()

    if APP['debug']:
        print("all done")

    return True

def main():
    global APP
    parser = argparse.ArgumentParser(description="This script adds a prefix to the ID of the site - to differentiate imports",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    now = datetime.now()
    now_st = now.strftime("%Y%m%d_%H%M")

    run(args['SITE_ID'], APP, "{}_{}".format(args['SITE_ID'], now_st))

if __name__ == '__main__':
    main()
