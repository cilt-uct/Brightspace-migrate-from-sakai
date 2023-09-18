# Python version of NYU code to merge Lessons items on a page for D2L import:
# https://github.com/cilt-uct/sakai/blob/21.x/common/archive-impl/impl2/src/java/org/sakaiproject/archive/impl/LessonsRejigger.java
# AMA-449

import sys
import os
import re
import shutil
import copy
import argparse
import urllib.parse
from bs4 import BeautifulSoup

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.lessons import *

# Lessons item types
# https://github.com/cilt-uct/sakai/blob/21.x/lessonbuilder/api/src/java/org/sakaiproject/lessonbuildertool/SimplePageItem.java#L36


def update_item_types(APP, items):

    sakai_url = APP['sakai_url']
    content_path_prefix= f"{sakai_url}/access/content"

    for item in items:
        content_path = item['sakaiid']

        item_html = item['html'] if 'html' in item else None

        if item['type'] == LessonType.MULTIMEDIA.value and is_image(content_path, item_html):
            alt_text = item['alt']
            item['sakaiid'] = ''
            item['type'] = LessonType.TEXT.value
            item['name'] = alt_text

            img_path = urllib.parse.quote(content_path)
            item['html'] = f'<p><img style=\"max-width: 100%\" alt=\"{alt_text}\" src=\"{content_path_prefix}{img_path}\"></p>'

        if item['type'] == LessonType.BREAK.value and item['name']:
            name = item['name']
            html_name = f'<h2 class=\"section-heading\">{name}</h2>'
            item['html'] = html_name
            item['type'] = LessonType.TEXT.value

    return items


def remove_adj_breaks(items):
    i = 0
    while i < len(items) - 1:
        # <break><break> => <break>
        if items[i]['type'] == LessonType.BREAK.value and items[i+1]['type'] == LessonType.BREAK.value:
            items.pop(i)
            i = i - 1
        i = i + 1
    return items


def remove_breaks(items):
    i = 0
    while i <= len(items) - 1:
        if items[i]['type'] == LessonType.BREAK.value:
            items.pop(i)
            i = i - 1
        i = i + 1
    return items


def remove_break_and_text(items):
    i = 1
    while i < len(items)-1:
        try:
            # <text><break><text> => <text w/ hr>
            if items[i-1]['type'] == LessonType.TEXT.value and \
                    items[i]['type'] == LessonType.BREAK.value \
                    and items[i+1]['type'] == LessonType.TEXT.value:
                victim = items.pop(i+1)
                items.pop(i)
                merged = items[i-1]
                merged['html'] = merged['html'] + "<hr>" + victim['html']
                i = i - 1
        except IndexError:
            return items

        i = i + 1
    return items


def merge_adj_text(items):
    i = 0
    while i < len(items) - 1:
        try:
            # <text><text> => <text>
            if items[i]['type'] == LessonType.TEXT.value and items[i + 1]['type'] == LessonType.TEXT.value:
                victim = items.pop(i + 1)
                merged = items[i]
                merged['html'] = merged['html'] + victim['html']
                i = i - 1
        except IndexError:
            return items

        i = i + 1
    return items


def name_nameless_items(items):
    i = 0
    while i <= len(items):
        try:
            if items[i]['type'] == LessonType.TEXT.value:
                if items[i]['name'] == '' or (i == 0 and is_image(items[i]['name'], None)):
                    html = BeautifulSoup(items[i]['html'], 'html.parser')

                    header = ''
                    generated_name = ''
                    if html.h1:
                        header = html.h1.text

                    if header != '':
                        generated_name = str(header)
                    else:
                        tags = html.find_all()
                        for tag in tags:
                            if tag.text is not None and tag.text != '':
                                generated_name = tag.text[0:30] + '...'
                                break

                    if generated_name is None or generated_name == '':
                        generated_name = 'Embedded Item'

                    items[i]['name'] = generated_name
                    i = i - 1
        except IndexError:
            return items

        i = i + 1
    return items


def is_image(att, content_type):

    if content_type and content_type.startswith("image/"):
        return True

    extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.jfif', '.pjpeg', '.pjp', '.ico', '.cur',
                  '.tif', '.tiff', '.webp']
    path = att.lower()
    for ex in extensions:
        if path.endswith(ex):
            return True


def run(SITE_ID, APP):

    logging.info(f"Merging Lessons items for {SITE_ID}")

    xml_src = r'{}{}-archive/lessonbuilder.xml'.format(APP['archive_folder'], SITE_ID)
    output = r'{}{}-archive/lessonbuilder.new'.format(APP['archive_folder'], SITE_ID)

    xml_dest = r'{}{}-archive/lessonbuilder.xml'.format(APP['archive_folder'], SITE_ID)
    xml_backup = r'{}{}-archive/lessonbuilder.xml.orig'.format(APP['archive_folder'], SITE_ID)

    if APP['debug']:
        ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
        xml_src = ROOT_DIR + '/../tests/test_files/input.xml'
        output = ROOT_DIR + '/../tests/test_files/output.xml'

    if not os.path.exists(xml_src):
        raise Exception(f"Lessonbuilder file {xml_src} not found")

    with open(xml_src, 'r') as f:
        data = f.read()

    all_xml = BeautifulSoup(data, "xml")
    lesson_builder = all_xml.find('lessonbuilder')
    pages = all_xml.find_all('page')

    for page in pages:
        items = page.find_all('item')

        items = update_item_types(APP, items)
        items = remove_adj_breaks(items)
        items = remove_break_and_text(items)
        items = merge_adj_text(items)
        items = remove_breaks(items)
        items = name_nameless_items(items)

        del page.contents
        page.contents = list(items)

        lesson_builder.append(page)

    with open(output, 'w') as f:
        f.write(all_xml.prettify())

    os.rename(xml_dest, xml_backup)
    os.rename(output, xml_dest)


def main():
    global APP
    parser = argparse.ArgumentParser(description="This script merges Lessons items",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)


if __name__ == '__main__':
    main()
