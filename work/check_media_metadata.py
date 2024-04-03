#!/usr/bin/python3

## Transcode media to supported formats
## https://jira.cilt.uct.ac.za/browse/AMA-552

import sys
import os
import argparse
import lxml.etree as ET
import logging

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.logging_config
from lib.utils import read_yaml
from lib.ffprobe_uct import FFProbe_UCT

def check_resources(src_folder, restricted_ext, paths_map, collection):

    xml_src = os.path.join(src_folder, collection)
    if not os.path.isfile(xml_src):
        logging.info(f"Collection {xml_src} not found")
        return None

    parser = ET.XMLParser(recover=True)
    content_tree = ET.parse(xml_src, parser)

    # find each resource with an id that contains that extension
    for item in content_tree.xpath(".//resource"):

        content_type = item.get('content-type')
        src_id = item.get('id')
        file_size = item.get('content-length')

        if file_size == '0':
            # Definitely no content - ignore (it will be removed later)
            continue

        if content_type == "audio/x-mpegurl":
            # AMA-604 M3U files are plain text collections of resource identifiers
            continue

        if content_type.startswith('audio/') or content_type.startswith('video/'):

            resource_body = item.get('body-location')
            resource_file = os.path.join(src_folder, resource_body)

            metadata = None
            try:
                metadata = FFProbe_UCT(resource_file)
            except Exception:
                raise Exception(f"Unable to read metadata for media file {src_id} body {resource_file}")

            if metadata is None:
                raise Exception(f"Unable to read metadata for media file {src_id} body {resource_file}")

            if not metadata.audio and not metadata.video:
                raise Exception(f"No media tracks found in {src_id} {content_type} body {resource_file}")

    return True

def run(SITE_ID, APP):
    logging.info('Content: checking audio and video metadata AMA-552 : {}'.format(SITE_ID))

    # restricted extensions
    restricted_ext = read_yaml(APP['content']['restricted-ext'])

    # map of tool attachment path components to tool XML file
    paths_map = APP['attachment']['paths']

    src_folder  = r'{}{}-archive/'.format(APP['archive_folder'], SITE_ID)

    check_resources(src_folder, restricted_ext, paths_map, 'content.xml')

def main():
    APP = config.config.APP
    parser = argparse.ArgumentParser(description="Check for zero-byte files",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
