#!/usr/bin/python3
# -*- coding: iso-8859-15 -*-

## This script accesses a Sakai DB (config.py) and exports the rubrics of a site to a packaged zip file.
## REF: AMA-37

import sys
import os
import argparse
import pymysql
import json

from pymysql.cursors import DictCursor

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *
from lib.local_auth import *


def getProviders(db_config, site_id):
    db = pymysql.connect(**db_config)
    cursor = db.cursor()

    SQL = """SELECT `provider`.PROVIDER_ID FROM SAKAI_REALM_PROVIDER `provider`
            left join SAKAI_REALM `realm` on `realm`.REALM_KEY = `provider`.REALM_KEY
            where `realm`.REALM_ID = %s;"""

    cursor.execute(SQL, f'/site/{site_id}')
    resp = {"success": 0, "message": ""}

    allRows = list( map(lambda st: re.sub(',\d{4}', '', st), [item[0] for item in cursor.fetchall()]) )
    return unique(allRows)

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
            logging.debug("Set providers: {} ({}-{})".format(provider_list, link_id, site_id))

    except Exception:
        logging.error(f"Could not update migration record {link_id} : {site_id}")
        return False

    return True

def run(SITE_ID, APP, link_id):
    logging.info('Update site provider : {}'.format(SITE_ID))

    tmp = getAuth(APP['auth']['sakai_db'])
    if (tmp is not None):
        SRC_DB = {'host' : tmp[0], 'database': tmp[1], 'user': tmp[2], 'password' : tmp[3]}
    else:
        logging.error("Authentication required (SRC)")
        return 0

    tmp = getAuth(APP['auth']['db'])
    if (tmp is not None):
        RUN_DB = {'host' : tmp[0], 'database': tmp[1], 'user': tmp[2], 'password' : tmp[3]}
    else:
        logging.error("Authentication required (Target)")
        return 0

    if (APP['debug']):
        print(f'{SITE_ID}\n{APP}\n{SRC_DB}\n{RUN_DB}')

    if update_providers(RUN_DB, link_id, SITE_ID, getProviders(SRC_DB, SITE_ID)):
        logging.info('\tDone')

def main():
    global APP
    parser = argparse.ArgumentParser(description="This script runs the workflow for a site",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("LINK_ID", help="The Link ID to run the workflow for")
    parser.add_argument("SITE_ID", help="The Site ID to run the workflow for")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())
    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP, args['LINK_ID'])

if __name__ == '__main__':
    main()
