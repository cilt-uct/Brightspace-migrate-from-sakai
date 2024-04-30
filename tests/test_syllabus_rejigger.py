import os
import shutil
import unittest
import argparse
import base64

import config.config
from work.syllabus_rejigger import main
from unittest.mock import patch
import xml.etree.ElementTree as ET


class SyllabusRejiggerTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
        config.config.APP['archive_folder'] = self.ROOT_DIR + '/test_files/'

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

        original = "PHAgc3R5bGU9InRleHQtYWxpZ246IGNlbnRlcjsiPjxpbWcgYWx0PSIiIGhlaWdodD0iMTExNiIgc3JjPSJodHRwczovL3Z1bGEudWN0LmFjLnphL2FjY2Vzcy9jb250ZW50L2dyb3VwLzlhYWVkYTI2LTU5YjgtNGVjMi04YzE5LTk1Nzk3ZmE4YWE0My9BZG1pbi9MZXNzb24lMjBwbGFuJTIwdjMucGRmIiB3aWR0aD0iMjAwMCIgLz48L3A+CgoKPGgzPkF0dGFjaG1lbnRzPC9oMz4KCjx1bD4KPGxpPjxhIGhyZWY9Imh0dHBzOi8vdnVsYS51Y3QuYWMuemEvYWNjZXNzL2NvbnRlbnQvYXR0YWNobWVudC85YWFlZGEyNi01OWI4LTRlYzItOGMxOS05NTc5N2ZhOGFhNDMvTGVzc29uIFBsYW4vNzZlMDk2YTQtMjBkMC00YzVmLWI1ZTYtNWY0MDYzOTYyMjg1L0xlc3NvbiBwbGFuIHYzLnBkZiI+TGVzc29uIHBsYW4gdjMucGRmPC9hPjwvbGk+CjwvdWw+Cg=="
        new = 'PGgyPkxlc3NvbiBwbGFuIHYzLjAgLSAwOS8wOS8yMTwvaDI+Cgo8cCBzdHlsZT0idGV4dC1hbGlnbjogY2VudGVyOyI+PGltZyBhbHQ9IiIgaGVpZ2h0PSIxMTE2IiBzcmM9Imh0dHBzOi8vdnVsYS51Y3QuYWMuemEvYWNjZXNzL2NvbnRlbnQvZ3JvdXAvOWFhZWRhMjYtNTliOC00ZWMyLThjMTktOTU3OTdmYThhYTQzL0FkbWluL0xlc3NvbiUyMHBsYW4lMjB2My5wZGYiIHdpZHRoPSIyMDAwIiAvPjwvcD4KCgo8aDM+QXR0YWNobWVudHM8L2gzPgoKPHVsPgo8bGk+PGEgaHJlZj0iaHR0cHM6Ly92dWxhLnVjdC5hYy56YS9hY2Nlc3MvY29udGVudC9hdHRhY2htZW50LzlhYWVkYTI2LTU5YjgtNGVjMi04YzE5LTk1Nzk3ZmE4YWE0My9MZXNzb24gUGxhbi83NmUwOTZhNC0yMGQwLTRjNWYtYjVlNi01ZjQwNjM5NjIyODUvTGVzc29uIHBsYW4gdjMucGRmIj5MZXNzb24gcGxhbiB2My5wZGY8L2E+PC9saT4KPC91bD4KPGgyPkxlc3NvbiBwbGFuIHYzLjAgLSAwOS8wOS8yMTwvaDI+Cgo8cCBzdHlsZT0idGV4dC1hbGlnbjogY2VudGVyOyI+PGltZyBhbHQ9IiIgaGVpZ2h0PSIxMTE2IiBzcmM9Imh0dHBzOi8vdnVsYS51Y3QuYWMuemEvYWNjZXNzL2NvbnRlbnQvZ3JvdXAvOWFhZWRhMjYtNTliOC00ZWMyLThjMTktOTU3OTdmYThhYTQzL0FkbWluL0xlc3NvbiUyMHBsYW4lMjB2My5wZGYiIHdpZHRoPSIyMDAwIiAvPjwvcD4KCgo8aDM+QXR0YWNobWVudHM8L2gzPgoKPHVsPgo8bGk+PGEgaHJlZj0iaHR0cHM6Ly92dWxhLnVjdC5hYy56YS9hY2Nlc3MvY29udGVudC9hdHRhY2htZW50LzlhYWVkYTI2LTU5YjgtNGVjMi04YzE5LTk1Nzk3ZmE4YWE0My9MZXNzb24gUGxhbi83NmUwOTZhNC0yMGQwLTRjNWYtYjVlNi01ZjQwNjM5NjIyODUvTGVzc29uIHBsYW4gdjMucGRmIj5MZXNzb24gcGxhbiB2My5wZGY8L2E+PC9saT4KPC91bD4K'
        self.assertEqual(new, encoded_html)
        self.assertNotEqual(original, encoded_html)

        decoded_html = base64.b64decode(encoded_html).decode("utf-8")
        self.assertIsNotNone(decoded_html)


if __name__ == '__main__':
    unittest.main(failfast=True)
