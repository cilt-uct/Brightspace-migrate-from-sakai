#!/usr/bin/python3

## AMA-432 Embedded audio files from ckeditor in html content

import sys
import os
import re
import shutil
import copy
import argparse
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import cssutils
from pathlib import Path

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *

def run(SITE_ID, APP):
    logging.info(f'Lessons: Fix embedded audio .wav files : {SITE_ID}')

    sakai_url = APP['sakai_url']
    xml_src = r'{}{}-archive/lessonbuilder.xml'.format(APP['archive_folder'], SITE_ID)
    remove_unwanted_characters(xml_src)

    attachment_src = r'{}{}-archive/attachment.xml'.format(APP['archive_folder'], SITE_ID)

    if not os.path.exists(attachment_src):
        # No attachments, nothing to do here
        return

    with  open(attachment_src, 'r') as af:
        attachment_xml = af.read()

    tree = ET.parse(xml_src)
    root = tree.getroot()

    rewrite = False

    for item in root.findall(".//item[@type='5']"):

        html = BeautifulSoup(item.attrib['html'], 'html.parser')

        for el in html.find_all("audio", {"class": "audioaudio"}):
            asrc = el.find("source", {"type" : "audio/x-wav"})
            if asrc:
                audio_url = asrc.get('src')

                if "/content/attachment/" in audio_url:
                    # Rewrite to a relative URL here, and update the attachment id.
                    # Drop all the path info because these are unique anyway
                    audio_path = Path(audio_url)
                    new_path = f"audio/{audio_path.name}"
                    asrc['src'] = new_path
                    attachment_xml = attachment_xml.replace(audio_url.replace(f"{sakai_url}/access/content",""), f"/LessonBuilder/{new_path}")
                    rewrite = True

        if rewrite:
            # Replace markup in the lessonbuilder item
            item.set('html', str(html))

    # Update the lessonbuilder XML
    if rewrite:
        logging.info(f"Updating {xml_src}")
        xml_old = r'{}{}-archive/lessonbuilder.old'.format(APP['archive_folder'], SITE_ID)
        shutil.copyfile(xml_src, xml_old)
        tree.write(xml_src, encoding='utf-8', xml_declaration=True) 

        with open(attachment_src, "wt") as af:
            af.write(attachment_xml)
    
def main():
    global APP
    parser = argparse.ArgumentParser(description="This script fixes embedded audio files in Lessons content",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
