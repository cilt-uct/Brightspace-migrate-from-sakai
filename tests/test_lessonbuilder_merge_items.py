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
                    # Merge html text + PDF
                    self.assertEqual(2, len(items))
                    self.assertEqual("5", items[0].attrs['type'])
                    html = '<div><p>Standard lessons page.</p><p><a href="https://vula.uct.ac.za/access/content/group/81814b18-6ae4-4570-be9d-7459154a94b4/Lessons 2.0/sample.pdf">sample.pdf</a></p></div>'
                    self.assertEqual(html, items[0].attrs['html'])
                    self.assertEqual("7", items[1].attrs['type'])
                if page_count == 1:
                    # Merge PDF + html text
                    self.assertEqual(2, len(items))
                    self.assertEqual("7", items[0].attrs['type'])
                    self.assertEqual("5", items[1].attrs['type'])
                    html = '<div><p><a href="https://vula.uct.ac.za/access/content/group/81814b18-6ae4-4570-be9d-7459154a94b4/Lessons 2.0/sample.pdf">sample.pdf</a></p><p>Standard lessons page.</p></div>'
                    self.assertEqual(html, items[1].attrs['html'])
                if page_count == 2:
                    # Merge PDF + html text + PDF
                    self.assertEqual(3, len(items))
                    self.assertEqual("7", items[0].attrs['type'])
                    self.assertEqual("5", items[1].attrs['type'])
                    html = '<div><p><a href="https://vula.uct.ac.za/access/content/group/81814b18-6ae4-4570-be9d-7459154a94b4/Lessons 2.0/sample.pdf">sample.pdf</a></p><p>Standard lessons page.</p><p><a href="https://vula.uct.ac.za/access/content/group/9da6b86e-15d3-4d29-b6f4-3a129109b869/Lessons/sample.pdf">Embedded PDF</a></p></div>'
                    self.assertEqual(html, items[1].attrs['html'])
                    self.assertEqual("1", items[2].attrs['type'])
                if page_count == 3:
                    # Merge html text + html text
                    self.assertEqual(1, len(items))
                    self.assertEqual("5", items[0].attrs['type'])
                    html = '<div><p>Embedded in the text field and not in the lessons page.</p><p>Here is a video below embedded in the lessons page.</p></div>'
                    self.assertEqual(html, items[0].attrs['html'])
                if page_count == 4:
                    # Merge html text + html text + embedded link + embedded link
                    self.assertEqual(3, len(items))
                    self.assertEqual("5", items[0].attrs['type'])
                    html = '<div><p>Embedded in the text field and not in the lessons page.</p><p>Here is a video below embedded in the lessons page.</p><p><a href="https://google.com" rel="noopener" target="_blank">Search with Google</a></p><p><a href="https://google.com" rel="noopener" target="_blank">Search with Google as an embed</a></p></div>'
                    self.assertEqual(html, items[0].attrs['html'])
                    self.assertEqual("1", items[1].attrs['type'])
                    self.assertEqual("7", items[2].attrs['type'])
                if page_count == 5:
                    # Merge html text + mp4
                    self.assertEqual(2, len(items))
                    self.assertEqual("5", items[0].attrs['type'])
                    html = '<div><p>Embedded in the text field and not in the lessons page.</p><p _="" data-sakaiid="/group/9917b8aa-d130-48dd-9c9c-48b280e4eadb/EWC/Business" data-type="placeholder" plan="" style="border-style:solid;" video.mp4=""><span style="font-weight:bold;">PLACEHOLDER</span> [name: Business Plan _ video.mp4; type: video/mp4]</p></div>'
                    self.assertEqual(html, items[0].attrs['html'])
                    self.assertEqual("1", items[1].attrs['type'])

                page_count += 1
