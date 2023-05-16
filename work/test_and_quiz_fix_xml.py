#!/usr/bin/python3

## This script takes as input the xml files in the 'qti' folder - Test and Quizzes
## and removes unwanted characters
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

    path = r'{}{}-archive/qti'.format(APP['archive_folder'], SITE_ID)
    dir_list = os.listdir(path)
    
    logging.info('T&Q: Replace unwanted XML characters in : {}'.format(SITE_ID))
    
    for x in dir_list:
        remove_unwanted_characters_tq('{}{}-archive/qti/{}'.format(APP['archive_folder'], SITE_ID, x))
    
def main():
    global APP
    parser = argparse.ArgumentParser(description="This script takes as input the xml files in the 'qti' folder - Test and Quizzes and replaces unwanted characters",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())
    
    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
