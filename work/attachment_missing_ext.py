#!/usr/bin/python3

## Fix attachments missing extensions else raise an exception if no matching extension can be found
## REF: AMA-451

import sys
import os
import argparse
import mimetypes
import lxml.etree as ET
import logging
from pathlib import Path

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.logging_config
from lib.utils import rewrite_tool_ref

def run(SITE_ID, APP):
    logging.info('Attachments: fix missing extensions : {}'.format(SITE_ID))

    # map of tool attachment path components to tool XML file
    paths_map = APP['attachment']['paths']
    types_map = APP['attachment']['content-types']

    src_folder  = r'{}{}-archive/'.format(APP['archive_folder'], SITE_ID)
    xml_src = os.path.join(src_folder, "attachment.xml")

    if not os.path.exists(xml_src):
        logging.info(f"No attachments in {SITE_ID}")
        return

    parser = ET.XMLParser(recover=True)
    content_tree = ET.parse(xml_src, parser)

    rewrite = False

    # find each resource with an id that contains that extension
    for item in content_tree.xpath(".//resource"):

        src_id = item.get('id')

        # Extensions
        file_name, file_extension = os.path.splitext(item.get('id'))

        psrc = Path(src_id)
        if psrc.stem.startswith(".") and not psrc.suffix:
            logging.debug(f"dot-prefix name {src_id}")
            continue

        # Content-type
        content_type = item.get('content-type')

        if content_type == "application/octet-stream" and file_extension:
            continue

        target_ext = mimetypes.guess_extension(content_type, False)
        if target_ext is None and content_type in types_map:
            target_ext = types_map[content_type]

        if target_ext and file_extension.upper() == target_ext.upper():
            continue

        if file_extension and "http" not in src_id and "www" not in src_id and "://" not in src_id and len(file_extension) <= 5:
            continue

        target_id = f"{src_id}{target_ext}"

        if file_extension == "" or (target_ext and file_extension.upper() != target_ext.upper()):

            # Identify the tool from the attachment path:
            # /attachment/cb2e80f8-b405-48f1-8824-6c9a62fad12d_20221114_1251/Announcements/

            tool_ref = src_id.split('/')[3]

            if tool_ref in paths_map:
                tool_xml = paths_map[tool_ref]

                if target_ext:
                    rewrite = True
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

                    logging.info(f"Replaced id {src_id} with {target_id} for {content_type} in attachment.xml and {tool_xml}")
                    continue

                else:
                    raise Exception("No extension identified to use for {src_id}")

            else:
                # We don't know which tool this comes from, so find the entire reference in any matching XML file and update that
                logging.info(f"Attachment '{src_id}' type {content_type} target extension {target_ext} has non-toolid path segment: AMA-451")

                rewrite = True
                item.set('id', target_id)

                if target_ext:
                    tool_xml_files = [entry for entry in os.scandir(src_folder) if entry.name.endswith('.xml')]
                    for toolxml in tool_xml_files:

                        if (toolxml.name in ["archive.xml", "site.xml", "content.xml", "attachment.xml", "user.xml"]):
                            continue

                        target_id = f"{src_id}{target_ext}"
                        if rewrite_tool_ref(toolxml, src_id, target_id):
                            logging.info(f"Fixed path {src_id} in {toolxml.name}")

                    continue
                else:
                    raise Exception(f"No extension identified to use for {src_id}")

        if file_extension == "":
            raise Exception(f"Attachment '{item.get('id')}' type {content_type} missing extension: AMA-451")
        else:
            if target_ext:
                logging.warning(f"Attachment '{item.get('id')}' type {content_type} non-standard extension {file_extension}: expected {target_ext} AMA-451")

    if rewrite:
        # Update attachment.xml
        content_tree.write(xml_src, encoding='utf-8', xml_declaration=True)

def main():
    APP = config.config.APP
    parser = argparse.ArgumentParser(description="Check for restricted exensions in attachments",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
