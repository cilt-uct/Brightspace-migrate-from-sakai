# Methods that use tables in the Tsugi database
# migration_site

import pymysql
import pymysql.cursors
import json
import config.logging_config
from pymysql.cursors import DictCursor

def get_records(db_config, expiry_minutes: int = 0, state: str = None, order_by_zip: bool = False):
    try:
        connection = pymysql.connect(**db_config, cursorclass=pymysql.cursors.DictCursor)
        with connection:
            with connection.cursor() as cursor:
                sql = query_get_records(order_by_zip=order_by_zip, expiry_minutes=expiry_minutes)

                if expiry_minutes > 0:
                    cursor.execute(sql, (expiry_minutes, state))
                else:
                    cursor.execute(sql, state)
                return cursor.fetchall()

    except Exception as e:
        raise Exception('Could not retrieve migration records') from e


def get_record(db_config, link_id: str = None, site_id: str = None):
    try:
        connection = pymysql.connect(**db_config, cursorclass=pymysql.cursors.DictCursor)
        with connection:
            with connection.cursor() as cursor:
                sql = query_get_record()
                cursor.execute(sql, (link_id, site_id))
                return cursor.fetchone()

    except Exception:
        config.logging_config.logging.error(f"Could not retrieve migration record {link_id} : {site_id}")
        return None


def query_get_record():
    where = "A.link_id=%s AND A.site_id=%s"
    return query(where=where, limit=1)


def query_get_records(order_by_zip: bool = False, expiry_minutes: int = 0):
    where = "A.active=1 AND A.state=%s"
    if order_by_zip:
        ordered_by = "zip_size ASC"
    else:
        ordered_by = "started_at ASC"
    return query(where=where, ordered_by=ordered_by, expiry_minutes=expiry_minutes)


def query(where: str, ordered_by: str = None, limit: int = 0, expiry_minutes: int = 0):

    expired_sql = "if(uploaded_at + INTERVAL %s MINUTE < NOW(),'Y','N') AS expired," if expiry_minutes > 0 else ""
    order_sql = f"ORDER BY {ordered_by}" if ordered_by else ""
    limit_sql = f"LIMIT {limit}" if limit > 0 else ""

    return f"""SELECT A.*, {expired_sql}
               ifnull((SELECT site_id FROM migration_site B WHERE B.link_id = A.link_id AND B.state='admin'), A.site_id) AS url,
               (SELECT email FROM lti_user C WHERE C.user_id = A.started_by) AS started_by_email
               FROM migration_site A WHERE {where} {order_sql} {limit_sql}""".rstrip() + ";"

def get_state_count(db_config, state):
    try:
        connection = pymysql.connect(**db_config, cursorclass=DictCursor)
        with connection:
            with connection.cursor() as cursor:

                sql = """SELECT COUNT(state) as CountOfState FROM migration_site WHERE state = %s;"""
                cursor.execute(sql, (state))
                return cursor.fetchone()['CountOfState']

    except Exception as e:
        config.logging_config.logging.error(f"Could not retrieve state {state}: {e}")
        return None

def set_uploaded_at(db_config, link_id, site_id):
    try:
        connection = pymysql.connect(**db_config, cursorclass=DictCursor)
        with connection:
            with connection.cursor() as cursor:
                # Create a new record
                sql = """UPDATE `migration_site` SET modified_at = NOW(), modified_by = 1, uploaded_at = NOW()
                         WHERE `link_id` = %s and site_id = %s;"""
                cursor.execute(sql, (link_id, site_id))

            connection.commit()

    except Exception:
        config.logging_config.logging.error(f"Could not update migration record {link_id} : {site_id}")
        return None

def update_providers(db_config, link_id, site_id, provider_list):
    try:
        connection = pymysql.connect(**db_config, cursorclass=DictCursor)
        with connection:
            with connection.cursor() as cursor:
                # Create a new record
                sql = """UPDATE `migration_site` SET modified_at = NOW(), modified_by = 1, provider = %s
                         WHERE `link_id` = %s and site_id = %s and (provider is null or length(provider) <= 2);"""
                cursor.execute(sql, (json.dumps(provider_list), link_id, site_id))

            connection.commit()
            config.logging_config.logging.debug("Set providers: {} ({}-{})".format(provider_list, link_id, site_id))

    except Exception:
        config.logging_config.logging.error(f"Could not update migration record {link_id} : {site_id}")
        return False

    return True

def set_to_state(db_config, link_id, site_id, new_state):

    try:
        connection = pymysql.connect(**db_config, cursorclass=DictCursor)
        with connection:
            with connection.cursor() as cursor:
                # Create a new record
                sql = """UPDATE `migration_site` SET modified_at = NOW(), modified_by = 1, state = %s
                         WHERE `link_id` = %s and site_id = %s;"""
                cursor.execute(sql, (new_state, link_id, site_id))

            connection.commit()
            config.logging_config.logging.debug("Set to {} for ({}-{})".format(new_state, link_id, site_id))

    except Exception as e:
        raise Exception(f'Could not set_to_updating for {link_id} : {site_id}') from e
