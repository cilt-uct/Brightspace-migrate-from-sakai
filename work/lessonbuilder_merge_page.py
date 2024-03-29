#!/usr/bin/python3

import sys
import os
import argparse
import base64
import logging
from bs4 import BeautifulSoup
from html import escape

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.config import *
from config.logging_config import *
from lib.utils import *
from lib.lessons import *
from lib.resources import *

def run(SITE_ID, APP):
    logging.info('Merge lessons page: {}'.format(SITE_ID))
    site_folder = APP['archive_folder']

    # List of valid resource IDs
    content_src = r'{}{}-archive/content.xml'.format(site_folder, SITE_ID)
    content_ids = get_resource_ids(content_src)

    xml_src = r'{}{}-archive/lessonbuilder.xml'.format(site_folder, SITE_ID)
    xml_old = r'{}{}-archive/lessonbuilder.old'.format(site_folder, SITE_ID)
    shutil.copyfile(xml_src, xml_old)

    remove_unwanted_characters(xml_src)

    file_path = os.path.join(site_folder, xml_src)

    with open(file_path, "r", encoding="utf8") as fp:
        soup = BeautifulSoup(fp, 'xml')
        pages = soup.find_all('page')
        for page in pages:
            merged = BeautifulSoup('<div></div>', 'html.parser')
            items = page.find_all('item')
            for item in items:

                html = None

                if item['type'] == ItemType.TEXT:
                    html = BeautifulSoup(item.attrs['html'], 'html.parser')

                if item['type'] in (ItemType.RESOURCE, ItemType.MULTIMEDIA):

                    # encode the SakaiID to avoid the D2L importer or anything else changing it
                    sakai_id = item.attrs["sakaiid"]
                    sakai_id_enc = base64.b64encode(sakai_id.encode("utf-8")).decode("utf-8")

                    content_type = item.attrs['html'] if 'html' in item.attrs else None
                    link_name = item.attrs["name"]

                    # Is this a valid id, i.e. this ID exists in content.xml
                    if sakai_id.startswith("/group/") and sakai_id not in content_ids:
                        logging.info(f'Missing item for name: {link_name}; type: {content_type}; id: {sakai_id}')
                        html = BeautifulSoup(f'<p style="border-style:solid;" data-type="missing-content" data-item-type="{item["type"]}" data-sakai-id="{sakai_id_enc}" data-name="{link_name}"><span style="font-weight:bold;">MISSING ITEM</span> [name: {link_name}; type: {content_type}]</p>', 'html.parser')
                    else:
                        if link_item(APP, content_type, sakai_id):
                            # Add a direct link to the item
                            href = f'{APP["sakai_url"]}/access/content{sakai_id}'
                            if 'description' in item.attrs:
                                desc = item.attrs['description']
                                html = BeautifulSoup(f'<p><a href="{href}">{link_name}</a><br>{escape(desc)}</p>', 'html.parser')
                            else:
                                html = BeautifulSoup(f'<p><a href="{href}">{link_name}</a></p>', 'html.parser')
                        else:
                            # Create a placeholder that will later be replaced with embed or link code (mostly video and audio)
                            logging.info(f'Placeholder for name: {item.attrs["name"]}; type: {item.attrs["html"]}; id: {sakai_id}')
                            html = BeautifulSoup(f'<p style="border-style:solid;" data-type="placeholder" data-item-type="{item["type"]}" data-sakai-id="{sakai_id_enc}" data-name="{link_name}"><span style="font-weight:bold;">PLACEHOLDER</span> [name: {link_name}; type: {content_type}]</p>', 'html.parser')

                if item['type'] == ItemType.BLTI:
                    # Embedded LTI Content Item launch
                    sakai_id = item["sakaiid"]
                    sakai_id_enc = base64.b64encode(sakai_id.encode("utf-8")).decode("utf-8")
                    link_name = item["name"]
                    link_desc = item["description"]

                    item_type = item.get("type")
                    item_format = item.get("format")

                    logging.info(f'Placeholder for LTI content: "{item["name"]}" id: {sakai_id} format: {item_format}')
                    html = BeautifulSoup(f'<p style="border-style:solid;" data-type="lti-content" data-display="{item_format}" data-item-type="{item_type}" data-sakai-id="{sakai_id_enc}" data-name="{link_name}"><span style="font-weight:bold;">LTI CONTENT</span> <em>{link_name} ({link_desc})</em></p>', 'html.parser')

                if html:
                    merged.div.append(html)

            updated_item = page.find('item', {'type': ItemType.TEXT})
            if updated_item:
                updated_item['html'] = str(merged)
                updated_item['data-merged'] = True

            for item in items:
                if not item.attrs.get('data-merged') and item.attrs.get('type') == ItemType.TEXT:
                    item.extract()

        updated_xml = soup.prettify()
        with open(file_path, 'w') as file:
            file.write(updated_xml)


def main():
    global APP
    parser = argparse.ArgumentParser(description="This script takes as input the 'lessonbuilder.xml' file inside "
                                                 "the site-archive folder and merges page content",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)


if __name__ == '__main__':
    main()
