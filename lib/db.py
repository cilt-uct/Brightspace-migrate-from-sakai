import pymysql
import pymysql.cursors
import config.logging_config

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
    where = f"A.active=1 AND A.state=%s"
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
