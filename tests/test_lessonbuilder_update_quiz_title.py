import os
import shutil
import unittest
import argparse

import config.config
from work.lessonbuilder_update_quiz_title import main
from unittest.mock import patch
import xml.etree.ElementTree as ET


class GenerateConversionReportTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
        config.config.APP['archive_folder'] = self.ROOT_DIR + '/test_files/'

    @patch('argparse.ArgumentParser.parse_args',
           return_value=argparse.Namespace(SITE_ID='site_12345', debug=False))
    def test_main_multiple_questions(self, *_):
        main()
        xml_src = self.ROOT_DIR + '/test_files/site_12345-archive/lessonbuilder.xml'
        xml_old = self.ROOT_DIR + '/test_files/site_12345-archive/lessonbuilder.old'
        self.check_converted(xml_src=xml_src)
        shutil.move(xml_old, xml_src)

    @patch('argparse.ArgumentParser.parse_args',
           return_value=argparse.Namespace(SITE_ID='site_1234', debug=False))
    def test_main_single_question(self, *_):
        main()
        xml_src = self.ROOT_DIR + '/test_files/site_1234-archive/lessonbuilder.xml'
        xml_old = self.ROOT_DIR + '/test_files/site_1234-archive/lessonbuilder.old'
        self.check_converted(xml_src=xml_src)
        shutil.move(xml_old, xml_src)

    def check_converted(self, xml_src: str):
        tree = ET.parse(xml_src)
        root = tree.getroot()

        pages = root.findall(".//page")

        for page in pages:
            questions = page.findall(".//item[@type='11']")

            for i, question in enumerate(questions):
                if len(questions) == 1:
                    self.assertEqual('Question', question.get('name'))
                else:
                    new_quiz_name = "Question {}".format(i + 1)
                    self.assertEqual(new_quiz_name, question.get('name'))


if __name__ == '__main__':
    unittest.main(failfast=True)
