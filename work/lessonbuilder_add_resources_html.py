#!/usr/bin/python3

import sys
import os
import argparse

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.lessons import *

def run(SITE_ID, APP):
    logging.info('Merge lessons page: {}'.format(SITE_ID))
    site_folder = APP['archive_folder']

    content_src = r'{}{}-archive/content.xml'.format(site_folder, SITE_ID)
    remove_unwanted_characters(content_src)
    content_path = os.path.join(site_folder, content_src)

    xml_src = r'{}{}-archive/lessonbuilder.xml'.format(site_folder, SITE_ID)
    xml_old = r'{}{}-archive/lessonbuilder.old'.format(site_folder, SITE_ID)
    shutil.copyfile(xml_src, xml_old)
    remove_unwanted_characters(xml_src)
    file_path = os.path.join(site_folder, xml_src)

    with open(file_path, "r", encoding="utf8") as fp:
        lessons_soup = BeautifulSoup(fp, 'xml')
        lessons_pages = lessons_soup.find_all('page')
        for lessons_page in lessons_pages:
            html_item = lessons_page.find('item', attrs={"type": "5"})
            html = html_item.get('html')
            if html:
                html_soup = BeautifulSoup(html, 'html.parser')
                resource_html = BeautifulSoup('<div data-type="folder-list"></div>', 'html.parser')
                resource_div = resource_html.find('div')
                embedded_resources = lessons_page.find_all('item', attrs={"type": "20"})
                for embedded_resource in embedded_resources:
                    attr = embedded_resource.find("attributes")
                    atrr_json = attr.get_text()
                    attributes = json.loads(atrr_json)
                    if 'dataDirectory' in attributes:
                        directory = attributes.get('dataDirectory')
                        directory = '/'.join(segment for segment in directory.split('/') if segment)
                        if directory:
                            with open(content_path, "r", encoding="utf8") as cp:
                                content_soup = BeautifulSoup(cp, 'xml')
                                resources = content_soup.find_all('resource')
                                for resource in resources:
                                    if directory in resource['id']:
                                        file_name = resource["rel-id"].split('/')[1]
                                        new_p_tag = BeautifulSoup(f'<p>{file_name}</p>', 'html.parser')
                                        resource_div.append(new_p_tag)

                html_soup.append(resource_div)

            if html and html_soup:
                html_item['html'] = str(html_soup)

        updated_xml = lessons_soup.prettify()
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
