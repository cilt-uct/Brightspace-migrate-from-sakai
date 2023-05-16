#!/usr/bin/python3

## Checks the DB for sites to be migrated
## REF:

import sys
import os
import argparse
import pymysql
import time
import logging

from pymysql.cursors import DictCursor
from datetime import datetime, timedelta
from subprocess import Popen
from pathlib import Path

import lib.local_auth
import lib.db

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.config import *
from lib.utils import *
from lib.local_auth import *
from lib.jira_rest import MyJira

LOG_FILE = 'brightspace_migration_list.log'

def set_running(db_config, link_id, site_id):
    try:
        connection = pymysql.connect(**db_config, cursorclass=DictCursor)
        with connection:
            with connection.cursor() as cursor:
                # Create a new record
                sql = """UPDATE `migration_site` SET modified_at = NOW(), modified_by = 1, active = %s, state = %s
                         WHERE `link_id` = %s and site_id = %s;"""
                cursor.execute(sql, ('1', 'exporting', link_id, site_id))

            connection.commit()

    except Exception as e:
        raise Exception(f'Could not update migration record {link_id} : {site_id}') from e

def another_running(db_config, link_id, site_id):
    try:
        connection = pymysql.connect(**db_config, cursorclass=DictCursor)
        with connection:
            with connection.cursor() as cursor:
                sql = """SELECT link_id FROM migration_site `A`
                            where  `A`.link_id <> %s and `A`.site_id = %s and `active` = 1
                            and `A`.state in ('exporting','running')"""
                cursor.execute(sql, (link_id, site_id))
                cursor.fetchall()
                return cursor.rowcount

    except Exception as e:
        raise Exception('Could not check on migration records') from e

    return 0

def check_migrations(APP):

    logging.debug("Checking form migration records")

    site_id = ''
    site_url = ''
    site_title = "check_migrations"
    failure_type = ''
    failure_detail = ''
    started_by = ''

    # datetime object containing current date and time that the workflow was started
    start_time = time.time()

    try:
        tmp = lib.local_auth.getAuth(APP['auth']['db'])
        if (tmp is not None):
            DB_AUTH = {'host' : tmp[0], 'database': tmp[1], 'user': tmp[2], 'password' : tmp[3]}
        else:
            raise Exception('Authentication required ({}})'.format(APP['auth']['db']))

        # datetime object containing current date and time that the workflow was started
        start_time = time.time()

        want_to_migrate = lib.db.get_records(db_config=DB_AUTH, state='starting')
        for site in want_to_migrate:
            site_id = site['site_id']
            site_url = site['url']
            site_title = site['title']
            failure_type = site['failure_type']
            failure_detail = site['failure_detail']
            started_by = site['started_by_email']
            try:
                logging.info(f"migration started for {site_id}")

                if (not another_running(DB_AUTH, site['link_id'], site['site_id'])):
                    set_running(DB_AUTH, site['link_id'], site['site_id'])

                    cmd = "python3 {}/run_workflow.py {} {}".format(SCRIPT_FOLDER, site['link_id'],site['site_id']).split()
                    # if APP['debug']:
                    #     cmd.append("-d")

                    p = Popen(cmd)
                    logging.info("\tRunning PID[{}] {} : {}".format(p.pid, site['link_id'],site['site_id']))

                    time.sleep(5)
                else:
                    logging.info("\tHas another task running for {}".format(site['site_id']))
            except Exception as e:
                send_template_email(
                    APP,
                    template='error_workflow.html',
                    to=None,
                    started_by=started_by,
                    subj='Failed conversion',
                    title=site_title,
                    site_id=site_id)
                raise e

    except Exception as e:
        logging.error(e)
        create_jira(APP=APP, url=site_url, site_id=site_id, site_title=site_title, jira_log=[str(e)],
                    jira_state='error', failure_type=failure_type, failure_detail=failure_detail, user=started_by)

    logging.debug("\t{}".format(str(timedelta(seconds=(time.time() - start_time)))))

def main():
    global APP
    parser = argparse.ArgumentParser(description="This runs periodically - start workflow on sites that want to migrate.",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())
    APP['debug'] = APP['debug'] or args['debug']

    # create logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(process)d %(filename)s(%(lineno)d) %(message)s')

    # create file handler
    fh = logging.FileHandler(Path(APP['log_folder']) / LOG_FILE)
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    if APP['debug']:
        # create stream handler (logging in the console)
        sh = logging.StreamHandler()
        sh.setLevel(logging.DEBUG)
        sh.setFormatter(formatter)
        logger.addHandler(sh)

    scan_interval = APP['scan_interval']['workflow']
    exit_flag_file = APP['exit_flag']['workflow']

    logging.info(f"Scanning for new migrations every {scan_interval} seconds until {exit_flag_file} exists")

    while not os.path.exists(exit_flag_file):
        check_migrations(APP)
        time.sleep(scan_interval)

    os.remove(exit_flag_file)
    logging.info("Done")

if __name__ == '__main__':
    main()
