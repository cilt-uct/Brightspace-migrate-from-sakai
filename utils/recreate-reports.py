#!/usr/bin/python3

## Checks the DB for sites that are imported and need to be updated
## REF:

import sys
import os
import argparse
import pymysql
import time
import logging
import re

from pymysql.cursors import DictCursor
from datetime import timedelta

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.config import *
from lib.utils import *
from lib.local_auth import getAuth

from work.archive_site import *
import work.archive_site
import work.clear_archive

from work.generate_conversion_report import *
import work.generate_conversion_report

def get_records(db_config):
    try:
        connection = pymysql.connect(**db_config, cursorclass=DictCursor)
        with connection:
            with connection.cursor() as cursor:
                sql = """SELECT link_id, site_id, transfer_site_id FROM tsugi_dev.migration_site
                            where report_url is null and state != 'admin' and transfer_site_id is not null
                            order by started_at desc ;"""
                            # and site_id='ffc1fc56-e377-4e19-a61f-590ea74986d8';""" #  limit 1;
                cursor.execute(sql)
                return cursor.fetchall()

    except Exception as e:
        raise Exception('Could not retrieve migration records') from e

def run(APP):

    tmp = getAuth(APP['auth']['db'])
    if (tmp is not None):
        DB_AUTH = {'host' : tmp[0], 'database': tmp[1], 'user': tmp[2], 'password' : tmp[3]}
    else:
        raise Exception("DB Authentication required")

    logging.info("Checking for sites ...")

    start_time = time.time()
    all_sites = get_records(DB_AUTH)

    for site in all_sites:
        try:
            n = re.findall(r'(\d{8}_\d{4})$', site['transfer_site_id'])
            now_st = ('' if len(n) == 0 else n[0]).strip()
            logging.debug("{} : {} {} ({})".format(site['link_id'], site['site_id'], now_st, site['transfer_site_id']))

            if work.archive_site.archive_site_retry(site['site_id'], APP):
                work.generate_conversion_report.run(site['site_id'], APP, link_id = site['link_id'], now_st = now_st)
                work.clear_archive.run(site['site_id'], APP)

        except Exception as e:
            logging.exception(e)

    logging.info("\t{}".format(str(timedelta(seconds=(time.time() - start_time)))))

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
