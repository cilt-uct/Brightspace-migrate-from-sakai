# Extended from NYU code to merge Lessons items on a page for D2L import:
# https://github.com/cilt-uct/sakai/blob/21.x/common/archive-impl/impl2/src/java/org/sakaiproject/archive/impl/LessonsRejigger.java
# AMA-449

import sys
import os
import re
import shutil
import copy
import argparse
import urllib.parse
import json
from bs4 import BeautifulSoup
from html import escape

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.lessons import *

def update_item_types(APP, items):

    sakai_url = APP['sakai_url']
    content_path_prefix= f"{sakai_url}/access/content"

    for item in items:
        content_path = item['sakaiid']

        item_html = item['html'] if 'html' in item.attrs else None

        # Inline images
        if item['type'] == ItemType.MULTIMEDIA and is_image(content_path, item_html):
            alt_text = item['alt']
            item['sakaiid'] = ''
            item['type'] = ItemType.TEXT
            item['name'] = alt_text

            img_path = urllib.parse.quote(content_path)
            item['html'] = f'<p><img style=\"max-width: 100%\" alt=\"{alt_text}\" src=\"{content_path_prefix}{img_path}\"></p>'
            continue

        # Page breaks
        if item['type'] == ItemType.BREAK and item['name']:
            name = item['name']
            html_name = f'<h2 class=\"section-heading\">{name}</h2>'
            item['html'] = html_name
            item['type'] = ItemType.TEXT
            continue

        # URLs
        if item['type'] in (ItemType.RESOURCE, ItemType.MULTIMEDIA) and item.find('attributes'):

            attr = item.find("attributes")
            aJson = attr.get_text()
            attributes = json.loads(aJson)

            # Links that are not embeds
            if 'multimediaUrl' in attributes and 'multimediaDisplayType' not in attributes:
                url = attributes['multimediaUrl']
                desc = item['description']
                name = item['name']

                if item['type'] == ItemType.MULTIMEDIA and desc:
                    link_html = f'<p><a href="{url}" target="_blank" rel="noopener">{url}</a><br>{desc}</p>'
                else:
                    link_html = f'<p><a href="{url}" target="_blank" rel="noopener">{name}</a></p>'

                item['type'] = ItemType.TEXT
                item['html'] = link_html
                attr.decompose()
                continue

            # Generic embed code
            if 'multimediaEmbedCode' in attributes:
                item['type'] = ItemType.TEXT
                item['html'] = generic_embed(attributes['multimediaEmbedCode'])
                attr.decompose()
                continue

            # Youtube or other known embed type
            if 'multimediaUrl' in attributes and 'multimediaDisplayType' in attributes:
                url = attributes['multimediaUrl']
                mmdt = attributes['multimediaDisplayType']
                name = item['name']

                if is_youtube(url):
                    (youtube_id, start_time) = parse_youtube(url)

                    logging.info(f"Embedding youtube video {youtube_id}")
                    item['type'] = ItemType.TEXT
                    item['html'] = youtube_embed(youtube_id, start_time, name)
                    attr.decompose()
                    continue

                if is_twitter(url):
                    embed = twitter_embed(url)
                    if embed:
                        logging.info(f"Embedding twitter URL {url}")
                        item['type'] = ItemType.TEXT
                        item['html'] = embed
                        attr.decompose()
                        continue

                if url and mmdt == '4':
                    # Generic embed: iframe it if the url returns text/html content type
                    if is_url_html(url):
                        embed = generic_iframe(url)
                        if embed:
                            logging.info(f"Embedding multimedia URL with iframe: {url}")
                            item['type'] = ItemType.TEXT
                            item['html'] = embed
                            attr.decompose()
                            continue

                if url and mmdt == '3':
                    # Generic link with description
                    if 'description' in item.attrs and item['description']:
                        desc = item['description']
                        html = f'<p><a href="{url}">{url}</a><br>{escape(desc)}</p>'
                    else:
                        html = f'<p><a href="{url}">{url}</a></p>'

                    item['type'] = ItemType.TEXT
                    item['html'] = html
                    continue


            # Plain link to internal resource, where we don't want to leave the resource
            # as a separate item because there is no D2L preview support for this type

            if (item['type'] in (ItemType.RESOURCE, ItemType.MULTIMEDIA)) and content_path:

                content_type = item['html'] if 'html' in item.attrs else None

                if not link_item(APP, content_type, content_path) and not is_audio_video(content_type, content_path):
                    href = f'{APP["sakai_url"]}/access/content{content_path}'
                    if 'description' in item.attrs and item['description']:
                        desc = item['description']
                        html = f'<p><a href="{href}">{item.attrs["name"]}</a><br>{escape(desc)}</p>'
                    else:
                        html = f'<p><a href="{href}">{item.attrs["name"]}</a></p>'

                    item['type'] = ItemType.TEXT
                    item['html'] = html
                    continue

    return items


def remove_adj_breaks(items):
    i = 0
    while i < len(items) - 1:
        # <break><break> => <break>
        if items[i]['type'] == ItemType.BREAK and items[i+1]['type'] == ItemType.BREAK:
            items.pop(i)
            i = i - 1
        i = i + 1
    return items


def remove_breaks(items):
    i = 0
    while i <= len(items) - 1:
        if items[i]['type'] == ItemType.BREAK:
            items.pop(i)
            i = i - 1
        i = i + 1
    return items


def remove_break_and_text(items):
    i = 1
    while i < len(items)-1:
        try:
            # <text><break><text> => <text w/ hr>
            if items[i-1]['type'] == ItemType.TEXT and \
                    items[i]['type'] == ItemType.BREAK \
                    and items[i+1]['type'] == ItemType.TEXT:
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
            if items[i]['type'] == ItemType.TEXT and items[i + 1]['type'] == ItemType.TEXT:
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
            if items[i]['type'] == ItemType.TEXT:
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

        if not items and not page.get('parent'):
            logging.info(f"Removing empty page with no parent: {page.get('pageid')} hidden: {page.get('hidden')} title: {page.get('title')}")
            page.decompose()
            continue

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
