import unittest

import lib.db
from lib.utils import stripspace

class QueryTestCase(unittest.TestCase):
    def test_query_get_records(self):
        self.maxDiff = None
        expected = """SELECT A.*,
               ifnull((SELECT site_id FROM migration_site B
               WHERE B.link_id = A.link_id AND B.state='admin'), A.site_id) AS url,
               (SELECT email FROM lti_user C WHERE C.user_id = A.started_by) AS started_by_email
               FROM migration_site A WHERE A.active=1 AND A.state=%s ORDER BY zip_size ASC;"""
        actual = lib.db.query_get_records(order_by_zip=True)
        self.assertEqual(stripspace(expected), stripspace(actual))

    def test_query_get_records_minutes(self):
        self.maxDiff = None
        expected = """SELECT A.*, if(uploaded_at + INTERVAL %s MINUTE < NOW(),'Y','N') AS expired,
               ifnull((SELECT site_id FROM migration_site B WHERE B.link_id = A.link_id AND B.state='admin'), A.site_id) AS url,
               (SELECT email FROM lti_user C WHERE C.user_id = A.started_by) AS started_by_email
               FROM migration_site A WHERE A.active=1 AND A.state=%s ORDER BY zip_size ASC;"""
        actual = lib.db.query_get_records(order_by_zip=True, expiry_minutes=1)
        self.assertEqual(stripspace(expected), stripspace(actual))

    def test_query_get_records_no_zip(self):
        self.maxDiff = None
        expected = """SELECT A.*,
               if(uploaded_at + INTERVAL %s MINUTE < NOW(),'Y','N') AS expired,
               ifnull((SELECT site_id FROM migration_site B WHERE B.link_id = A.link_id AND B.state='admin'), A.site_id) AS url,
               (SELECT email FROM lti_user C WHERE C.user_id = A.started_by) AS started_by_email
               FROM migration_site A WHERE A.active=1 AND A.state=%s ORDER BY started_at ASC;"""
        actual = lib.db.query_get_records(order_by_zip=False, expiry_minutes=1)
        self.assertEqual(stripspace(expected), stripspace(actual))

    def test_query_get_record(self):
        self.maxDiff = None
        expected = """SELECT A.*,
               ifnull((SELECT site_id FROM migration_site B WHERE B.link_id = A.link_id AND B.state='admin'), A.site_id) AS url,
               (SELECT email FROM lti_user C WHERE C.user_id = A.started_by) AS started_by_email
               FROM migration_site A WHERE A.link_id=%s AND A.site_id=%s LIMIT 1;"""
        actual = lib.db.query_get_record()
        self.assertEqual(stripspace(expected), stripspace(actual))

if __name__ == '__main__':
    unittest.main(failfast=True)
