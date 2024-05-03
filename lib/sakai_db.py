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

from lib.local_auth import getAuth

class SakaiDb:

    def __init__(self, APP):

        auth = getAuth(APP['auth']['sakai_db'], ['hostname', 'database', 'username', 'password'])

        if not auth['valid']:
            raise Exception("Authentication required for Sakai database")

        self.db_config = {
                'host' : auth['hostname'],
                'database': auth['database'],
                'user': auth['username'],
                'password' : auth['password']
        }

        # Optional string parameters: https://pymysql.readthedocs.io/en/latest/modules/connections.html
        opt_params = ['charset', 'ssl_ca', 'ssl_cert', 'ssl_disabled', 'ssl_key', 'ssl_key_password',
                'ssl_verify_cert', 'ssl_verify_identity', 'server_public_key']

        for opt_param in opt_params:
            if opt_param in auth:
                self.db_config[opt_param] = auth[opt_param]

        if not self.validate_connection():
            raise Exception(f"Unable to validate connection to mysql db: {auth['hostname']}:{auth['database']}:{auth['username']}")


    def validate_connection(self):

        # Validate db connection and tables
        # We expect at least 40 SAKAI_* tables in a Sakai database
        try:
            if self.table_count("SAKAI_") < 40:
                logging.error(f"Expected tables not found in mysql db: {self.db_config['host']}:{self.db_config['database']}")
                return False

        except Exception as e:
            logging.error(f"Could not validate mysql connection: {e}")
            return False

        return True

    def table_count(self, prefix):
        # Count of tables matching prefix
        connection = pymysql.connect(**self.db_config, cursorclass=DictCursor)
        with connection:
            with connection.cursor() as cursor:
                sql = "SHOW TABLES LIKE %s"
                cursor.execute(sql, f"{prefix}%")
                return len(cursor.fetchall())
