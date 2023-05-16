#!/usr/bin/python3

## This script takes as input the 'qna.xml' file located in a site archive
## and generates a single HTML output file
## REF: AMA-403
import sys
import os
import argparse
import lxml.etree as ET

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *

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

        output_file = os.path.join(output_folder, "qna.html")

        dom = ET.parse(xml_src)
        root = dom.getroot()

        if root.tag == 'archive':
            if len(root.findall(".//question")) == 0:
                logging.info(f'\tNothing to do')
                return

        xslt = ET.parse(xsl_src)
        transform = ET.XSLT(xslt)
        newdom = transform(dom)

        f = open(output_file, "wb")
        f.write(ET.tostring(newdom, pretty_print=True))
        f.close()

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
