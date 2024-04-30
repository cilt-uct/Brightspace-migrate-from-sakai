# Methods that use tables in the Tsugi database
# migration_site

import pymysql
import pymysql.cursors
import json
import logging
import os
import sys

from pymysql.cursors import DictCursor

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from lib.local_auth import getAuthDict

class MigrationDb:

    def __init__(self, APP):

        auth = getAuthDict(APP['auth']['db'])

        if auth is None:
            raise Exception("Authentication required for migration database")

        self.db_config = {
                'host' : auth['hostname'],
                'database': auth['database'],
                'user': auth['username'],
                'password' : auth['password']
        }

        if not self.validate_connection():
            raise Exception(f"Unable to validate connection to mysql db: {auth['hostname']}:{auth['database']}:{auth['username']}")


    def validate_connection(self):

        # Validate db connection and tables migration, migration_site, migration_site_property, lti_user

        try:
            connection = pymysql.connect(**self.db_config, cursorclass=DictCursor)
            with connection:
                with connection.cursor() as cursor:
                    sql = "SHOW TABLES LIKE 'migration%'"
                    cursor.execute(sql)
                    if len(cursor.fetchall()) != 3:
                        return False

                    sql = "SHOW TABLES LIKE 'lti_user'"
                    cursor.execute(sql)
                    if len(cursor.fetchall()) != 1:
                        return False

        except Exception as e:
            logging.exception(f"Could not valid mysql connection: {e}")
            return False

        return True


    def get_records(self, expiry_minutes: int = 0, state: str = None, order_by_zip: bool = False):
        try:
            connection = pymysql.connect(**self.db_config, cursorclass=DictCursor)
            with connection:
                with connection.cursor() as cursor:
                    sql = MigrationDb.query_get_records(order_by_zip=order_by_zip, expiry_minutes=expiry_minutes)

                    if expiry_minutes > 0:
                        cursor.execute(sql, (expiry_minutes, state))
                    else:
                        cursor.execute(sql, state)
                    return cursor.fetchall()

        except Exception as e:
            raise Exception('Could not retrieve migration records') from e


    def get_record(self, link_id: str = None, site_id: str = None):
        try:
            connection = pymysql.connect(**self.db_config, cursorclass=DictCursor)
            with connection:
                with connection.cursor() as cursor:
                    sql = MigrationDb.query_get_record()
                    cursor.execute(sql, (link_id, site_id))
                    return cursor.fetchone()

        except Exception:
            logging.error(f"Could not retrieve migration record {link_id} : {site_id}")
            return None


    def query_get_record():
        where = "A.link_id=%s AND A.site_id=%s"
        return MigrationDb.query(where=where, limit=1)


    def query_get_records(order_by_zip: bool = False, expiry_minutes: int = 0):
        where = "A.active=1 AND A.state=%s"
        if order_by_zip:
            ordered_by = "zip_size ASC"
        else:
            ordered_by = "started_at ASC"
        return MigrationDb.query(where=where, ordered_by=ordered_by, expiry_minutes=expiry_minutes)


    def query(where: str, ordered_by: str = None, limit: int = 0, expiry_minutes: int = 0):

        expired_sql = "if(uploaded_at + INTERVAL %s MINUTE < NOW(),'Y','N') AS expired," if expiry_minutes > 0 else ""
        order_sql = f"ORDER BY {ordered_by}" if ordered_by else ""
        limit_sql = f"LIMIT {limit}" if limit > 0 else ""

        return f"""SELECT A.*, {expired_sql}
                   ifnull((SELECT site_id FROM migration_site B WHERE B.link_id = A.link_id AND B.state='admin'), A.site_id) AS url,
                   (SELECT email FROM lti_user C WHERE C.user_id = A.started_by) AS started_by_email
                   FROM migration_site A WHERE {where} {order_sql} {limit_sql}""".rstrip() + ";"

    def get_state_count(self, state):
        try:
            connection = pymysql.connect(**self.db_config, cursorclass=DictCursor)
            with connection:
                with connection.cursor() as cursor:

                    sql = """SELECT COUNT(state) as CountOfState FROM migration_site WHERE state = %s;"""
                    cursor.execute(sql, (state))
                    return cursor.fetchone()['CountOfState']

        except Exception as e:
            logging.error(f"Could not retrieve state {state}: {e}")
            return None

    def set_uploaded_at(self, link_id, site_id):
        try:
            connection = pymysql.connect(**self.db_config, cursorclass=DictCursor)
            with connection:
                with connection.cursor() as cursor:
                    # Create a new record
                    sql = """UPDATE `migration_site` SET modified_at = NOW(), modified_by = 1, uploaded_at = NOW()
                             WHERE `link_id` = %s and site_id = %s;"""
                    cursor.execute(sql, (link_id, site_id))

                connection.commit()

        except Exception:
            logging.error(f"Could not update migration record {link_id} : {site_id}")
            return None

    def update_providers(self, link_id, site_id, provider_list):
        try:
            connection = pymysql.connect(**self.db_config, cursorclass=DictCursor)
            with connection:
                with connection.cursor() as cursor:
                    # Create a new record
                    sql = """UPDATE `migration_site` SET modified_at = NOW(), modified_by = 1, provider = %s
                             WHERE `link_id` = %s and site_id = %s and (provider is null or length(provider) <= 2);"""
                    cursor.execute(sql, (json.dumps(provider_list), link_id, site_id))

                connection.commit()
                logging.debug("Set providers: {} ({}-{})".format(provider_list, link_id, site_id))

        except Exception:
            logging.error(f"Could not update migration record {link_id} : {site_id}")
            return False

        return True

    def set_to_state(self, link_id, site_id, new_state):

        try:
            connection = pymysql.connect(**self.db_config, cursorclass=DictCursor)
            with connection:
                with connection.cursor() as cursor:
                    # Create a new record
                    sql = """UPDATE `migration_site` SET modified_at = NOW(), modified_by = 1, state = %s
                             WHERE `link_id` = %s and site_id = %s;"""
                    cursor.execute(sql, (new_state, link_id, site_id))

                connection.commit()
                logging.debug("Set to {} for ({}-{})".format(new_state, link_id, site_id))

        except Exception as e:
            raise Exception(f'Could not set_to_updating for {link_id} : {site_id}') from e

    def set_running(self, link_id, site_id):
        try:
            connection = pymysql.connect(**self.db_config, cursorclass=DictCursor)
            with connection:
                with connection.cursor() as cursor:
                    # Create a new record
                    sql = """UPDATE `migration_site` SET modified_at = NOW(), modified_by = 1, active = %s, state = %s
                             WHERE `link_id` = %s and site_id = %s;"""
                    cursor.execute(sql, ('1', 'exporting', link_id, site_id))

                connection.commit()

        except Exception as e:
            raise Exception(f'Could not update migration record {link_id} : {site_id}') from e

    def another_running(self, link_id, site_id):

        # Possible states:
        # ('init','starting','exporting','running','queued','uploading','importing','updating','completed','error','paused','admin')

        try:
            connection = pymysql.connect(**self.db_config, cursorclass=DictCursor)
            with connection:
                with connection.cursor() as cursor:
                    sql = """SELECT link_id FROM migration_site `A`
                                where  `A`.link_id <> %s and `A`.site_id = %s and `active` = 1
                                and `A`.state NOT in ('init', 'starting', 'completed', 'error')"""
                    cursor.execute(sql, (link_id, site_id))
                    cursor.fetchall()
                    return cursor.rowcount

        except Exception as e:
            raise Exception('Could not check on migration records') from e

        return 0
