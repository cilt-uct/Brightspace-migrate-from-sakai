#!/usr/bin/python3

## This script takes as input samigo_question_pools.xml
## and replace all the wiris math components with something Brightspace can use
## REF: AMA-67

import sys
import os
import argparse
import lxml.etree as ET
import logging

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import remove_unwanted_characters, replace_wiris

def run(SITE_ID, APP):

    qpfile = '{}{}-archive/samigo_question_pools.xml'.format(APP['archive_folder'], SITE_ID)

    if os.path.isfile(qpfile):
        logging.info('T&Q: Question Pools - Replace wiris in : {}'.format(SITE_ID))
    else:
        logging.info('T&Q: Question Pools not present in : {}'.format(SITE_ID))
        return

    xml_src = r'{}{}-archive/samigo_question_pools.xml'.format(APP['archive_folder'], SITE_ID)

    remove_unwanted_characters(xml_src)

    tree = ET.parse(xml_src)
    root = tree.getroot()

    if root.tag == 'QuestionPools':

        for item in root.findall(".//mattext"):
            if item.text:
                if item.text.find('data-mathml') > 0:
                    item.text = ET.CDATA(replace_wiris(item.text.replace("<![CDATA[", "").replace("]]>", "")))

        tree.write(xml_src)

def main():
    global APP
    parser = argparse.ArgumentParser(description="This script takes as input samigo_question_pools.xml and replace all the wiris math components with something Brightspace can use",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
