#!/usr/bin/python3

## AMA-121 Inline Images
## AMA-1149 Inline audio (partial support)

import sys
import os
import argparse
import hashlib
import lxml.etree as ET
import logging

from bs4 import BeautifulSoup
from urllib.parse import quote, unquote

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.logging_config
from lib.resources import get_resource_ids, move_attachments, rename_attachments

def fix_inline(APP, SITE_ID, content_ids, attachment_ids, collection, move_list, rename_list, xml_src):

    #print(f"Fixing images: {xml_src}")

    sakai_url = APP['sakai_url']

    tree = ET.parse(xml_src)
    root = tree.getroot()

    update_file = False

    # Assessment or Question Pools
    if root.tag == 'questestinterop' or root.tag == "QuestionPools":

        for item in root.findall(".//mattext"):

            if item.text:

               # could be plain text so check that it at least contains an image or source tag
               if "<img" in item.text or "<source":

                    #print(f"Checking: {item.text}")
                    item_text = item.text.replace("<![CDATA[", "").replace("]]>", "")
                    html = BeautifulSoup(item_text, 'html.parser')
                    update_item = False

                    # Find all the media tags
                    for el in html.findAll("img") + html.findAll("source"):

                        update_item = True
                        update_file = True

                        # Make wide images scale correctly in the editor and preview
                        if el.name == "img":
                            el['style'] = "max-width: 100%; height: auto;"

                        media_src = el.get('src')

                        if not media_src:
                            # Unlikely
                            continue

                        if media_src.startswith("data:"):
                            # Inline base64 image
                            continue

                        # URLs to Resources in this site - nothing to do
                        if media_src.startswith(f"{sakai_url}/access/content/group/{SITE_ID}/"):
                            # print(f"Ignoring {media_src} - already in this site")
                            continue

                        # Attachments and cross-site resources included in this site's attachment archive
                        if media_src.startswith(f"{sakai_url}/access/content/"):

                            #print(f"Checking {media_src}")

                            # Drop the space in the attachment path AMA-120
                            media_src = media_src.replace("/Tests _ Quizzes/","/Tests_Quizzes/")
                            attach_id = unquote(media_src.replace(f"{sakai_url}/access/content",""))

                            if attach_id in content_ids:
                                continue

                            if attach_id not in attachment_ids:
                                logging.warning(f"Missing media: {attach_id} in {xml_src} URL {media_src}")
                                continue

                            shorthash = hashlib.shake_256(attach_id.encode()).hexdigest(3)
                            filename = attach_id.split("/")[-1]

                            if el.name == "img":
                                # Move this item from Attachments to Resources
                                # ID in attachment.xml
                                #   /attachment/eae4b5a5-614b-4d4a-a987-00666530af3b/Tests_Quizzes/80be4545-5832-413f-a13c-5b8407fed61b/ACB_fig1.png
                                #   /group/9148b87f-a73a-42e0-bb23-18b1d76a0165/ACB_fig1.png

                                new_id = f"/group/{SITE_ID}/{collection}/{shorthash}/{filename}"
                                new_url = f"{sakai_url}/access/content{quote(new_id)}"
                                move_list[attach_id] = new_id
                            else:
                                # Don't move .wav files from attachments, otherwise they'll get imported into Media Library which we don't want
                                # However, we still end up with a broken URL in the quiz item unfortunately.
                                new_id = f"/{collection}/{shorthash}/{filename}"
                                new_url = f"{sakai_url}/access/content/group/{SITE_ID}{quote(new_id)}"
                                rename_list[attach_id] = new_id

                            # print(f"Attach ID: {attach_id} new URL: {new_url}")

                            el['src'] = new_url

                    if update_item:
                        item.text = ET.CDATA(str(html))
                        print(f"Updated item: new text {item.text}")

    if update_file:
        print(f"Fixing inline media: {xml_src}")
        tree.write(xml_src)

    return

def run(SITE_ID, APP):

    logging.info('T&Q: Inline media : {}'.format(SITE_ID))

    collection = APP['quizzes']['media_collection']
    move_list = {}
    rename_list = {}

    site_folder = f"{APP['archive_folder']}{SITE_ID}-archive"
    qti_path = f"{site_folder}/qti"

    content_src = f'{site_folder}/content.xml'
    attach_src = f'{site_folder}/attachment.xml'

    content_ids = get_resource_ids(content_src)
    attachment_ids = get_resource_ids(attach_src)

    for qti in os.scandir(qti_path):
        if qti.is_file():
            fix_inline(APP, SITE_ID, content_ids, attachment_ids, collection, move_list, rename_list, qti.path)

    qp = f"{site_folder}/samigo_question_pools.xml"
    if os.path.exists(qp):
        fix_inline(APP, SITE_ID, content_ids, attachment_ids, collection, move_list, rename_list, qp)

    if len(move_list):
        print(f"\nMoving attachments to {collection}:\n{move_list}")
        move_attachments(SITE_ID, site_folder, collection, move_list)

    if len(rename_list):
        print(f"\nRenaming attachments for {collection}:\n{rename_list}")
        rename_attachments(SITE_ID, site_folder, collection, rename_list)


def main():
    APP = config.config.APP
    parser = argparse.ArgumentParser(description="AMA-121 Inline Images",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
