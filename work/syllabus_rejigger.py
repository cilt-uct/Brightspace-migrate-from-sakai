#!/usr/bin/python3

## This script takes as input the syllabus-archive.xml file inside the site-archive folder.
## https://jira.cilt.uct.ac.za/browse/AMA-700

import sys
import os
import shutil
import argparse
import lxml.etree as ET
import base64
import logging

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.logging_config

def run(SITE_ID, APP):
    xml_src = r'{}{}-archive/syllabus.xml'.format(APP['archive_folder'], SITE_ID)
    xml_old = r'{}{}-archive/syllabus.old'.format(APP['archive_folder'], SITE_ID)
    shutil.copyfile(xml_src, xml_old)

    tree = ET.parse(xml_src)
    root = tree.getroot()

    # Find syllabus_data nodes
    syllabus_data = root.findall(".//siteArchive/syllabus/syllabus_data")

    # Nothing to do here
    if len(syllabus_data) == 0:
        logging.info(f'Site {SITE_ID} has no syllabus data.')
        return

    content = []

    syllabus_data_index = 0

    # Build up content
    for merge_me in syllabus_data:
        title = merge_me.get("title")
        content.append(f"<h2>{title}</h2>\n\n")

        attachment_paths = []
        for child in merge_me:
            if child.tag == "asset":
                decoded = base64.b64decode(child.get("syllabus_body-html")).decode("utf-8")
                content.append(decoded)
            elif child.tag == "attachment":
                attachment_paths.append(child.get("relative-url").replace("/content", ""))

        if attachment_paths:
            content.append("\n\n<h3>Attachments</h3>\n")
            content.append("<ul>\n")
            for attachment in attachment_paths:
                content.append(f"<li><a href=\"{attachment}\">{os.path.basename(attachment)}</a></li>\n")
            content.append("</ul>\n")

        # Remove merged nodes
        if syllabus_data_index > 0:
            merge_me.getparent().remove(merge_me)

        syllabus_data_index = syllabus_data_index + 1

    # Page title
    root.set("title", "Course Outline")

    # Add modified content to the first syllabus_data node
    if syllabus_data:
        asset_node = syllabus_data[0].find(".//asset")
        if asset_node is not None:
            asset_node.set("syllabus_body-html", base64.b64encode("".join(content).encode("utf-8")).decode("utf-8"))

    # Write the modified XML to a new file
    logging.info(f'Site {SITE_ID} syllabus data has been updated.')
    tree.write(xml_src,  encoding='utf-8', xml_declaration=True)


def main():
    APP = config.config.APP
    parser = argparse.ArgumentParser(description="This script applies an HTML template to syllabus-archive.xml",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
