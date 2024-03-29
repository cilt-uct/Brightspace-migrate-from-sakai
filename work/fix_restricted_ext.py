#!/usr/bin/python3

## AMA-316 Zip restricted files

import sys
import os
import shutil
import argparse
import zipfile
import lxml.etree as ET
import logging
from pathlib import Path

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import read_yaml, rewrite_tool_ref, get_size

def replace_with_zip(src_path, src_name):

    zip_file = src_path + ".zip"
    zipobj = zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED)
    zipobj.write(src_path, src_name)
    zipobj.close()

    shutil.move(zip_file, src_path)

    return True

def check_resources(src_folder, disallowed, paths_map, collection):

    xml_src = os.path.join(src_folder, collection)
    if not os.path.isfile(xml_src):
        logging.info(f"Collection {xml_src} not found")
        return None

    rewrite = False

    parser = ET.XMLParser(recover=True)
    content_tree = ET.parse(xml_src, parser)

    # find each resource with an id that contains that extension
    for item in content_tree.xpath(".//resource"):

        # Ignore URL resource types
        if item.get('resource-type') == "org.sakaiproject.content.types.urlResource":
            continue

        # Check restricted extensions
        file_name, file_extension = os.path.splitext(item.get('id'))
        if file_extension and file_extension.upper().replace(".","") in disallowed:

            rewrite = True

            # Zip the body, update the content-length, update the id and references to it
            src_id = item.get('id')
            resource_body = item.get('body-location')
            resource_file = os.path.join(src_folder, resource_body)

            target_id = src_id + ".zip"
            item.set('id', target_id)
            item.set('original-id', src_id)

            simple_name = Path(src_id).name
            replace_with_zip(resource_file, simple_name)

            if item.get('rel-id'):
                item.set('rel-id', item.get('rel-id') + ".zip")

            item.set('content-length', str(get_size(resource_file)))
            item.set('content-type', 'application/zip')

            # If this is an attachment, update the reference from elsewhere
            if collection == "attachment.xml":

                # Identify the tool from the attachment path:
                # /attachment/cb2e80f8-b405-48f1-8824-6c9a62fad12d_20221114_1251/Announcements/

                tool_ref = src_id.split('/')[3]

                if tool_ref in paths_map:
                    tool_xml = paths_map[tool_ref]
                    tool_src = os.path.join(src_folder, tool_xml)
                    item.set('id', target_id)

                    if tool_ref == "Tests_Quizzes":
                        # Assessments in qti/
                        qti_folder = f"{src_folder}/qti/"
                        qti_files = [entry for entry in os.scandir(qti_folder) if entry.name.endswith('.xml')]
                        for qti in qti_files:
                            rewrite_tool_ref(qti, src_id, target_id)

                        # Question Pools
                        qp = f"{src_folder}/samigo_question_pools.xml"
                        if os.path.exists(qp):
                            rewrite_tool_ref(qp, src_id, target_id)

                    else:
                        tool_src = os.path.join(src_folder, tool_xml)
                        rewrite_tool_ref(tool_src, src_id, target_id)

                    logging.info(f"Zipped {src_id} in {collection} and {tool_xml}")
                    continue

    if rewrite:
        # Update file
        xml_old = xml_src.replace(".xml",".old")
        shutil.copyfile(xml_src, xml_old)
        content_tree.write(xml_src, encoding='utf-8', xml_declaration=True)

    return True

def run(SITE_ID, APP):
    logging.info('Content: AMA-316 Zip restricted files : {}'.format(SITE_ID))

    # restricted extensions
    restricted_ext = read_yaml(APP['content']['restricted-ext'])
    disallowed = restricted_ext['RESTRICTED_EXT']

    # map of tool attachment path components to tool XML file
    paths_map = APP['attachment']['paths']

    src_folder  = r'{}{}-archive/'.format(APP['archive_folder'], SITE_ID)

    check_resources(src_folder, disallowed, paths_map, 'attachment.xml')
    check_resources(src_folder, disallowed, paths_map, 'content.xml')

def main():
    global APP
    parser = argparse.ArgumentParser(description="AMA-316 Zip restricted files",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
