import argparse
import os
import shutil
import unittest

import config.config
from unittest.mock import patch
from work.lessonbuilder_merge_items import main
from bs4 import BeautifulSoup


class AddResourcesHtmlTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
        config.config.APP['archive_folder'] = self.ROOT_DIR + '/test_files/'

    @patch('argparse.ArgumentParser.parse_args',
           return_value=argparse.Namespace(SITE_ID='site_resource_html', debug=False))
    def test_add_resource_html(self, _):
        main()
        xml_src = self.ROOT_DIR + '/test_files/site_resource_html-archive/lessonbuilder.xml'
        xml_old = self.ROOT_DIR + '/test_files/site_resource_html-archive/lessonbuilder.xml.orig'
        file_path = os.path.join(xml_src)
        with open(file_path, "r", encoding="utf8") as fp:
            soup = BeautifulSoup(fp, 'xml')
            page = soup.find('item', attrs={"type": "5"})
            html = BeautifulSoup(page.get('html'), 'html.parser')
            div = html.find('div', attrs={"data-type": "folder-list"})
            self.assertIsNotNone(div)
            paragraphs = div.find_all('a')
            self.assertEqual(8, len(paragraphs))
        shutil.move(xml_old, xml_src)
