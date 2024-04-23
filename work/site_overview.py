#!/usr/bin/python3

## This script adds the site description as a styled HTML file in Resources
## REF: AMA-84 / AMA-701

import sys
import os
import argparse
import logging
import base64
import lxml.etree as ET

from bs4 import BeautifulSoup

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.logging_config
from lib.resources import add_resource
from lib.utils import make_well_formed

def run(SITE_ID, APP):
    logging.info('Site Overview: convert to content page: {}'.format(SITE_ID))

    src_folder  = r'{}{}-archive'.format(APP['archive_folder'], SITE_ID)
    xml_src = r'{}/site.xml'.format(src_folder)
    output_file = r'{}/siteinfo.html'.format(src_folder)

    if not os.path.exists(xml_src):
        raise Exception(f"site.xml not found at {xml_src}")

    # Get the site description (HTML blob)
    parser = ET.XMLParser(recover=True)
    content_tree = ET.parse(xml_src, parser)
    site_el = content_tree.find(".//site")
    site_info_enc = site_el.get('description-enc')

    if not site_info_enc:
        logging.info("No site description found.")
        return

    site_info_html = base64.b64decode(site_info_enc).decode("utf-8")

    # Apply the same styling as used for Lessons pages
    body_soup = BeautifulSoup(site_info_html, 'html.parser')
    new_body = make_well_formed(body_soup, "Site Information", "styled")
    new_html = str(new_body.prettify())

    # Write html
    with open(output_file, "wb") as file:
        file.write(new_html.encode('utf-8'))

    # Add the output file to Resources
    add_resource(SITE_ID, src_folder, output_file, "Site Information", "text/html", "")

    return

def main():
    APP = config.config.APP
    parser = argparse.ArgumentParser(description="This script adds the site description as a styled html file in context.xml",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
