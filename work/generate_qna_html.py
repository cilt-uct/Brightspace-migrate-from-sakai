#!/usr/bin/python3

## This script takes as input the 'qna.xml' file located in a site archive
## and generates a single HTML output file
## REF: AMA-403
import sys
import os
import argparse
import lxml.etree as ET
import hashlib

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from bs4 import BeautifulSoup
from config.logging_config import *
from lib.utils import *
from lib.resources import *
from urllib.parse import quote

# def run(SITE_ID, APP):
def run(SITE_ID, APP):
    try:
        logging.info('QNA: generate single HTML output file : {}'.format(SITE_ID))

        xml_src = r'{}{}-archive/qna.xml'.format(APP['archive_folder'], SITE_ID)
        xsl_src = APP['qna']['xsl']

        if not os.path.isfile(xml_src):
            raise Exception(f"qna.xml not found in {SITE_ID} archive")

        if not os.path.isfile(xsl_src):
            raise Exception(f"xslt not found: {xsl_src}")

        # output folder for D2L content import
        output_folder = "{}{}-content".format(APP['output'], SITE_ID)
        if not os.path.exists(output_folder):
            os.mkdir(output_folder)

        site_folder = r'{}{}-archive/'.format(APP['archive_folder'], SITE_ID)
        output_file = f'{site_folder}qna.html'

        dom = ET.parse(xml_src)
        root = dom.getroot()

        if root.tag == 'archive':
            if len(root.findall(".//question")) == 0:
                logging.info('\tNothing to do')
                return

        # Replace wiris content
        for item in root.xpath(".//question | .//answer"):
            if item.text:
                if item.text.find('data-mathml') > 0:
                    html_str = item.text.replace("<![CDATA[", "").replace("]]>", "")
                    item.text = ET.CDATA(replace_wiris(html_str))

        xslt = ET.parse(xsl_src)
        transform = ET.XSLT(xslt)
        newdom = transform(dom)

        # Adjust attachment refs
        html = BeautifulSoup(ET.tostring(newdom), 'html.parser')

        collection = APP['qna']['collection']
        move_list = {}

        for el in html.body.find_all("a", {"data-qna" : "attachment"}):
            attach_id = el.get('href')
            filename = attach_id.split("/")[-1]
            shorthash = hashlib.shake_256(attach_id.encode()).hexdigest(3)
            new_id = f"/group/{SITE_ID}/{collection}/{shorthash}/{filename}"
            new_url = f"{shorthash}/{quote(filename)}"

            move_list[attach_id] = new_id
            el['href'] = new_url
            el['target'] = "_blank"
            el.string = filename

        # Drop empty paras
        for el in html.body.find_all("p"):
            if not el.findChildren() and (el.get_text() is None or el.get_text().strip() == ""):
                el.decompose()

        # Write html
        html_updated_bytes = html.encode('utf-8')
        with open(output_file, "wb") as file:
            file.write(html_updated_bytes)

        # Add qna.html itself
        add_resource(SITE_ID, site_folder, output_file, "text/html", collection)

        # Move any attachments
        move_attachments(SITE_ID, site_folder, collection, move_list)

        logging.info(f'\tDone: QNA output in {output_file}')

    except Exception as e:
        raise e


def main():
    global APP
    parser = argparse.ArgumentParser(description="This script takes as input the 'qna.xml' file located in a site archive and generates a single HTML output file for possible use in Brightspace",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']
    run(args['SITE_ID'], APP)


if __name__ == '__main__':
    main()
