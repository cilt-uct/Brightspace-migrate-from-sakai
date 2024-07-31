#!/usr/bin/python3

## Report orphaned Resources (not referenced from anywhere)
## REF: AMA-903

import sys
import os
import argparse
import urllib.parse
import logging

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.config
import config.logging_config
from lib.resources import get_resource_sizes

def orphaned(APP, SITE_ID, content_src):
    content_sizes = get_resource_sizes(content_src)
    content_ids = sorted(content_sizes.keys(), key=lambda s: s.casefold())
    used_ids = {}

    # Look at each XML file
    xml_folder = "{}{}-archive/".format(APP['archive_folder'], SITE_ID)
    qti_folder = "{}{}-archive/qti/".format(APP['archive_folder'], SITE_ID)

    archive_files = [entry for entry in os.scandir(xml_folder)
            if (entry.name.endswith('.xml') and entry.name not in ('content.xml', 'archive.xml')) ]
    qti_files = [entry for entry in os.scandir(qti_folder) if entry.name.endswith('.xml')]
    xml_files = archive_files + qti_files

    for xml_file in xml_files:
        # print(f"Checking file refs in {xml_file.name}")

        with open(xml_file.path, 'r') as file:
            content = file.read()

            for id in content_ids:

                if id not in used_ids:

                    url_id = urllib.parse.quote(id)

                    if id in content:
                        used_ids[id] = 'found-plain'
                        # print(f"{id} found in {xml_file.name}")
                    elif url_id in content:
                        used_ids[id] = 'found-escaped'
                        # print(f"{id} found escaped in {xml_file.name}")

    # Now check the ids that weren't found

    # Referenced files
    for id in content_ids:
        #print(f"used? {id}")
        if id in used_ids:
            print(f"USED: {content_sizes[id]} {id}")

    print("")

    # Orphaned files
    for id in content_ids:
        #print(f"used? {id}")
        if id not in used_ids:
            print(f"ORPHANED: {content_sizes[id]} {id}")

    return


def run(SITE_ID, APP):
    logging.info(f'Content: identify orphaned resources : {SITE_ID}\n')

    src_folder  = r'{}{}-archive/'.format(APP['archive_folder'], SITE_ID)

    content_src = os.path.join(src_folder, "content.xml")
    if not os.path.exists(content_src):
        print(f"ERROR {content_src} not found")
        return False

    orphaned(APP, SITE_ID, content_src)

def main():
    APP = config.config.APP
    parser = argparse.ArgumentParser(description="Check for restricted exensions in attachments",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']
    if APP['debug']:
        config.logging_config.logger.setLevel(logging.DEBUG)

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
