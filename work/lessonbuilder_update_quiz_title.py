#!/usr/bin/python3

import sys
import os
import argparse
import xml.etree.ElementTree as ET
import logging

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.config import *
from config.logging_config import *
from lib.utils import *


def run(SITE_ID, APP):
    logging.info('Lessons: Updating quiz title : {}'.format(SITE_ID))

    xml_src = r'{}{}-archive/lessonbuilder.xml'.format(APP['archive_folder'], SITE_ID)
    xml_old = r'{}{}-archive/lessonbuilder.old'.format(APP['archive_folder'], SITE_ID)
    shutil.copyfile(xml_src, xml_old)

    remove_unwanted_characters(xml_src)

    try:
        tree = ET.parse(xml_src)
        root = tree.getroot()

        pages = root.findall(".//page")

        for page in pages:
            questions = page.findall(".//item[@type='11']")

            for i, question in enumerate(questions):
                if len(questions) == 1:
                    question.set("name", "Question")
                else:
                    new_quiz_name = "Question {}".format(i + 1)
                    question.set("name", new_quiz_name)

        tree.write(xml_src, encoding="UTF-8", xml_declaration=True)

    except Exception as e:
        print(e)


def main():
    global APP
    parser = argparse.ArgumentParser(description="This script takes as input the 'lessonbuilder.xml' "
                                                 "file inside the site-archive folder and updates quiz titles",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
