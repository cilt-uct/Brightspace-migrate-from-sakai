# AMA-914 MIG-3127 Set the parent attribute for Lessons items
# Sometimes this seems to be unset, and in this case a type 2 item link to a
# page from a parent page is the only way that the hierarchy is defined.
# Both the lessonbuilder_reduce_levels script and the Brightspace importer rely
# on the parent ids.

import sys
import os
import argparse
import logging

from bs4 import BeautifulSoup

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *

def run(SITE_ID, APP):

    logging.info(f"Setting Lessons page parents for {SITE_ID}")

    xml_src = r'{}{}-archive/lessonbuilder.xml'.format(APP['archive_folder'], SITE_ID)
    output = r'{}{}-archive/lessonbuilder.new'.format(APP['archive_folder'], SITE_ID)

    xml_dest = r'{}{}-archive/lessonbuilder.xml'.format(APP['archive_folder'], SITE_ID)
    xml_backup = r'{}{}-archive/lessonbuilder.xml.orig'.format(APP['archive_folder'], SITE_ID)

    if APP['debug']:
        ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
        xml_src = ROOT_DIR + '/../tests/test_files/input.xml'
        output = ROOT_DIR + '/../tests/test_files/output.xml'

    if not os.path.exists(xml_src):
        raise Exception(f"Lessonbuilder file {xml_src} not found")

    with open(xml_src, 'r') as f:
        data = f.read()

    all_xml = BeautifulSoup(data, "xml")
    lesson_builder = all_xml.find('lessonbuilder')
    pages = all_xml.find_all('page')

    update = False

    for page in pages:

        page_id = page.get('pageid')
        page_title = page.get('title')

        logging.debug(f"Setting parent for sub-pages on page {page_id} title '{page_title}")

        items = page.find_all('item')

        for item in items:
            item_id = item.get('id')
            item_type = item.get('type')

            # Items that link to pages
            if item_type == '2':
                item_link = item.get('sakaiid')
                logging.debug(f"item id {item_id} has type {item_type} and name '{item.get('name')}' linking to id {item_link}")

                # Set page parent if needed
                page_target = lesson_builder.find("page", {'pageid': item_link} )
                if page_target is not None:
                    page_target_parent = page_target.get('parent')
                    if page_target_parent is None or page_target_parent == "0":
                        logging.info(f"Found page target {page_target.get('title')} parent '{page_target_parent}' updating parent to {page_id}")
                        page_target['parent'] = page_id
                        update = True

    if update:
        with open(output, 'w') as f:
            f.write(all_xml.prettify())

        os.rename(xml_dest, xml_backup)
        os.rename(output, xml_dest)


def main():
    global APP
    parser = argparse.ArgumentParser(description="This script sets Lessons page parents",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)


if __name__ == '__main__':
    main()
