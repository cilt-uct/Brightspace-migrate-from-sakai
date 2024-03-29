#!/usr/bin/python3

## Once-off check for sites marked completed with D2L import errors

import sys
import os
import argparse
import pymysql
import logging
import re
import requests


from pymysql.cursors import DictCursor

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.config import *
from lib.utils import *
from lib.local_auth import *

from work.archive_site import *

from work.generate_conversion_report import *

def get_records(db_config):
    try:
        connection = pymysql.connect(**db_config, cursorclass=DictCursor)
        with connection:
            with connection.cursor() as cursor:
                sql = """SELECT link_id, site_id, transfer_site_id, imported_site_id FROM migration_site
                            where state = 'completed' and transfer_site_id is not null and imported_site_id is not null
                            order by started_at asc ;"""

                cursor.execute(sql)
                return cursor.fetchall()

    except Exception as e:
        raise Exception('Could not retrieve migration records') from e

def get_import_history(brightspace_url, org_unit, session):
    logging.info(f"Getting import history for {org_unit}")
    url = f'{brightspace_url}/d2l/le/conversion/import/{org_unit}/history/display?ou={org_unit}'
    r = session.get(url)
    return r.text

def get_first_import_status(content):
    pattern = re.compile('<d2l-status-indicator state="(.*?)" text="(.*?)"(.*?)>')
    if pattern.search(content):
        return pattern.search(content).group(2)

def get_first_import_job_log(content):
    pattern = re.compile('<a class=(.*?) href=(.*?)logs/(.*?)/Display">View Import Log(.*?)')
    if pattern.search(content):
        return pattern.search(content).group(3)

def web_login(login_url, username, password):

    values = {
        'web_loginPath': '/d2l/login',
        'username': username,
        'password': password
    }

    session = requests.Session()
    session.post(login_url, data=values)
    return session

def get_import_status_collection(brightspace_url, WEB_AUTH, orgunit_ids):

    login_url = f'{brightspace_url}/d2l/lp/auth/login/login.d2l'
    session = web_login(login_url, WEB_AUTH['username'], WEB_AUTH['password'])

    status_list = { }
    for orgunit_id in orgunit_ids:
        content = get_import_history(brightspace_url, orgunit_id, session)
        status_list[orgunit_id] = {
                'status': get_first_import_status(content),
                'job_id': get_first_import_job_log(content)
        }

    return status_list

def run(APP):

    brightspace_url = APP['brightspace_url']

    tmp = getAuth(APP['auth']['db'])
    if (tmp is not None):
        DB_AUTH = {'host' : tmp[0], 'database': tmp[1], 'user': tmp[2], 'password' : tmp[3]}
    else:
        raise Exception("DB Authentication required")

    webAuth = lib.local_auth.getAuth('BrightspaceWeb')
    if (webAuth is not None):
        WEB_AUTH = {'username': webAuth[0], 'password' : webAuth[1]}
    else:
        raise Exception('Web Authentication required [getBrightspaceWebAuth]')

    logging.info(f"Checking for sites migrated to {brightspace_url}")

    all_sites = get_records(DB_AUTH)

    logging.info(f"{len(all_sites)} completed sites")

    ouids = []
    ouid_site = {}

    for site in all_sites:
        try:
            logging.debug(f"Site {site['site_id']} ")
            ouids.append(site['imported_site_id'])
            ouid_site[site['imported_site_id']] = f"{site['site_id']} {site['link_id']}"

        except Exception as e:
            logging.exception(e)

    logging.info(f"{len(ouids)} org unit ids")

    status_collection = get_import_status_collection(brightspace_url, WEB_AUTH, ouids)
    for ouid in ouids:
        logging.debug(f"ouid {ouid} ")
        status = status_collection[ouid]
        if 'status' in status and status['status'] is not None and status['status'] != "Complete":
            logging.warning(f"site {ouid_site[ouid]} ouid {ouid} not completed: {status['status']}")

def main():
    global APP
    parser = argparse.ArgumentParser(description="This runs periodically - start workflow on sites that have been imported and need to be updated.",
                                formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())
    APP['debug'] = APP['debug'] or args['debug']

    run(APP)

if __name__ == '__main__':
    main()
