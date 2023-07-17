#!/usr/bin/python3

## Report extensions used in Resources and attachments
## REF: AMA-316

import sys
import os
import shutil
import yaml
import argparse
import lxml.etree as ET
import base64

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *

def extensions(xml_src):

    if not os.path.exists(xml_src):
        return

    with open(xml_src, 'r') as f:
        contents = f.read()

    parser = ET.XMLParser(recover=True)
    content_tree = ET.parse(xml_src, parser)

    file_exts = {}
    mimes = {}

    # find each resource with an id that contains that extension
    for item in content_tree.xpath(f".//resource"):
        file_path = item.get('id')

        if len(file_path) > 230:
            print(f" Warning ID {file_path} length {len(file_path)}")

        file_name, file_extension = os.path.splitext(file_path)
        mime_type = item.get('content-type')

        # print(f"{file_path} {mime_type} ASCII: {file_path.isascii()}")
        display_names = item.xpath('./properties/property[@name="DAV:displayname"]')

        if display_names:
            display_name_el = display_names[0]
            display_name_value = base64.b64decode(display_name_el.get('value')).decode('utf-8')
            # print(f" display_name1: {display_name_value} ASCII: {display_name_value.isascii()}")

            display_name_value = display_name_value.replace(u"\u000B", "")
            # print(f" display_name2: {display_name_value} ASCII: {display_name_value.isascii()}")

        mimes[mime_type] = 'used'

        if file_extension:
            file_extension = file_extension.upper().replace(".","")
            file_exts[file_extension] = 'used'

    return [file_exts, mimes]


def run(SITE_ID, APP):
    logging.info('Content: identify extensions : {}'.format(SITE_ID))

    # restricted extensions
    restricted_ext = read_yaml(APP['content']['restricted-ext'])
    disallowed = restricted_ext['RESTRICTED_EXT']

    src_folder  = r'{}{}-archive/'.format(APP['archive_folder'], SITE_ID)

    xml_src = os.path.join(src_folder, "content.xml")
    if not os.path.exists(xml_src):
        print(f"ERROR Site {SITE_ID} not present in archive folder")
        return False

    [ext_set, mime_set]  = extensions(xml_src)
    if ext_set:
        print(f"Content extensions: {sorted(ext_set.keys())}")
    if mime_set:
        print(f"Content types: {sorted(mime_set.keys())}")
    else:
        print("No content")

    xml_src = os.path.join(src_folder, "attachment.xml")

    if os.path.exists(xml_src):

        [ext_set, mime_set]  = extensions(xml_src)
        if ext_set:
            print(f"Attachment extensions: {sorted(ext_set.keys())}")
        if mime_set:
            print(f"Attachment types: {sorted(mime_set.keys())}")
        else:
            print("No attachment")
    else:
        print("No attachments")

def main():
    global APP
    parser = argparse.ArgumentParser(description="Check for restricted exensions in attachments",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
