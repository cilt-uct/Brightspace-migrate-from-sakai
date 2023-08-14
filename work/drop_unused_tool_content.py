#!/usr/bin/python3

## Drop tool content where the tools are not in the Sakai site,
## defined by drop-if-unused=true property in config/conversion_issues.json
## REF: AMA-473

import sys
import os
import shutil
import argparse
import lxml.etree as ET

from datetime import datetime, timedelta
from bs4 import BeautifulSoup

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *

def drop_content(toolid, archive_path):
    logging.info(f"Tool {toolid} is unused: dropping content")

    if not os.path.exists(archive_path):
        logging.warning("Archive file {archive_path} does not exist")
        return

    # Remove everything except the archive element
    tree = ET.parse(archive_path)
    archive_node = tree.getroot()

    if archive_node is not None:
        for child in list(archive_node):
            archive_node.remove(child)

        tree.write(archive_path, encoding='utf-8', xml_declaration=True)

def drop_attachments(site_folder, SITE_ID, path_segments):

    xml_src = os.path.join(site_folder, "attachment.xml")

    if not os.path.isfile(xml_src):
        logging.debug(f"Collection {xml_src} not found")
        return

    rewrite = False

    parser = ET.XMLParser(recover=True)
    content_tree = ET.parse(xml_src, parser)

    remove_items = []
    # find each resource with an id that contains one of the path segments
    for item in content_tree.xpath(".//resource"):

        src_id = item.get('id')
        remove = False

        for segment in path_segments:
            if src_id.startswith(f"/attachment/{SITE_ID}/{segment}/"):
                remove = True
                rewrite = True
                break

        if remove:
            # Delete the body and remove the element from the xml
            logging.info(f"Removing attachment {src_id}")
            resource_body = item.get('body-location')
            resource_file = os.path.join(site_folder, resource_body)
            if os.path.exists(resource_file):
                os.remove(resource_file)
            remove_items.append(item)

    if rewrite:
        # Remove attachment elements
        attachment_list = content_tree.find(".//org.sakaiproject.content.api.ContentHostingService")
        for item in remove_items:
            attachment_list.remove(item)

        # Update file
        xml_old = xml_src.replace(".xml",".old")
        shutil.copyfile(xml_src, xml_old)
        content_tree.write(xml_src, encoding='utf-8', xml_declaration=True)


def run(SITE_ID, APP):
    logging.info(f"Dropping content from unused tools: {SITE_ID}")

    with open(APP['report']['json']) as json_file:
        conf = json.load(json_file)

    # map of tool attachment path components to tool XML file
    paths_map = APP['attachment']['paths']

    drop_tools = list(filter(lambda i: 'drop-if-unused' in i and i['drop-if-unused'], conf['tools']))

    site_folder = r'{}{}-archive'.format(APP['archive_folder'], SITE_ID)

    # soups used in this dish
    site_soup = init__soup(site_folder, "site.xml")

    if not site_soup:
        raise Exception(f"site.xml not found - archive for {SITE_ID} may be incomplete or missing")

    # Build list of tools in use
    found_tool_keys = []
    for k in conf['tools']:
        if site_soup.find("tool", {"toolId": k['key']}):
            found_tool_keys.append(k['key'])

    drop_tools = list(filter(lambda i: 'drop-if-unused' in i and i['drop-if-unused'], conf['tools']))

    for tool in drop_tools:
        toolid = tool['key']
        if not toolid in found_tool_keys and 'archive' in tool:
            # Drop tool content
            drop_content(tool['key'], os.path.join(site_folder, tool['archive']))

            # Drop attachments
            path_segments = {i for i in paths_map if paths_map[i]==tool['archive']}
            if len(path_segments):
                drop_attachments(site_folder, SITE_ID, path_segments)

    return True

def main():
    global APP
    parser = argparse.ArgumentParser(description="This script drops tool content where the tool is unused",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
