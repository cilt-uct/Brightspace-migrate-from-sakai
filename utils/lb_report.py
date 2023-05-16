#!/usr/bin/python3

## Report extensions used in Resources and attachments
## REF: AMA-316

import sys
import os
import shutil
import yaml
import argparse
import lxml.etree as ET

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *

def count_items(xml_src):

    if not os.path.exists(xml_src):
        raise Exception(f"{xml_src} not found")

    with open(xml_src, 'r') as f:
        contents = f.read()

    parser = ET.XMLParser(recover=True)
    content_tree = ET.parse(xml_src, parser)

    pagecount = 0
    itemcount = 0

    for item in content_tree.xpath(f".//page"):
        pagecount += 1

    typecount = {}
    for item in content_tree.xpath(f".//item"):
        itemtype = item.get('type')
        tp = f"type_{itemtype}"
        if tp in typecount:
            typecount[tp] += 1
        else:
            typecount[tp] = 1

        itemcount += 1

    # print(f"{xml_src} pages {pagecount} items {itemcount}")

    return [pagecount, itemcount, typecount]


def run(SITE_ID, APP):
    logging.debug('Content: identify extensions : {}'.format(SITE_ID))

    # restricted extensions
    restricted_ext = read_yaml(APP['content']['restricted-ext'])
    disallowed = restricted_ext['RESTRICTED_EXT']

    src_folder  = r'{}{}-archive/'.format(APP['archive_folder'], SITE_ID)

    [orig_p, orig_i, orig_tc ] = count_items(os.path.join(src_folder, "lessonbuilder.xml"))
    [java_p, java_i, java_tc ] = count_items(os.path.join(src_folder, "lessonbuilder.xml.orig"))
    [py_p, py_i, py_tc ] = count_items(os.path.join(src_folder, "lessonbuilder.xml"))

    if orig_p != java_p or java_p != py_p:
        print(f"ERROR {SITE_ID}: page count mismatch {orig_p}: {java_p} vs {py_p}")

    if java_i != py_i:
        print(f"ERROR: {SITE_ID}: item count mismatch pages: {orig_i} java_items: {java_i} python_items: {py_i} {java_tc} {py_tc}")

    if java_i == py_i and java_p == py_p:
        print(f"OK: {SITE_ID} {orig_p} pages items reduced from {orig_i} to {py_i}")
    
def main():
    global APP
    parser = argparse.ArgumentParser(description="Check for restricted exensions in attachments",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']
    
    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
