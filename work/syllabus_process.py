#!/usr/bin/python3

## AMA-213 AMA-700 This script takes as input the syllabus.xml file and
## 1. merges multiple syllabus items into a single document
## 2. rewrites attachment paths
## 3. applies the html page template
## 4. updates the syllabus.xml with the resulting html content

import sys
import os
import shutil
import argparse
import lxml.etree as ET
import base64
import logging

from bs4 import BeautifulSoup
from pathlib import Path
from html import escape
from urllib.parse import quote

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.logging_config
from lib.utils import make_well_formed

def run(SITE_ID, APP):
    logging.info('Syllabus: rewrite into one page: {}'.format(SITE_ID))

    attachment_src = r'{}{}-archive/attachment.xml'.format(APP['archive_folder'], SITE_ID)
    have_attachments = False

    # Shorten the attachment paths
    if os.path.exists(attachment_src):
        # Update the paths (ids) for Course Outline attachment IDs
        attachment_tree = ET.parse(attachment_src)
        attachment_names = {}

        # find each resource with an id that contains that extension
        for item in attachment_tree.xpath(".//resource[contains(@id,'/Course Outline/')]"):
            path = Path(item.get('id'))
            filename = path.name
            new_path = f"/attachment/course_outline/{filename}"

            if filename in attachment_names:
                path_parts = os.path.normpath(str(path)).split(os.sep)
                if len(path_parts) >= 2:
                    id = path_parts[-2]
                    filename = f'{id}_{filename}'
                    new_path = f"/attachment/course_outline/{filename}"
                    attachment_names[filename] = 'used'
                else:
                    raise Exception(f"Could not rename file {filename} to resolve file name collision.")
            else:
                attachment_names[filename] = 'used'

            item.set('id', new_path)
            have_attachments = True

        # Update attachment.xml if needed
        if have_attachments:
            attachment_old = r'{}{}-archive/attachment.old'.format(APP['archive_folder'], SITE_ID)
            shutil.copyfile(attachment_src, attachment_old)
            attachment_tree.write(attachment_src, xml_declaration=True)

    # Now rewrite the Syllabus file
    xml_src = r'{}{}-archive/syllabus.xml'.format(APP['archive_folder'], SITE_ID)
    xml_old = r'{}{}-archive/syllabus.old'.format(APP['archive_folder'], SITE_ID)
    shutil.copyfile(xml_src, xml_old)

    tree = ET.parse(xml_src)
    root = tree.getroot()

    # Find all syllabus items
    syllabus_data = root.findall(".//siteArchive/syllabus/syllabus_data")

    # Nothing to do here
    if len(syllabus_data) == 0:
        logging.info(f'Site {SITE_ID} has no syllabus data.')
        return

    content = "<h1>Course Outline</h1>\n"

    syllabus_data_index = 0

    # Build up content
    for syllabus_item in syllabus_data:

        # Item
        title = syllabus_item.get("title")
        content += f"<h2>{title}</h2>\n"

        # Item content
        asset = syllabus_item.find(".//asset")
        if asset is not None:
            decoded = base64.b64decode(asset.get("syllabus_body-html")).decode("utf-8")
            content += decoded

        # List of attachments
        if syllabus_item.find(".//attachment") is not None:
            content += "<ul>\n"
            for attachment in syllabus_item.findall(".//attachment"):
                filename = Path(attachment.get("relative-url")).name
                content += f"<li><a href=\"attachment/course_outline/{quote(filename)}\">{escape(filename)}</a></li>\n"
                syllabus_item.remove(attachment)
            content += "</ul>\n"

        # Remove merged nodes
        if syllabus_data_index == 0:
            syllabus_item.set("title", "Course Outline")
        else:
            syllabus_item.getparent().remove(syllabus_item)

        syllabus_data_index = syllabus_data_index + 1

    # Apply the template
    body_soup = BeautifulSoup(content, 'html.parser')
    new_body = make_well_formed(body_soup, "Course Outline", "styled")
    content = str(new_body)

    # Add the modified content to the first syllabus_data node
    if syllabus_data:
        asset_node = syllabus_data[0].find(".//asset")
        if asset_node is not None:
            asset_node.set("syllabus_body-html", base64.b64encode("".join(content).encode("utf-8")).decode("utf-8"))

    # Write the modified XML to a new file
    logging.info(f'Site {SITE_ID} syllabus data has been updated.')
    tree.write(xml_src, encoding='utf-8', xml_declaration=True)

def main():
    APP = config.config.APP
    parser = argparse.ArgumentParser(description="This script applies an HTML template to syllabus.xml",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
