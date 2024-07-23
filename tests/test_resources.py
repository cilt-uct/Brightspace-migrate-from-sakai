import os
import unittest
import argparse

import config.config
from unittest.mock import patch

from lib.resources import resource_exists, get_content_displayname, get_content_owner

class ResourcesSpecialCharsTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
        config.config.APP['archive_folder'] = self.ROOT_DIR + '/test_files/'

    @patch('argparse.ArgumentParser.parse_args', return_value=argparse.Namespace(SITE_ID='site_resource_special', debug=True))

    # Resource IDs with apostrophes
    def test_resource_id_chars(self, *_):
        site_folder = self.ROOT_DIR + '/test_files/site_resource_special-archive'

        # Doesn't exist
        self.assertFalse(resource_exists(site_folder, "zaphod"))

        # Folder with underscore
        collection_id = "/group/4bc86af2-7ed2-4659-bc86-9cdbda4fb494/quoted_name/"
        self.assertTrue(resource_exists(site_folder, collection_id))

        # Folder with apostrophe
        collection_id = "/group/4bc86af2-7ed2-4659-bc86-9cdbda4fb494/apos'trophe2/"
        self.assertTrue(resource_exists(site_folder, collection_id))

        # Resource with apostrophe
        resource_id = "/group/4bc86af2-7ed2-4659-bc86-9cdbda4fb494/apos'trophe2/test'file.txt.txt"
        self.assertTrue(resource_exists(site_folder, resource_id))
        self.assertEquals(get_content_displayname(site_folder, resource_id), "test'file.txt.txt")
        self.assertEquals(get_content_owner(site_folder, resource_id), ("marquard", "01404877"))

        # Folder with quote
        collection_id = '/group/4bc86af2-7ed2-4659-bc86-9cdbda4fb494/quoted"name2/'
        self.assertTrue(resource_exists(site_folder, collection_id))

        # Resource with quote
        resource_id = '/group/4bc86af2-7ed2-4659-bc86-9cdbda4fb494/quoted"name2/quoted"file.txt'
        self.assertTrue(resource_exists(site_folder, resource_id))


if __name__ == '__main__':
    unittest.main(failfast=True)
