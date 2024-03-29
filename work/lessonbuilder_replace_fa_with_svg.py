#!/usr/bin/python3

## Replace lesson FontAwesome icons with SVG images
## REF:

import sys
import os
import shutil
import argparse
import xml.etree.ElementTree as ET
import logging

from bs4 import BeautifulSoup

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import remove_unwanted_characters, make_well_formed

shared_path = '/shared/HTML-Template-Library/HTML-Templates-V3/_assets/img/'

def replace_with_img(html, path, img, _cls = None):
    for icon in html.select(path):
        new_span = html.new_tag("span")
        new_span['aria-hidden'] = 'true'
        if (_cls is not None):
            new_span['class'] = _cls
        img = html.new_tag('img', alt="", src=f"{shared_path}{img}")
        new_span.append(img)

        icon.replace_with(new_span)

def run(SITE_ID, APP):
    logging.info('Lessons: Replace fa icons with SVG : {}'.format(SITE_ID))

    xml_src = r'{}{}-archive/lessonbuilder.xml'.format(APP['archive_folder'], SITE_ID)
    xml_old = r'{}{}-archive/lessonbuilder.old'.format(APP['archive_folder'], SITE_ID)
    shutil.copyfile(xml_src, xml_old)

    remove_unwanted_characters(xml_src)

    tree = ET.parse(xml_src)
    root = tree.getroot()

    if root.tag == 'archive':
        for item in root.findall(".//item[@type='5']"):

            title = None
            parent = root.findall('.//item[@id="{}"]...'.format(item.attrib['id']))
            if len(parent) > 0:
                title = parent[0].attrib['title']

            html = BeautifulSoup(item.attrib['html'], 'html.parser')
            html = make_well_formed(html, title)

            # headings
            replace_with_img(html, 'h2 span[class="fa fa-bullseye fa-fw"]', 'icon_learning_outcomes.svg')
            replace_with_img(html, 'h2 span[class="fa fa-fw fa-key"]', 'icon_key_information.svg')
            replace_with_img(html, 'h2 span[class="fa fa-check-square fa-fw"]', 'icon_key_activities.svg')

            replace_with_img(html, 'h2 span[class="fa fa-book"]', 'icon_reading.svg')
            replace_with_img(html, 'h3 span[class="fa fa-book"]', 'icon_reading.svg')

            replace_with_img(html, 'h2 span[class="fa fa-play-circle"]', 'icon_video.svg')
            replace_with_img(html, 'h3 span[class="fa fa-play-circle"]', 'icon_video.svg')

            replace_with_img(html, 'h2[class!="sectionheader"] span[class="fas fa-file-alt"]', 'icon_assignment.svg')
            replace_with_img(html, 'h3 span[class="fa fa-file-text"]', 'icon_assignment.svg')

            replace_with_img(html, 'h2 span[class="fa fa-comments"]', 'icon_discussion.svg')
            replace_with_img(html, 'h3 span[class="fa fa-comments"]', 'icon_discussion.svg')

            # alerts
            replace_with_img(html, 'div[class*="alert"] div span[class*="fa-lightbulb"]', 'icon_lightbulb.svg', 'lightbulb')
            replace_with_img(html, 'div[class*="alert"] div span[class*="fa-star"]', 'icon_star.svg', 'star')

            # panel
            replace_with_img(html, 'div[class*="panel"] div span[class*="fa-exclamation-triangle"]', 'icon_warning.svg')

            # write_test_case(html, item.attrib['id'])
            item.set('html', str(html))
            # print(ET.tostring(item))

        tree.write(xml_src, encoding='utf-8', xml_declaration=True)

def main():
    global APP
    parser = argparse.ArgumentParser(description="Replace lesson FontAwesome icons with SVG images",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
