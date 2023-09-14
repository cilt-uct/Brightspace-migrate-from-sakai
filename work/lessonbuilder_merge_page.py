#!/usr/bin/python3

import sys
import os
import argparse

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *


def run(SITE_ID, APP):
    logging.info('Merge lessons page: {}'.format(SITE_ID))
    site_folder = APP['archive_folder']

    xml_src = r'{}{}-archive/lessonbuilder.xml'.format(site_folder, SITE_ID)
    xml_old = r'{}{}-archive/lessonbuilder.old'.format(site_folder, SITE_ID)
    shutil.copyfile(xml_src, xml_old)

    remove_unwanted_characters(xml_src)

    file_path = os.path.join(site_folder, xml_src)

    with open(file_path, "r", encoding="utf8") as fp:
        soup = BeautifulSoup(fp, 'xml')
        pages = soup.find_all('page')
        for page in pages:
            merged = BeautifulSoup('<div></div>', 'html.parser')
            items = page.find_all('item')
            for item in items:
                if item.attrs['type'] == '5':
                    html = BeautifulSoup(item.attrs['html'], 'html.parser')
                else:
                    if item.attrs['html'] in APP['lessons']['type_to_link']:
                        href = f'{APP["sakai_url"]}/access/content{item.attrs["sakaiid"]}'
                        html = BeautifulSoup(f'<p><a href="{href}">{item.attrs["name"]}</a></p>', 'html.parser')
                    else:
                        html = BeautifulSoup(f'<p style="border-style:solid;" data-type="placeholder"><span style="font-weight:bold;">PLACEHOLDER</span> [name: {item.attrs["name"]}; type: {item.attrs["html"]}]</p>', 'html.parser')
                merged.div.append(html)

            updated_item = page.find('item', {'type': '5'})
            updated_item['html'] = str(merged)
            updated_item['data-merged'] = True

            for item in items:
                if not item.attrs.get('data-merged') and item.attrs.get('type') == 5:
                    item.extract()

        updated_xml = soup.prettify()
        with open(file_path, 'w') as file:
            file.write(updated_xml)


def main():
    global APP
    parser = argparse.ArgumentParser(description="This script takes as input the 'lessonbuilder.xml' file inside "
                                                 "the site-archive folder and merges page content",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)


if __name__ == '__main__':
    main()
