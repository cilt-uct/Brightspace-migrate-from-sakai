#!/usr/bin/python3

## This script takes as input the syllabus.xml file inside the site-archive folder and:
## 1. applies an HTML template to base64-encoded html in syllabus_body-html: decode, update, encode, store
## https://jira.cilt.uct.ac.za/browse/AMA-213

import sys
import os
import shutil
import argparse
import lxml.etree as ET
import base64
import logging

from bs4 import BeautifulSoup
from pathlib import Path

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.logging_config

def run(SITE_ID, APP):
    logging.info('Syllabus: Attachments, export  html: {}'.format(SITE_ID))

    # Folder for html for packaging and import
    output_folder = "{}/{}-content".format(APP['output'], SITE_ID)

    attachment_src = r'{}{}-archive/attachment.xml'.format(APP['archive_folder'], SITE_ID)
    have_attachments = False

    if os.path.exists(attachment_src):
        # Update the paths (ids) for Course Outline attachment IDs
        attachment_tree = ET.parse(attachment_src)
        attachment_names = {}

        # find each resource with an id that contains that extension
        for item in attachment_tree.xpath(".//resource[contains(@id,'/Course Outline/')]"):
            path = Path(item.get('id'))
            filename = path.name
            new_path = f"/attachment/Course Outline/{filename}"

            if filename in attachment_names:
                path_parts = os.path.normpath(str(path)).split(os.sep)
                if len(path_parts) >= 2:
                    id = path_parts[-2]
                    filename = f'{id}_{filename}'
                    new_path = f"/attachment/Course Outline/{filename}"
                    attachment_names[filename] = 'used'
                else:
                    raise Exception(f"Could not rename file {filename} to resolve file name collision.")
            else:
                attachment_names[filename] = 'used'

            item.set('id', new_path)
            have_attachments = True

        # Save attachments if needed
        if have_attachments:
            attachment_old = r'{}{}-archive/attachment.old'.format(APP['archive_folder'], SITE_ID)
            shutil.copyfile(attachment_src, attachment_old)
            attachment_tree.write(attachment_src, xml_declaration=True)

    # Now rewrite the html
    with open(f'{parent}/templates/syllabus.html', 'r')as f:
        tmpl_contents = f.read()

    xml_src = r'{}{}-archive/syllabus.xml'.format(APP['archive_folder'], SITE_ID)
    xml_old = r'{}{}-archive/syllabus.old'.format(APP['archive_folder'], SITE_ID)
    shutil.copyfile(xml_src, xml_old)

    tree = ET.parse(xml_src)
    root = tree.getroot()

    # TODO don't replace if the template is already applied

    # Really expecting only one here
    for item in root.findall(".//asset"):

        # Original syllabus content
        syllabus_body_html = item.attrib['syllabus_body-html']
        html_bytes = base64.b64decode(syllabus_body_html)
        html = BeautifulSoup(html_bytes.decode('utf-8'), 'html.parser')

        # Change the attachment paths in html tree
        for a in html.find_all('a'):
            href = a.get('href')
            if href and href.startswith("/attachment/") and "Course Outline" in href:
                filename = Path(href).name
                a['href'] = f"attachment/Course Outline/{filename}"

        # Template
        tmpl_dom = BeautifulSoup(tmpl_contents, "html.parser")
        syllabus_content = tmpl_dom.find("div", id="content")

        # Add original content to the template
        syllabus_content.string.replace_with(html)

        # Write the html to the output folder for later import again
        new_html = tmpl_dom.prettify()
        html_updated_bytes = new_html.encode('utf-8')
        with open(os.path.join(output_folder, "Course Outline.html"), "wb") as file:
            file.write(html_updated_bytes)

        # Replace base64-encoded contents
        b64_bytes = base64.b64encode(html_updated_bytes)
        b64_str = b64_bytes.decode('utf-8')

        item.attrib['syllabus_body-html'] = b64_str

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
