#!/usr/bin/python3

## Force the mime-types for specific extentions
## REF: AMA-150

import sys
import os
import shutil
import argparse
import lxml.etree as ET

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *

def run(SITE_ID, APP):
    logging.info('Content: fix mime-types : {}'.format(SITE_ID))

    mime_types = read_yaml(APP['content']['mime-types'])

    src_folder  = r'{}{}-archive/'.format(APP['archive_folder'], SITE_ID)
    create_folders(src_folder)

    xml_src = r'{}/content.xml'.format(src_folder)
    xml_old = r'{}/content.old'.format(src_folder)
    shutil.copyfile(xml_src, xml_old)

    with open(xml_src, 'r') as f:
        contents = f.read()

    ET.register_namespace("sakai", "https://www.sakailms.org/")
    parser = ET.XMLParser(recover=True)

    content_tree = ET.parse(xml_src, parser)

    # through each of the file extensions
    for ext, type in mime_types['FILES'].items():

        # find each resource with an id that contains that extension
        for item in content_tree.xpath(f".//resource[contains(@id,'.{ext}')]"):
            file_name, file_extension = os.path.splitext(item.get('id'))

            # make sure the extension is found correctly
            if (f".{ext}" == file_extension):
                item.set('content-type', type)

    content_tree.write(xml_src, encoding='utf-8', xml_declaration=True)

def main():
    global APP
    parser = argparse.ArgumentParser(description="Force the mime-types for specific extentions",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
