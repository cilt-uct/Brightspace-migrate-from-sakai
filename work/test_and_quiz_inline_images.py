#!/usr/bin/python3

## REF: AMA-121 Inline Images

import sys
import os
import re
import shutil
import copy
import argparse
import hashlib
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from urllib.parse import urlparse, quote, unquote

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *
from lib.resources import *

def fix_images(APP, SITE_ID, content_ids, attachment_ids, collection, move_list, xml_src):

    print(f"Fixing images: {xml_src}")

    sakai_url = APP['sakai_url']

    tree = ET.parse(xml_src)
    root = tree.getroot()

    update_file = False

    # Assessment or Question Pools
    if root.tag == 'questestinterop' or root.tag == "QuestionPools":

        for item in root.findall(".//mattext"):

            if item.text:

               # could be plain text so check that it at least contains an image tag
               if "<img" in item.text:

                    #print(f"Checking: {item.text}")
                    item_text = item.text.replace("<![CDATA[", "").replace("]]>", "")
                    html = BeautifulSoup(item_text, 'html.parser')
                    update_item = False

                    # Find all the image tags
                    for el in html.findAll("img"):

                        update_item = True
                        update_file = True

                        del el['width']
                        del el['height']
                        el['style'] = "max-width: 100%;"

                        img_src = el.get('src')

                        if not img_src:
                            # Unlikely
                            continue

                        if img_src.startswith("data:"):
                            # Inline base64 image
                            continue

                        # URLs to Resources in this site - nothing to do
                        if img_src.startswith(f"{sakai_url}/access/content/group/{SITE_ID}/"):
                            # print(f"Ignoring {img_src} - already in this site")
                            continue

                        # Attachments and cross-site resources included in this site's attachment archive
                        if img_src.startswith(f"{sakai_url}/access/content/"):

                            #print(f"Checking {img_src}")

                            # Drop the space in the attachment path AMA-120
                            img_src = img_src.replace("/Tests _ Quizzes/","/Tests_Quizzes/")
                            attach_id = unquote(img_src.replace(f"{sakai_url}/access/content",""))

                            if not attach_id in attachment_ids:
                                raise Exception(f"Missing attachment: {attach_id} in {xml_src}")

                            # Move this item from Attachments to Resources
                            # ID in attachment.xml
                            #   /attachment/eae4b5a5-614b-4d4a-a987-00666530af3b/Tests_Quizzes/80be4545-5832-413f-a13c-5b8407fed61b/ACB_fig1.png
                            #   /group/9148b87f-a73a-42e0-bb23-18b1d76a0165/ACB_fig1.png

                            shorthash = hashlib.shake_256(attach_id.encode()).hexdigest(3)
                            filename = attach_id.split("/")[-1]
                            new_id = f"/group/{SITE_ID}/{collection}/{shorthash}/{filename}"

                            move_list[attach_id] = new_id
                            new_url = f"{sakai_url}/access/content{quote(new_id)}"

                            # print(f"Attach ID: {attach_id} new URL: {new_url}")

                            el['src'] = new_url

                    if update_item:
                        item.text = ET.CDATA(str(html))
                        # print(f"New text: {item.text}")

            if update_file:
                tree.write(xml_src)

    return

def run(SITE_ID, APP):

    logging.info('T&Q: Inline images : {}'.format(SITE_ID))

    collection = "quiz_images"
    move_list = {}

    site_folder = f"{APP['archive_folder']}{SITE_ID}-archive"
    qti_path = f"{site_folder}/qti"

    content_src = f'{site_folder}/content.xml'
    attach_src = f'{site_folder}/attachment.xml'

    content_ids = get_resource_ids(content_src)
    attachment_ids = get_resource_ids(attach_src)

    for qti in os.scandir(qti_path):
        if qti.is_file():
            fix_images(APP, SITE_ID, content_ids, attachment_ids, collection, move_list, qti.path)

    qp = f"{site_folder}/samigo_question_pools.xml"
    if os.path.exists(qp):
        fix_images(APP, SITE_ID, content_ids, attachment_ids, collection, move_list, qp)

    print(f"\nMoving attachments")
    move_attachments(SITE_ID, site_folder, collection, move_list)

    print(f"\nmove list: {move_list}")

def main():
    global APP
    parser = argparse.ArgumentParser(description="AMA-121 Inline Images",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
