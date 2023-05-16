#!/usr/bin/python3

## This script takes as input the xml files in the 'qti' folder - Test and Quizzes
## and replace all the wiris math components with something Brightspace can use
## REF: AMA-67

import sys
import os
import re
import shutil
import copy
import argparse
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *

regex_wiris = re.compile('.*data-mathml.*')

def work_on_TQ(xml_src):

    # logging.info('SRC : {}'.format(xml_src))

    remove_unwanted_characters(xml_src)

    try:
        tree = ET.parse(xml_src)
        root = tree.getroot()

        # print(ET.tostring(root))
        if root.tag == 'questestinterop':

            for item in root.findall(".//mattext[@texttype='text/plain']"):
                if item.text:
                    if item.text.find('data-mathml') > 0:
                        # print(item.text)

                        html = BeautifulSoup(item.text, 'html.parser')

                        for el in html.findAll("img", {"class" : "Wirisformula"}):
                            math_ml_raw = el['data-mathml'].replace("«", "<").replace("»", ">").replace("¨", "\"").replace("§", "&")
                            math_ml = BeautifulSoup(math_ml_raw,'html.parser')
                            el.replace_with(math_ml)

                        # print(html)
                        item.text = '<![CDATA[' + str(html) + ']]>'

            tree.write(xml_src)
    except Exception as e:
        raise Exception(f'{xml_src} : {e}')

def run(SITE_ID, APP):

    path = r'{}{}-archive/qti'.format(APP['archive_folder'], SITE_ID)
    dir_list = os.listdir(path)

    logging.info('T&Q: Replace wiris in : {}'.format(SITE_ID))

    for x in dir_list:
        work_on_TQ('{}{}-archive/qti/{}'.format(APP['archive_folder'], SITE_ID, x))

def main():
    global APP
    parser = argparse.ArgumentParser(description="This script takes as input the xml files in the 'qti' folder - Test and Quizzes and replace all the wiris math components with something Brightspace can use",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
