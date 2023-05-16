import argparse
import os
import work.lessonbuilder_merge_items
import unittest
from bs4 import BeautifulSoup
from unittest.mock import patch

class MergeTestCases(unittest.TestCase):

    def setUp(self) -> None:
        self.ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

    @patch('os.rename')
    @patch('argparse.ArgumentParser.parse_args', return_value=argparse.Namespace(SITE_ID='site_id', debug=True))
    def test_read_xml(self, *_):
        work.lessonbuilder_merge_items.main()
        with open(self.ROOT_DIR + '/test_files/output.xml', 'r') as f:
            data = f.read()

        all_xml = BeautifulSoup(data, "xml")
        pages = all_xml.find_all('page')
        items = []
        for page in pages:
            page_items = page.find_all('item')
            items.extend(page_items)

        self.assertEqual(2, len(pages))
        self.assertEqual(16, len(items))

    def test_remove_adj_breaks(self):
        with open(self.ROOT_DIR + '/test_files/test_breaks.xml', 'r') as f:
            data = f.read()

        all_xml = BeautifulSoup(data, "xml")
        page = all_xml.find('page')
        items = page.find_all('item')
        items = work.lessonbuilder_merge_items.remove_adj_breaks(items=items)
        self.assertEqual(4, len(items))

    def test_remove_breaks(self):
        with open(self.ROOT_DIR + '/test_files/test_breaks.xml', 'r') as f:
            data = f.read()

        all_xml = BeautifulSoup(data, "xml")
        page = all_xml.find('page')
        items = page.find_all('item')
        items = work.lessonbuilder_merge_items.remove_breaks(items=items)
        self.assertEqual(2, len(items))

    def test_remove_break_and_text(self):
        with open(self.ROOT_DIR + '/test_files/test_text_break_text.xml', 'r') as f:
            data = f.read()

        all_xml = BeautifulSoup(data, "xml")
        page = all_xml.find('page')
        items = page.find_all('item')
        items = work.lessonbuilder_merge_items.remove_break_and_text(items=items)
        self.assertEqual(2, len(items))
        self.assertEqual('my html<hr>my html', items[0]['html'])
        self.assertEqual('my html<hr>my html', items[1]['html'])

    def test_merge_adj_text(self):
        with open(self.ROOT_DIR + '/test_files/test_text_text.xml', 'r') as f:
            data = f.read()

        all_xml = BeautifulSoup(data, "xml")
        page = all_xml.find('page')
        items = page.find_all('item')
        items = work.lessonbuilder_merge_items.merge_adj_text(items=items)
        self.assertEqual(1, len(items))
        self.assertEqual('my htmlmy htmlmy htmlmy html', items[0]['html'])

    def test_name_nameless_items(self):
        with open(self.ROOT_DIR + '/test_files/test_nameless.xml', 'r') as f:
            data = f.read()

        all_xml = BeautifulSoup(data, "xml")
        page = all_xml.find('page')
        items = page.find_all('item')
        items = work.lessonbuilder_merge_items.name_nameless_items(items=items)
        self.assertEqual(2, len(items))
        self.assertEqual('Header name', items[0]['name'])
        self.assertEqual('Header name', items[1]['name'])

if __name__ == '__main__':
    unittest.main(failfast=True)
