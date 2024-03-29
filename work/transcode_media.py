#!/usr/bin/python3

## Transcode media to supported formats
## https://jira.cilt.uct.ac.za/browse/AMA-552

import sys
import os
import shutil
import argparse
import lxml.etree as ET
import base64
import logging

from pathlib import Path

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import read_yaml, rewrite_tool_ref, get_size
from lib.ffprobe_uct import FFProbe_UCT

def transcode(src_path):

    metadata = FFProbe_UCT(src_path)

    if metadata.audio and len(metadata.audio) == 1 and not metadata.video:
        # Single audio stream only
        codec = metadata.audio[0].codec_long_name

        if codec == "MP3 (MPEG audio layer 3)":
            return ("audio/mp3", "mp3")

        # Another audio format: convert to m4a / AAC
        dest_path = src_path + ".m4a"
        ffmpeg_cmd = f"/usr/bin/ffmpeg -i {src_path}  -c:a aac -b:a 384k {dest_path}"
        logging.info(f"Transcoding: {ffmpeg_cmd}")
        os.system(ffmpeg_cmd)

        if os.path.exists(dest_path):
            shutil.move(dest_path, src_path)
            return ("audio/mp4", "m4a")
        else:
            raise Exception(f"Transcoding failed: {ffmpeg_cmd}")

    if metadata.video:
        # Video: transcode to mp4, H264, AAC
        dest_path = src_path + ".mp4"
        ffmpeg_cmd = f"/usr/bin/ffmpeg -i {src_path} -c:v libx265 -c:a aac -b:a 384k {dest_path}"
        logging.info(f"Transcoding: {ffmpeg_cmd}")
        os.system(ffmpeg_cmd)

        if os.path.exists(dest_path):
            shutil.move(dest_path, src_path)
            return ("video/mp4", "mp4")
        else:
            raise Exception(f"Transcoding failed: {ffmpeg_cmd}")

    raise Exception(f"Invalid video file in {src_path} - no audio or video tracks")

def check_resources(src_folder, restricted_ext, paths_map, collection):

    xml_src = os.path.join(src_folder, collection)
    if not os.path.isfile(xml_src):
        logging.info(f"Collection {xml_src} not found")
        return None

    supported_audio = restricted_ext['SUPPORTED_AUDIO']
    supported_video = restricted_ext['SUPPORTED_VIDEO']

    rewrite = False

    parser = ET.XMLParser(recover=True)
    content_tree = ET.parse(xml_src, parser)

    # find each resource with an id that contains that extension
    for item in content_tree.xpath(".//resource"):

        file_name, file_extension = os.path.splitext(item.get('id'))
        file_extension = file_extension.upper().replace(".","")
        content_type = item.get('content-type')
        src_id = item.get('id')
        src_rel_id = item.get('rel-id')

        if content_type == "audio/x-mpegurl":
            # AMA-604 M3U files are plain text collections of resource identifiers
            continue

        if item.get('content-length') == '0':
            # ignore it, because nothing to do and it will get removed later
            continue

        if (content_type.startswith('audio/') and file_extension not in supported_audio) or \
           (content_type.startswith('video/') and file_extension not in supported_video):

            resource_body = item.get('body-location')
            resource_file = os.path.join(src_folder, resource_body)

            logging.info(f"Transcoding {item.get('id')} unsupported {file_extension} {content_type} body {resource_file}")

            (target_type, target_ext) = transcode(resource_file)

            if target_type:
                rewrite = True
                # Update resource details

                new_id = src_id.rsplit('.', 1)[0] + '.' + target_ext
                new_rel_id = src_rel_id.rsplit('.', 1)[0] + '.' + target_ext

                logging.info(f"Got new type {target_type} ext {target_ext} newid {new_id}")

                item.set('original-id', src_id)
                item.set('rel-id', new_rel_id)
                item.set('id', new_id)

                item.set('content-type', target_type)
                item.set('content-length', str(get_size(resource_file)))

                # Need to update the display name too
                display_name_value = None
                display_names = item.xpath('./properties/property[@name="DAV:displayname"]')

                if display_names:
                    display_name_el = display_names[0]
                    display_name_value = base64.b64decode(display_name_el.get('value')).decode('utf-8')

                    # The display name should not be an issue but seems to be treated as a filename by the D2L importer
                    if display_name_value:
                        display_name_el.set('value', base64.b64encode(Path(new_id).name.encode('utf-8')))

                else:
                    logging.debug(f"Item {item.get('id')} has no display name")
                    continue

                tool_xml_files = [entry for entry in os.scandir(src_folder) if entry.name.endswith('.xml')]
                for toolxml in tool_xml_files:

                    if (toolxml.name in ["archive.xml", "site.xml", "content.xml", "attachment.xml", "user.xml"]):
                        continue

                    if rewrite_tool_ref(toolxml, src_id, new_id):
                        logging.info(f"Fixed path {src_id} in {toolxml.name}")

    if rewrite:
        # Update file
        xml_old = xml_src.replace(".xml",".old")
        shutil.copyfile(xml_src, xml_old)
        content_tree.write(xml_src, encoding='utf-8', xml_declaration=True)

    return True

def run(SITE_ID, APP):
    logging.info('Content: transcoding unsupported audio and video types AMA-552 : {}'.format(SITE_ID))

    # restricted extensions
    restricted_ext = read_yaml(APP['content']['restricted-ext'])

    # map of tool attachment path components to tool XML file
    paths_map = APP['attachment']['paths']

    src_folder  = r'{}{}-archive/'.format(APP['archive_folder'], SITE_ID)

    check_resources(src_folder, restricted_ext, paths_map, 'content.xml')

def main():
    global APP
    parser = argparse.ArgumentParser(description="Check for zero-byte files",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
