#!/usr/bin/python3

## Remove zero-byte files from content collection (Resources files)
## REF: AMA-419

import sys
import os
import shutil
import argparse
import lxml.etree as ET
import logging

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *

def run(SITE_ID, APP):
    logging.info('Content: remove zero-byte files : {}'.format(SITE_ID))

    src_folder  = r'{}{}-archive/'.format(APP['archive_folder'], SITE_ID)

    xml_src = r'{}/content.xml'.format(src_folder)

    parser = ET.XMLParser(recover=True)
    content_tree = ET.parse(xml_src, parser)

    found_zero_bytes = False

    # find each resource with a file length of 0
    for item in content_tree.xpath(".//resource[@content-length='0']"):
        filename = os.path.join(src_folder, item.get('body-location'))
        found_zero_bytes = True
        item.getparent().remove(item)
        os.remove(filename)
        logging.info(f"\tremoved zero-byte file: {item.get('id')}")

    # Rewrite the XML if we need to
    if found_zero_bytes:
        xml_old = r'{}/content.old.pre-zero'.format(src_folder)
        shutil.copyfile(xml_src, xml_old)
        content_tree.write(xml_src, encoding='utf-8', xml_declaration=True)

def main():
    global APP
    parser = argparse.ArgumentParser(description="Remove zero-byte files from content.xml and folder",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
