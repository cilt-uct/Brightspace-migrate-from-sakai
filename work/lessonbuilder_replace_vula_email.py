import sys
import os
import re
import shutil
import copy
import argparse
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import cssutils

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *

current = os.path.dirname(os.path.realpath(__file__))

def run(SITE_ID, APP):
  logging.info('Lessons: Replace help@vula.uct.ac.za with cilt-helpdesk@uct.ac.za : {}'.format(SITE_ID))

  xml_src = r'{}{}-archive/lessonbuilder.xml'.format(APP['archive_folder'], SITE_ID)
  xml_old = r'{}{}-archive/lessonbuilder.old'.format(APP['archive_folder'], SITE_ID)
  shutil.copyfile(xml_src, xml_old)

  tree = ET.parse(xml_src)
  root = tree.getroot()

  if root.tag == 'archive':
    for item in root.findall(".//item[@type='5']"):
              # pass the html here
              html = BeautifulSoup(item.attrib['html'], 'html.parser')
              # replace all occurences of the emails, pass as vars
              oldmail = 'help@vula.uct.ac.za'
              newmail = 'cilt-helpdesk@uct.ac.za'
              def update_email(node):
                  if node.parent and node.parent.name == 'a':
                      node.parent['href'] = node.parent['href'].replace(oldmail, newmail)
                      node.replace_with(newmail)
                  else:
                      node.replace_with(str(node).replace(oldmail, newmail))

              text_nodes = html.find_all(string=True)
              for node in text_nodes:
                  update_email(node)

              item.set('html', str(html))

              tree.write(xml_src, encoding='utf-8', xml_declaration=True)

def main():
    global APP
    parser = argparse.ArgumentParser(description="Replace help@vula.uct.ac.za with cilt-helpdesk@uct.ac.za",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
