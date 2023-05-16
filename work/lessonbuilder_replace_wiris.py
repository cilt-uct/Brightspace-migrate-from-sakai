#!/usr/bin/python3

## This script takes as input the 'lessonbuilder.xml' file inside the site-archive folder
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

def run(SITE_ID, APP):
    logging.info('Lessons: Replace wiris in : {}'.format(SITE_ID))

    xml_src = r'{}{}-archive/lessonbuilder.xml'.format(APP['archive_folder'], SITE_ID)
    xml_old = r'{}{}-archive/lessonbuilder.old'.format(APP['archive_folder'], SITE_ID)
    shutil.copyfile(xml_src, xml_old)

    remove_unwanted_characters(xml_src)

    tree = ET.parse(xml_src)
    root = tree.getroot()

    if root.tag == 'archive':

        for item in root.findall(".//item[@type='5']"):
            html = BeautifulSoup(item.attrib['html'], 'html.parser')
            html = make_well_formed(html)

            for el in html.body.findAll("img", {"class" : "Wirisformula"}):
                math_ml_raw = el['data-mathml'].replace("«", "<").replace("»", ">").replace("¨", "\"").replace("§", "&")
                math_ml = BeautifulSoup(math_ml_raw,'html.parser')
                el.replace_with(math_ml)

                # «math xmlns=¨http://www.w3.org/1998/Math/MathML¨»
                #     «msqrt»
                #         «mn»33«/mn»
                #     «/msqrt»
                # «/math»"
                # <math title="" xmlns="http://www.w3.org/1998/Math/MathML" display="inline">
                #     <semantics>
                #         <mstyle>
                #             <msqrt><mn>33</mn></msqrt>
                #         </mstyle>
                #     </semantics>
                # </math>

            # write_test_case(html)
            item.set('html', str(html))
            # print(ET.tostring(item))

        tree.write(xml_src)

def main():
    global APP
    parser = argparse.ArgumentParser(description="This script takes as input the 'lessonbuilder.xml' file inside the site-archive folder and replace all the wiris math components with something Brightspace can use",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
