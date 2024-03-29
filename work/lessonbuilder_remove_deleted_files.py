#!/usr/bin/python3

## This script replaces audio, images and video files in lessonbuilder (with text) that have been removed
## from content (deleted resources)
## REF: AMA-100

import sys
import os
import argparse
import shutil
import lxml.etree as ET
import logging

from bs4 import BeautifulSoup

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import remove_unwanted_characters, make_well_formed

def is_deleted(item, content_xml, site_id):
    sakai_id = item.get("sakaiid")

    if sakai_id.startswith(f'/group/{site_id}'):
        # it is a valid reference to a resource

        for resource in content_xml.findall(f".//resource[@id='{sakai_id}']"):
            return False # so we did not find it
        return True

    return False

def update(item, SITE_ID):

    title = item.getparent().get('title')

    if APP['debug']:
        print(f"Updating item {item.get('id')} of type {item.get('html')}")
        # print("{} {} {}".format(item.get('id'), item.get('html'), title))

    content_path = str(item.get('sakaiid')).replace(f'/group/{SITE_ID}/', '')
    html = BeautifulSoup(f"<p><em>File not available: {content_path}</em></p>", 'html.parser')

    result = make_well_formed(html, title, "small")

    item.set("html", str(result))
    item.set("type", "5")
    item.set("name", title)
    item.set("sakaiid", "")

def write(file_name, xml):
    f = open(file_name, "w")
    xml.writexml(f)
    f.close()

def run(SITE_ID, APP):
    logging.info('Lessons: Remove Deleted Content from : {}'.format(SITE_ID))

    content_file = r'{}{}-archive/content.xml'.format(APP['archive_folder'], SITE_ID)
    lessons_file = r'{}{}-archive/lessonbuilder.xml'.format(APP['archive_folder'], SITE_ID)
    lessons_file_old = r'{}{}-archive/lessonbuilder.old'.format(APP['archive_folder'], SITE_ID)
    shutil.copyfile(lessons_file, lessons_file_old)

    remove_unwanted_characters(lessons_file)
    remove_unwanted_characters(content_file)

    ET.register_namespace("sakai", "https://www.sakailms.org/")
    parser = ET.XMLParser(recover=True)

    lesson_tree = ET.parse(lessons_file)
    content_tree = ET.parse(content_file, parser)

    # Get Embedded <item type="7" html="video/*" or html="audio/*"></item>
    # for item in lesson_tree.xpath(".//item[@type='7' and contains(@html,'video')]") \
    #             + lesson_tree.xpath(".//item[@type='7' and contains(@html,'audio')]"):

    # Type 7 is Multimedia
    # Type 1 is Resource
    for item in lesson_tree.xpath(".//item[@type='7']") \
                + lesson_tree.xpath(".//item[@type='1']"):

        # print("{} {} {} {} {}".format(item.get('type'), is_deleted(item, content_tree, SITE_ID), item.get('sakaiid'), item.get('name'), item.get('html')))

        if is_deleted(item, content_tree, SITE_ID):
            update(item, SITE_ID)

    # we can handle image files in another way later on - because they are type="5" (normal html)
    # <img ... src="https://[server]/access/content/[sakaiid]">

    lesson_tree.write(lessons_file, encoding='utf-8', xml_declaration=True)
    logging.info('\tDone')

def main():
    global APP
    parser = argparse.ArgumentParser(description="This script replaces audio, images and video files in lessonbuilder (with text) that have been removed from content (deleted resources)",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID to fix lessons")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
