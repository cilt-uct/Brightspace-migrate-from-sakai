import os
import shutil
import unittest
import argparse

import config.config

from unittest.mock import patch
from work.check_for_placeholders import main

class PlaceholdersTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
        config.config.APP['archive_folder'] = self.ROOT_DIR + '/test_files/'

    @patch('argparse.ArgumentParser.parse_args',
           return_value=argparse.Namespace(SITE_ID='site_placeholder', IMPORT_ID='import', debug=False))
    @patch('lib.utils.middleware_api',
           side_effect=[{'status': 'success', 'data': [{'Description': {'Text': '', 'Html': '<p style="border-style:solid;" data-type="placeholder" data-sakaiid="sakaiID" data-name="sample.mp4"><span style="font-weight:bold;">PLACEHOLDER</span> [name: sample.mp4; type: video/mp4]</p>'}, 'ParentModuleId': None, 'ModuleDueDate': None, 'Structure': [{'Id': 633541, 'Title': 'Arrangements', 'ShortTitle': '', 'Type': 0, 'LastModifiedDate': '2022-11-11T17:01:01.080Z'}, {'Id': 633545, 'Title': 'sample.mp4', 'ShortTitle': '', 'Type': 0, 'LastModifiedDate': '2022-11-11T17:01:01.547Z'}], 'ModuleStartDate': None, 'ModuleEndDate': None, 'IsHidden': True, 'IsLocked': False, 'Id': 633540, 'Title': 'Resources', 'ShortTitle': '', 'Type': 0, 'LastModifiedDate': '2022-11-11T17:01:00.983Z'}]},
                        [{'status': 'success', 'data': {'ActivityId': 'https://ids.brightspace.com/activities/contenttopic/2A6C5E3E-963A-496E-8DA2-9ABB510E4C72-115000', 'IsExempt': False, 'DueDate': None, 'Description': {'Text': '', 'Html': ''}, 'ParentModuleId': 633452, 'OpenAsExternalResource': False, 'TopicType': 11, 'Url': 'd2l:brightspace:content:eu-west-1:dfe1698a-8384-4c5b-a2df-504f8d2a1d3b:video:cd79c5f1-90cb-40fa-9e5a-e1841300ef04/latest', 'StartDate': None, 'EndDate': None, 'IsHidden': True, 'IsLocked': False, 'IsBroken': False, 'ActivityType': 1, 'ToolId': None, 'ToolItemId': None, 'GradeItemId': None, 'AssociatedGradeItemIds': [], 'Id': 633545, 'Title': 'sample.mp4', 'ShortTitle': '', 'Type': 1, 'LastModifiedDate': '2023-10-02T10:46:14.230Z'}}],
                        {}])
    def test_check_for_placeholder(self, _, import_calls):
        main()

