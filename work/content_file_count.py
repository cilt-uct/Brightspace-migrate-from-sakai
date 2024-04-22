#!/usr/bin/python3

## Limit on number of files we're prepared to convert
## https://jira.cilt.uct.ac.za/browse/AMA-1079

import sys
import os
import argparse
import lxml.etree as ET
import logging

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.config
import config.logging_config

def run(SITE_ID, APP):

    logging.info(f'Content: checking number of files: {SITE_ID}')

    max_files = APP['content']['max_files']
    src_folder  = r'{}{}-archive/'.format(APP['archive_folder'], SITE_ID)
    xml_src = r'{}/content.xml'.format(src_folder)

    if os.path.isfile(xml_src):
        parser = ET.XMLParser(recover=True)
        content_tree = ET.parse(xml_src, parser)

        if content_tree.find(".//resource") is not None:
            resource_files = len(content_tree.findall(".//resource"))
            if resource_files >  max_files:
                raise Exception(f"Resources file count {resource_files} exceeds limit of {max_files}")
            else:
                logging.info(f"{resource_files} Resources files in {SITE_ID}")
        else:
            logging.info(f"No Resources files in {SITE_ID}")

    else:
        logging.warning(f"No content.xml found for {SITE_ID}")

def main():
    APP = config.config.APP
    parser = argparse.ArgumentParser(description="AMA-1079 Check number of files in Resources",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
