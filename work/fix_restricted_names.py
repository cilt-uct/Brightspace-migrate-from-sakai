#!/usr/bin/python3

## Fix characters in file/folder IDs that are disallowed in Brightspace
## - mp4s with colons in the name e.g. "2022:10:17 zoom.mp4"
## https://jira.cilt.uct.ac.za/browse/AMA-517

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

from config.logging_config import *
from lib.utils import read_yaml, rewrite_tool_ref

def has_restricted(name, disallowed):

    for char in disallowed:
        if char in name:
            return True

    return False

def check_resources(src_folder, paths_map, collection, restricted_ext):

    disallowed_chars = (':', '+', u"\u000B")

    # Video and audio types we expect to be imported into Media Library
    supported_audio = restricted_ext['SUPPORTED_AUDIO']
    supported_video = restricted_ext['SUPPORTED_VIDEO']

    xml_src = os.path.join(src_folder, collection)
    if not os.path.isfile(xml_src):
        logging.debug(f"Collection {xml_src} not found")
        return None

    rewrite = False

    parser = ET.XMLParser(recover=True)
    content_tree = ET.parse(xml_src, parser)

    # find each resource which needs fixing
    for item in content_tree.xpath(".//resource"):

        # Check restricted names
        file_head, file_extension = os.path.splitext(item.get('id'))
        file_path, file_name = os.path.split(file_head)

        display_name_value = None
        display_names = item.xpath('./properties/property[@name="DAV:displayname"]')

        if display_names:
            display_name_el = display_names[0]
            display_name_value = base64.b64decode(display_name_el.get('value')).decode('utf-8')
        else:
            logging.debug(f"Item {item.get('id')} has no display name")
            continue

        logging.debug(f"checking {file_name}{file_extension} displayname {display_name_value}")

        file_extension = file_extension.upper().replace(".","")

        # Display names with HTML entity names
        # Fix some HTML entities in display name. There are lots of these, but fix the ones we run into.
        # https://www.w3.org/wiki/Common_HTML_entities_used_for_typography
        # The Brightspace importer converts these into numeric refs like &#8211; which causes lookup mismatches
        # for the media handling code later (check_for_placeholders).
        if display_name_value and '&' in display_name_value:
            display_name_value = display_name_value.replace("&ndash;","-").replace("&mdash;","-")
            display_name_el.set('value', base64.b64encode(display_name_value.encode('utf-8')))
            rewrite = True

        # Audio/video with colons in filename
        if (((file_extension in supported_audio) or (file_extension in supported_video)) and (has_restricted(file_name, disallowed_chars) or has_restricted(display_name_value, disallowed_chars))):

            rewrite = True
            src_id = item.get('id')
            src_rel_id = item.get('rel-id')

            target_id = src_id
            target_rel_id = src_rel_id

            # Fix id
            for char in disallowed_chars:

                # Replace only the filename element of the full path
                target_id = target_id.replace(file_name, file_name.replace(char,"_"))

                # Replace in the rel-id which is the relative path only
                if src_rel_id:
                    target_rel_id = target_rel_id.replace(char, "_")

                # The display name should not be an issue but seems to be treated as a filename by the D2L importer
                if display_name_value:
                    display_name_value = display_name_value.replace(char, "_")

            item.set('id', target_id)
            item.set('original-id', src_id)

            if src_rel_id:
                item.set('rel-id', target_rel_id)

            if display_name_value:
                display_name_el.set('value', base64.b64encode(display_name_value.encode('utf-8')))

            logging.info(f"Fixing {file_name}{file_extension}: new id {target_id} new rel-id {target_rel_id} new displayname {display_name_value}")

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

                    logging.info(f"Updated id {src_id} in {collection} and {tool_xml}")
                    continue

            else:

                # Replace the ID reference in any XML file (including Lessons)

                qti_folder = f"{src_folder}/qti/"

                archive_files = [entry for entry in os.scandir(src_folder) if entry.name.endswith('.xml')]
                qti_files = [entry for entry in os.scandir(qti_folder) if entry.name.endswith('.xml')]

                xml_files = archive_files + qti_files

                for file in xml_files:

                    with open(f'{file.path}', 'r+', encoding='utf8') as f:
                        # read and replace content
                        content = f.read().replace(src_id, target_id)
                        # reset file cursor and write to file
                        f.seek(0)
                        f.write(content)
                        f.truncate()

    if rewrite:
        # Update file
        xml_old = xml_src.replace(".xml",".old")
        shutil.copyfile(xml_src, xml_old)
        content_tree.write(xml_src, encoding='utf-8', xml_declaration=True)

    return True

def run(SITE_ID, APP):
    logging.info('Content: checking unsupported filenames : {}'.format(SITE_ID))

    # map of tool attachment path components to tool XML file
    paths_map = APP['attachment']['paths']

    src_folder  = r'{}{}-archive/'.format(APP['archive_folder'], SITE_ID)

    # restricted extensions
    restricted_ext = read_yaml(APP['content']['restricted-ext'])

    check_resources(src_folder, paths_map, 'attachment.xml', restricted_ext)
    check_resources(src_folder, paths_map, 'content.xml', restricted_ext)

def main():
    global APP
    parser = argparse.ArgumentParser(description="Check for restricted names",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
