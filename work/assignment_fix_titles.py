#!/usr/bin/python3

## Fix empty Assignment titles
## REF: AMA-454

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
    logging.info('Assignment: fix empty titles : {}'.format(SITE_ID))

    src_folder  = r'{}{}-archive/'.format(APP['archive_folder'], SITE_ID)
    xml_src = r'{}/assignment.xml'.format(src_folder)

    with open(xml_src, 'r') as f:
        contents = f.read()

    parser = ET.XMLParser(recover=True)
    asn_tree = ET.parse(xml_src, parser)

    ua = 1
    rewrite = False

    # find each resource with an id that contains that extension
    for asn in asn_tree.xpath(f"//Assignment/title[not(text())]"):
        asn.text = f"Untitled Assignment {ua}"
        ua += 1
        rewrite = True

    if rewrite:
        xml_old = r'{}/assignment.old'.format(src_folder)
        shutil.copyfile(xml_src, xml_old)
        asn_tree.write(xml_src, encoding='utf-8', xml_declaration=True)

def main():
    global APP
    parser = argparse.ArgumentParser(description="Fix empty Assignment titles",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
