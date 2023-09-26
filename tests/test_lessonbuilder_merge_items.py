import os
import shutil
import unittest
import argparse

import config.config
from work.lessonbuilder_merge_page import main
from unittest.mock import patch
from bs4 import BeautifulSoup

class MergePageTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
        config.config.APP['archive_folder'] = self.ROOT_DIR + '/test_files/'

    @patch('argparse.ArgumentParser.parse_args',
           return_value=argparse.Namespace(SITE_ID='site_merge', debug=False))
    def test_main_multiple_questions(self, *_):
        main()
        xml_src = self.ROOT_DIR + '/test_files/site_merge-archive/lessonbuilder.xml'
        xml_old = self.ROOT_DIR + '/test_files/site_merge-archive/lessonbuilder.old'
        self.check_converted(xml_src=xml_src)
        shutil.move(xml_old, xml_src)


    def check_converted(self, xml_src):
        file_path = os.path.join(xml_src)
        page_count = 0

        with open(file_path, "r", encoding="utf8") as fp:
            soup = BeautifulSoup(fp, 'xml')
            pages = soup.find_all('page')
            for page in pages:
                items = page.find_all('item')

                if page_count == 0:
                    self.assertEqual(2, len(items))
                    self.assertEqual("5", items[0].attrs['type'])
                    self.assertEqual("7", items[1].attrs['type'])
                if page_count == 1:
                    self.assertEqual(2, len(items))
                    self.assertEqual("7", items[0].attrs['type'])
                    self.assertEqual("5", items[1].attrs['type'])
                if page_count == 2:
                    self.assertEqual(3, len(items))
                    self.assertEqual("7", items[0].attrs['type'])
                    self.assertEqual("5", items[1].attrs['type'])
                    self.assertEqual("1", items[2].attrs['type'])
                if page_count == 3:
                    self.assertEqual(1, len(items))
                    self.assertEqual("5", items[0].attrs['type'])
                if page_count == 4:
                    self.assertEqual(3, len(items))
                    self.assertEqual("7", items[0].attrs['type'])
                    self.assertEqual("5", items[1].attrs['type'])
                    html = '<div><p 2.0="" data-sakaiid="/group/81814b18-6ae4-4570-be9d-7459154a94b4/Lessons" data-type="placeholder" sample.pdf="" style="border-style:solid;"><span style="font-weight:bold;">PLACEHOLDER</span> [name: sample.pdf; type: N/A]</p><p>Standard lessons page.</p><p data-sakaiid="/group/9da6b86e-15d3-4d29-b6f4-3a129109b869/Lessons/sample.pdf" data-type="placeholder" style="border-style:solid;"><span style="font-weight:bold;">PLACEHOLDER</span> [name: Embedded PDF; type: N/A]</p></div>'
                    self.assertEqual(html, items[1].attrs['html'])
                    self.assertEqual("1", items[2].attrs['type'])

                page_count += 1
