import os
import shutil
import unittest
import argparse

import config.config
from work.lessonbuilder_rewrite_urls import main
from unittest.mock import patch
import xml.etree.ElementTree as ET

class LessonbuilderUpdateUrlRewriteTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
        config.config.APP['archive_folder'] = self.ROOT_DIR + '/test_files/'

    @patch('os.rename')
    @patch('argparse.ArgumentParser.parse_args', return_value=argparse.Namespace(SITE_ID='123456', debug=True))

    def test_url_rewrite_chars_fix(self, *_):
        main()
        xml_src = self.ROOT_DIR + '/test_files/site_123456-archive/lessonbuilder.xml'
        xml_old = self.ROOT_DIR + '/test_files/site_123456-archive/lessonbuilder.old'
        self.check_urls_chars(xml_src=xml_src)
        shutil.move(xml_old, xml_src)

    def check_urls_chars(self, xml_src: str):
        tree = ET.parse(xml_src)
        root = tree.getroot()
        pages = root.findall(".//page")

        # check xml_src is updated here
        with open(xml_src, 'r') as f:
            data = f.read()
        print(data)

        for page in pages:
            items = page.findall(".//item[@type='5']")
            for item in items:
                print(item)

if __name__ == '__main__':
    unittest.main(failfast=True)
