#!/usr/bin/python3

## This script will check lessons and restructure the XML so that it does not pass 3 levels
## REF: AMA-94

import sys
import os
import argparse
import shutil
import lxml.etree as ET

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *
from lib.lessons import *

def update_page(page, level):
    page_title = page.get("title")
    page_id = page.get("pageid")

    if debug:
        print(f"Reading tree page title='{page_title}' id={page_id} level={level}")

    child_pages = lessonbuilder_root.xpath(f".//page[@parent='{page_id}']")
    child_page_count = len(child_pages)

    if child_page_count == 0:
        if debug:
            print("No child pages")
    else:
        if debug:
            print(f"{child_page_count} child page{'s' if child_page_count > 1 else ''}")

    for child_page in child_pages:
        update_page(child_page, level + 1)
        if level >= 3:
            move_down(page, page_title, page_id, child_page)

def move_down(page, page_title, page_id, child_page):
    child_page_title = child_page.get("title")

    if debug:
        print("Move items from {}({}) down to {}({})".format(
            child_page_title,
            child_page.get("pageid"),
            page_title,
            page_id
        ))

    items = child_page.xpath(".//item")
    if not items:
        if debug:
            print(f"No items in page {child_page_title}({child_page.get('pageid')}), ignoring page")
        return

    sequence = highest_sequence(page)
    for item in items:

        item_type = item.get('type')
        name = item.get("name")

        if debug:
            print(f"Moving item {item.get('id')}")

        sequence += 1
        item.set("pageId", page_id)
        item.set("sequence", str(sequence))
        item.set("id", str(new_item_id()))

        # Change the item name for text items only
        if item_type == ItemType.TEXT:

            if name:
                name = page_title + " - " + name
            else:
                name = page_title + " - " + child_page_title

            item.set("name", name)

        page.append(item)

    lessonbuilder_element.remove(child_page)

def highest_sequence(page):
    sequence = 1
    for item in page.findall(".//item[@sequence]"):
        item_sequence = int(item.get("sequence"))
        if item_sequence > sequence:
            sequence = item_sequence
    return sequence

def highest_item_id(root):
    highest_id = 1
    for item in root.findall(".//item[@id]"):
        item_id = int(item.get("id"))
        if item_id > highest_id:
            highest_id = item_id

    return highest_id

def new_item_id():
    global last_item_id
    last_item_id += 1

    return last_item_id

def get_top_parent(root):
    pages_with_top_parent = root.xpath(".//page[@topparent]")

    valid_top_parents = list(filter(lambda x: x.get('topparent') != '0', pages_with_top_parent))

    if debug:
        # print(pages_with_top_parent)
        print("Top parent LEN {}".format(len(valid_top_parents)))

    if len(valid_top_parents) == 0:
        # so we don't have a topparent value
        # see if we have ANY pages
        any_page = root.xpath(".//page")

        # if any_page has pages return the first one otherwise return empty
        return any_page[0] if any_page else None
    else:
        top_parent_id = valid_top_parents[0].get("topparent")
        if debug:
            print(f"Top parent id {top_parent_id}")

        return root.xpath(f".//page[@pageid='{top_parent_id}']")[0]

def run(SITE_ID, APP):
    global debug
    debug = APP['debug'] # :p

    logging.info('Lessons: Fix 3 levels : {}'.format(SITE_ID))

    xml_src = r'{}{}-archive/lessonbuilder.xml'.format(APP['archive_folder'], SITE_ID)
    xml_old = r'{}{}-archive/lessonbuilder.old'.format(APP['archive_folder'], SITE_ID)
    shutil.copyfile(xml_src, xml_old)

    remove_unwanted_characters(xml_src)

    lessonbuilder_xml = ET.parse(xml_src)
    global lessonbuilder_root # really a global variable to store the tree ?
    lessonbuilder_root = lessonbuilder_xml.getroot()

    section_count = len(lessonbuilder_root.xpath(".//item[@format='section']"))
    if section_count > 0:
        logging.warning(f"There are {section_count} section items in Lessons, exiting.")

    else:
        global lessonbuilder_element
        lessonbuilder_list = lessonbuilder_root.xpath(".//lessonbuilder")

        if len(lessonbuilder_list) > 0:
            lessonbuilder_element = lessonbuilder_list[0]

            global last_item_id
            last_item_id = highest_item_id(lessonbuilder_root)

            if debug:
                print(f"last_item_id {last_item_id}")

            top_parent_list = get_top_parent(lessonbuilder_root)

            if debug:
                print(f"top_parent_list {top_parent_list} {top_parent_list is not None}")

            if top_parent_list is not None:
                update_page(top_parent_list, 1)
                lessonbuilder_xml.write(xml_src, encoding='utf-8', xml_declaration=True)

                logging.info('\tDone')
            else:
                logging.info('No Lessons pages with topparent')
        else:
            logging.info('No Lesson pages.')

def main():
    global APP
    parser = argparse.ArgumentParser(description="This script will check lessons and restructure the XML so that it does not pass 3 levels",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID to change lessons for")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
