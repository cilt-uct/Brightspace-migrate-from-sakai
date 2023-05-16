import os
import unittest
import argparse

from bs4 import BeautifulSoup

import config.config
from work.generate_conversion_report import main
from unittest.mock import patch


class GenerateConversionReportTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
        config.config.APP['report']['json'] = self.ROOT_DIR + '/../config/conversion_issues.json'
        config.config.APP['report']['output'] = self.ROOT_DIR + '/test_files'
        config.config.APP['output'] = self.ROOT_DIR + '/test_files'


    @patch('argparse.ArgumentParser.parse_args',
           return_value=argparse.Namespace(SITE_ID='55be22eb-fc01-4ba8-bec7-6a9904bdbe76', ISSUE_KEY='a6', debug=False))
    @patch('work.generate_conversion_report.init__soup', return_value=BeautifulSoup())
    @patch('lib.utils.read_yaml', return_value={'STEPS': [{'action': 'mail', 'template': 'finished',
                                                           'subject': 'my email subject'}]})
    @patch('work.generate_conversion_report.html')
    @patch('lib.local_auth.getAuth', return_value=['host', 'db', 'user', 'pass'])
    @patch('work.generate_conversion_report.do_check', return_value=True)
    @patch('logging.info')
    def test_main(self, mock_log, mock_check, *_):
        main()
        self.assertTrue(mock_check.called)
        self.assertEqual(1, mock_check.call_count)
        self.assertTrue(mock_log.called)
        self.assertEqual(1, mock_log.call_count)
        self.assertEqual('Executed conversion check a6 for site 55be22eb-fc01-4ba8-bec7-6a9904bdbe76: True',
                         mock_log.call_args.args[0])

    @patch('argparse.ArgumentParser.parse_args',
           return_value=argparse.Namespace(SITE_ID='55be22eb-fc01-4ba8-bec7-6a9904bdbe76', ISSUE_KEY=None, debug=False))
    @patch('work.generate_conversion_report.init__soup', return_value=BeautifulSoup())
    @patch('lib.utils.read_yaml', return_value={'STEPS': [{'action': 'mail', 'template': 'finished',
                                                           'subject': 'my email subject'}]})
    @patch('work.generate_conversion_report.html')
    @patch('lib.local_auth.getAuth', return_value=['host', 'db', 'user', 'pass'])
    @patch('pymysql.connect')
    @patch('work.generate_conversion_report.do_check', return_value=True)
    @patch('logging.info')
    def test_main_no_issue_key(self, mock_log, mock_check, *_):
        main()
        self.assertTrue(mock_check.called)
        self.assertTrue(mock_check.call_count>1)
        self.assertFalse(mock_log.called)
        self.assertEqual(0, mock_log.call_count)

if __name__ == '__main__':
    unittest.main(failfast=True)
