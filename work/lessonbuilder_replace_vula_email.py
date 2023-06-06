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

# string replace key,val
chars_to_replace = {'help@vula.uct.ac.za': 'cilt-helpdesk.uct.ac.za', 'The Vula Help Team': 'CILT Help Desk', 'Vula Help': 'CILT Help Desk'}

def replace_with_text(html, char_to_replace):
    for element in html.find_all(string=True):
        for key, value in char_to_replace.items():
            if key in element:
                new_text = element.replace(key, value)
                element.replace_with(new_text)
                return BeautifulSoup('html', 'html.parser')
  
  
def run(SITE_ID, APP):
  logging.info('Lessons: Replace vula email and team with cilt helpdesk name and team: {}'.format(SITE_ID))

xml_src = r'{}{}-archive/lessonbuilder.xml'.format(APP['archive_folder'], SITE_ID)
xml_old = r'{}{}-archive/lessonbuilder.old'.format(APP['archive_folder'], SITE_ID)
shutil.copyfile(xml_src, xml_old)

tree = ET.parse(xml_src)
root = tree.getroot()
def run():
  if root.tag == 'archive':
    for item in root.findall(".//item[@type='5']"):
              # pass the html here
              html = BeautifulSoup(item.attrib['html'], 'html.parser')
              replace_with_text(html, chars_to_replace)
              
              item.set('html', str(html))

              tree.write(xml_src, encoding='utf-8', xml_declaration=True)

  def main():
      global APP
      parser = argparse.ArgumentParser(description="Replace vula email and team with cilt helpdesk name and team",
                                      formatter_class=argparse.ArgumentDefaultsHelpFormatter)
      parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
      parser.add_argument('-d', '--debug', action='store_true')
      args = vars(parser.parse_args())

      APP['debug'] = APP['debug'] or args['debug']

      run(args['SITE_ID'], APP)

  if __name__ == '__main__':
      main()

