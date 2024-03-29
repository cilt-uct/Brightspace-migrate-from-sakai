#!/usr/bin/python3

# Testing stub for XML rewriting

import sys
import os
import shutil
import argparse
import xml.etree.ElementTree as ET
import logging

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *

def run(SITE_ID, APP):

        logging.info('XML rewrite test : {}'.format(SITE_ID))

        xml_src = r'{}{}-archive/lessonbuilder.xml'.format(APP['archive_folder'], SITE_ID)
        xml_old = r'{}{}-archive/lessonbuilder.old'.format(APP['archive_folder'], SITE_ID)
        shutil.copyfile(xml_src, xml_old)

        tree = ET.parse(xml_src)
        tree.write(xml_src, xml_declaration=True)

        logging.info('\tDone')

def main():
    global APP
    parser = argparse.ArgumentParser(description="XML rewrite test",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']
    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
