import os
import shutil
import unittest
import argparse
import config
import config.config
from work.lessonbuilder_rewrite_urls import fix_unwanted_url_chars
from unittest.mock import patch
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

class LessonbuilderUpdateUrlRewriteTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

    @patch('os.rename')
    @patch('argparse.ArgumentParser.parse_args', return_value=argparse.Namespace(SITE_ID='123456', debug=True))

    def test_url_rewrite_chars_fix(self, *_):
        xml_src = self.ROOT_DIR + '/test_files/site_123456-archive/lessonbuilder.xml'
        xml_old = self.ROOT_DIR + '/test_files/site_123456-archive/lessonbuilder.old'
        self.check_urls_chars(xml_src=xml_src)
        shutil.move(xml_old, xml_src)
    def check_urls_chars(self, xml_src: str):

        tree = ET.parse(xml_src)
        root = tree.getroot()

        urlprefix = 'https://vula.uct.ac.za/access/content/group/site_123456'
        expected_outcome = '../Lesson 1 with in title/Jpeg_thumb_artifacts_test.jpg'

        for item in root.findall(".//item[@type='5']"):
            html = BeautifulSoup(item.attrib['html'], 'html.parser')
            for element in html.find_all(attrs={'src': True}):
                current_url = element.get('src')
                self.assertEquals((fix_unwanted_url_chars(current_url, urlprefix)), expected_outcome)

if __name__ == '__main__':
    unittest.main(failfast=True)
