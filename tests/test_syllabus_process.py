import os
import shutil
import unittest
import argparse
import base64

import config.config
from work.syllabus_process import main
from unittest.mock import patch
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup


class SyllabusRejiggerTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
        config.config.APP['archive_folder'] = self.ROOT_DIR + '/test_files/'
        config.config.APP['output'] = self.ROOT_DIR + '/test_files/'

    @patch('argparse.ArgumentParser.parse_args',
           return_value=argparse.Namespace(SITE_ID='syllabus', debug=False))
    def test_main_multiple_questions(self, *_):
        main()
        xml_src = self.ROOT_DIR + '/test_files/syllabus-archive/syllabus.xml'
        xml_old = self.ROOT_DIR + '/test_files/syllabus-archive/syllabus.old'

        new_tree = ET.parse(xml_src)
        new_root = new_tree.getroot()

        old_tree = ET.parse(xml_old)
        old_root = old_tree.getroot()

        old_syllabus_data = old_root.findall(".//siteArchive/syllabus/syllabus_data")
        new_syllabus_data = new_root.findall(".//siteArchive/syllabus/syllabus_data")
        # old xml file has 3 syllabus_data
        self.assertEqual(3, len(old_syllabus_data))
        # new xml file has 1 syllabus_data, merged
        self.assertEqual(1, len(new_syllabus_data))

        encoded_html = new_root.findall(".//siteArchive/syllabus/syllabus_data/asset")[0].get("syllabus_body-html")
        after_decoded_html = base64.b64decode(encoded_html).decode("utf-8")
        body_soup = BeautifulSoup(after_decoded_html, 'html.parser')
        # check elements in the html file
        self.assertEqual(1, len(body_soup.find_all('h1')))
        self.assertEqual(3, len(body_soup.find_all('h2')))

        shutil.move(xml_old, xml_src)

if __name__ == '__main__':
    unittest.main(failfast=True)
