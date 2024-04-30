# Direct read access to the Sakai database

import pymysql
import pymysql.cursors
import logging
import os
import sys

from pymysql.cursors import DictCursor

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from lib.local_auth import getAuthDict

class SakaiDb:

    def __init__(self, APP):

        auth = getAuthDict(APP['auth']['sakai_db'])

        if auth is None:
            raise Exception("Authentication required for Sakai database")

        self.db_config = {
                'host' : auth['hostname'],
                'database': auth['database'],
                'user': auth['username'],
                'password' : auth['password']
        }

        if not self.validate_connection():
            raise Exception(f"Unable to validate connection to mysql db: {auth['hostname']}:{auth['database']}:{auth['username']}")


    def validate_connection(self):

        # Validate db connection and tables rbc_*
        # We expect 13 tables in a Sakai 21 database

        try:
            connection = pymysql.connect(**self.db_config, cursorclass=DictCursor)
            with connection:
                with connection.cursor() as cursor:
                    sql = "SHOW TABLES LIKE 'rbc_%'"
                    cursor.execute(sql)
                    if len(cursor.fetchall()) != 13:
                        return False

        except Exception as e:
            logging.exception(f"Could not valid mysql connection: {e}")
            return False

        return True
