import unittest

import config.config
import lib.local_auth
import lib.d2l

class GenerateConversionReportTestCase(unittest.TestCase):
    def setUp(self) -> None:
        try:
            web_auth = lib.local_auth.getAuth('BrightspaceWeb')
            if web_auth is not None:
                self.username = web_auth[0]
                self.password = web_auth[1]
            else:
                raise Exception("Please update username and password before running the GenerateConversionReportTestCase.")
        except FileNotFoundError:
            self.username = None
            self.password = None
            raise Exception("For local tests, please update username and password.")

    def test_login(self):
        APP = config.config.APP
        url = f"{APP['brightspace_url']}/d2l/lp/auth/login/login.d2l"
        res = lib.d2l.web_login(url, username=self.username, password=self.password)
        self.assertIsNotNone(res)

    def test_get_org(self):
        APP = config.config.APP
        url = f"{APP['brightspace_url']}/d2l/lp/auth/login/login.d2l"
        login = lib.d2l.web_login(url, username=self.username, password=self.password)
        res = lib.d2l.get_import_history(APP['brightspace_url'], 12980, login)
        self.assertIsNotNone(res)

    def test_get_status(self):
        res = '<div><d2l-status-indicator state="Failed" text="Failed">Indicator</d2l-status-indicator></div>'
        content = lib.d2l.get_first_import_status(res)
        self.assertIsNotNone(content)
        self.assertEqual('Failed', content)

    def test_get_import_job_log(self):
        res = '<div><a class="class1 class2" href=https://amatuba.co.za/logs/2390/Display">View Import Log</a></div>'
        content = lib.d2l.get_first_import_job_log(res)
        self.assertIsNotNone(content)
        self.assertEqual('2390', content)


if __name__ == '__main__':
    unittest.main(failfast=True)
