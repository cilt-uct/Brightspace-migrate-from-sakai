import os
import shutil
import unittest
import argparse
import base64

import config.config
from work.syllabus_process import main
from unittest.mock import patch
import xml.etree.ElementTree as ET


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
        try:
            self.check_converted(xml_src=xml_src)
        finally:
            shutil.move(xml_old, xml_src)

    def check_converted(self, xml_src: str):
        tree = ET.parse(xml_src)
        root = tree.getroot()

        # Find syllabus_data nodes
        syllabus_data = root.findall(".//siteArchive/syllabus/syllabus_data/asset")
        encoded_html = syllabus_data[0].get("syllabus_body-html")

        after_decoded_html = base64.b64decode(encoded_html).decode("utf-8")
        self.assertIsNotNone(after_decoded_html)

        with open(self.ROOT_DIR + '/test_files/syllabus-archive/new_syllabus.html', 'r') as file:
            new_syllabus_html = file.read()

        self.assertEqual(new_syllabus_html, after_decoded_html)


if __name__ == '__main__':
    unittest.main(failfast=True)
