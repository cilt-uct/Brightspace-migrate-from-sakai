#!/usr/bin/python3

## Remove invalid URLs from content collection (Resources files)
## REF: AMA-885

import sys
import os
import shutil
import argparse
import lxml.etree as ET
import validators
import logging

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.logging_config

def run(SITE_ID, APP):
    logging.info('Content: remove invalid URLs : {}'.format(SITE_ID))

    src_folder  = r'{}{}-archive/'.format(APP['archive_folder'], SITE_ID)

    xml_src = r'{}/content.xml'.format(src_folder)

    parser = ET.XMLParser(recover=True)
    content_tree = ET.parse(xml_src, parser)

    found_invalid_url = False

    # find each URL item
    for item in content_tree.xpath(".//resource[@content-type='text/url']"):
        filename = os.path.join(src_folder, item.get('body-location'))
        with open(filename, 'r') as b:
            url = b.read()
            if not validators.url(url):
                found_invalid_url = True
                item.getparent().remove(item)
                os.remove(filename)
                logging.info(f"\tremoved invalid URL '{url}' in {item.get('id')}")

    # Rewrite the XML if we need to
    if found_invalid_url:
        xml_old = r'{}/content.old.pre-url'.format(src_folder)
        shutil.copyfile(xml_src, xml_old)
        content_tree.write(xml_src, encoding='utf-8', xml_declaration=True)

def main():
    APP = config.config.APP
    parser = argparse.ArgumentParser(description="Remove text/url resources with invalid URL targets from content.xml and folder",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
