import os
import shutil
import unittest
import argparse

import config.config
from work.lessonbuilder_rewrite_urls import main, fix_unwanted_url_chars
from unittest.mock import patch
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

class LessonbuilderUpdateUrlRewriteTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
        config.config.APP['archive_folder'] = self.ROOT_DIR + '/test_files/'

        # Match the URL in the test case data
        config.config.APP['sakai_url'] = "https://vula.uct.ac.za"

    @patch('argparse.ArgumentParser.parse_args', return_value=argparse.Namespace(SITE_ID='site_123456', debug=True))

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

        for page in pages:
            items = page.findall(".//item[@type='5']")
            for item in items:
                html = BeautifulSoup(item.attrib['html'], 'html.parser')
                for attr in ['src', 'href']:
                    for element in html.find_all(attrs={attr: True}):
                        self.assertEqual(element.get(attr), '../Lesson 1 with in title/Jpeg_thumb_artifacts_test.jpg')


    # with . inbetween names
    def test_unwanted_chars(self):
        currenturl = 'https://vula.uct.ac.za/access/content/group/site_123456/Lesson%201%20with%20in%20title%3A/Jpeg_.thumb_artifacts%3A_dots_in_name.jpg'
        prefix = 'https://vula.uct.ac.za/access/content/group/site_123456'
        expected1 = '../Lesson%201%20with%20in%20title/Jpeg_.thumb_artifacts_dots_in_name.jpg'
        self.assertEqual(fix_unwanted_url_chars(currenturl, prefix), expected1)

    def test_unwanted_chars_2(self):
        currenturl = 'https://vula.uct.ac.za/access/content/group/site_123456/..Lesson%201%20..with%20in..%20title%3A../Jpeg_.thumb_artifacts%3A_dots_in_folder.jpg'
        prefix = 'https://vula.uct.ac.za/access/content/group/site_123456'
        expected1 = '../Lesson%201%20..with%20in..%20title/Jpeg_.thumb_artifacts_dots_in_folder.jpg'
        self.assertEqual(fix_unwanted_url_chars(currenturl, prefix), expected1)

    # testing ! in name
    def test_unwanted_chars_3(self):
        currenturl = 'https://vula.uct.ac.za/access/content/group/site_123456/SCT%20with%20!%20in%20filename/VIELEN%20DANK%20!!!.gif'
        prefix = 'https://vula.uct.ac.za/access/content/group/site_123456'
        expected3 = '../SCT%20with%20%20in%20filename/VIELEN%20DANK%20.gif'
        self.assertEqual(fix_unwanted_url_chars(currenturl, prefix), expected3)

    # testing folder starts & ends with .. and ! in name
    def test_unwanted_chars_4(self):
        currenturl = 'https://vula.uct.ac.za/access/content/group/site_123456/..SCT%20with%20!%20in%20filename/VIELEN%20DANK%20!!!.gif'
        prefix = 'https://vula.uct.ac.za/access/content/group/site_123456'
        expected4 = '../SCT%20with%20%20in%20filename/VIELEN%20DANK%20.gif'
        self.assertEqual(fix_unwanted_url_chars(currenturl, prefix), expected4)

    # testing non vula url with special chars
    def test_unwanted_chars_5(self):
        currenturl = 'https://www.google.com/?search=!:'
        prefix = 'https://vula.uct.ac.za/access/content/group/site_123456'
        expected5 = 'https://www.google.com/?search=!:'
        self.assertEqual(fix_unwanted_url_chars(currenturl, prefix), expected5)

    # testing src + in name
    def test_unwanted_chars_6(self):
        currenturl = 'https://vula.uct.ac.za/access/content/group/site_123456/SCT+with+in+filename+/VIELEN+DANK+.gif'
        prefix = 'https://vula.uct.ac.za/access/content/group/site_123456'
        expected6 ='../SCT_with_in_filename_/VIELEN_DANK_.gif'
        self.assertEqual(fix_unwanted_url_chars(currenturl, prefix), expected6)

if __name__ == '__main__':
    unittest.main(failfast=True)
