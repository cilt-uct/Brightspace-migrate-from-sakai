#!/usr/bin/python3

## Checks the DB for sites that are imported and need to be updated
## REF:

import sys
import os
import subprocess
import argparse
import pymysql
import time
import logging
import requests
import json
import importlib

from requests.exceptions import HTTPError
from pathlib import Path
from stat import S_ISREG

from pymysql.cursors import DictCursor
from datetime import datetime, timedelta
from subprocess import Popen

import lib.local_auth
import run_update
import lib.db

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.config import *
from lib.utils import *
from lib.local_auth import *

# output path for the log file of this script
LOG_FILE = 'brightspace_uploading_list.log'

def get_state_count(db_config, state):
    try:
        connection = pymysql.connect(**db_config, cursorclass=DictCursor)
        with connection:
            with connection.cursor() as cursor:

                sql = """SELECT COUNT(state) as CountOfState FROM migration_site WHERE state = %s;"""
                cursor.execute(sql, (state))
                return cursor.fetchone()['CountOfState']

    except Exception as e:
        logging.error(f"Could not retrieve state {state}")
        return None

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
            logging.debug("Set to {} for ({}-{})".format(new_state, link_id, site_id))

    except Exception as e:
        raise Exception(f'Could not set_to_updating for {link_id} : {site_id}') from e

def upload(db_config, link_id, site_id, title):

    try:
        set_to_state(db_config, link_id, site_id, "uploading")

        cmd = "python3 {}/run_upload.py {} {}".format(SCRIPT_FOLDER, link_id, site_id).split()
        if APP['debug']:
            cmd.append("-d")

        # async
        p = Popen(cmd)
        logging.info("Upload : starting PID[{}] for {} : {} ({})".format(p.pid, link_id, site_id, title))

    except Exception as e:
        logging.exception(e)

def check_upload(APP):

    logging.debug("##### Checking for uploads")

    tmp = lib.local_auth.getAuth(APP['auth']['db'])
    if (tmp is not None):
        DB_AUTH = {'host' : tmp[0], 'database': tmp[1], 'user': tmp[2], 'password' : tmp[3]}
    else:
        raise Exception("DB Authentication required")

    # Max permitted import jobs
    max_jobs = APP['import']['max_jobs']
    active_imports = get_state_count(DB_AUTH, 'importing')
    active_uploads = get_state_count(DB_AUTH, 'uploading')

    # datetime object containing current date and time that the workflow was started
    now = datetime.now()
    start_time = time.time()

    # Jobs pending
    want_to_process = lib.db.get_records(db_config=DB_AUTH, state='queued', order_by_zip=True)

    if want_to_process:
        logging.info(f"{len(want_to_process)} site(s) queued, {active_uploads} site(s) uploading, {active_imports} site(s) importing out of maximum {max_jobs}")
    else:
        logging.debug("----- No sites to upload")
        return

    for site in want_to_process:

        active_imports = get_state_count(DB_AUTH, 'importing')
        active_uploads = get_state_count(DB_AUTH, 'uploading')

        if (active_imports + active_uploads) >= max_jobs:
            break

        site_id = site['site_id']
        site_title = site['title']
        try:
            logging.info(f"Upload for '{site_title}' {site_id}")

            if not site['files'] or not site['workflow']:
                logging.warning(f"Skipping {site_id} {site_title} - missing files and/or workflow")
                continue

            # run upload workflow
            upload(DB_AUTH, site['link_id'], site_id, site_title)

        except Exception as e:
            logging.exception(e)

    logging.info("##### Finished. Elapsed time {}".format(str(timedelta(seconds=(time.time() - start_time)))))

def main():
    global APP
    parser = argparse.ArgumentParser(description="This runs periodically - start workflow on sites that need to be uploaded.",
                                formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())
    APP['debug'] = APP['debug'] or args['debug']

    # create logger
    logger = logging.getLogger()
    if APP['debug']:
        logger.setLevel(logging.DEBUG)
    else:
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

    scan_interval = APP['scan_interval']['upload']
    exit_flag_file = APP['exit_flag']['upload']

    logging.info(f"Scanning for new uploads every {scan_interval} seconds until {exit_flag_file} exists")

    while not os.path.exists(exit_flag_file):
        check_upload(APP)
        time.sleep(scan_interval)

    os.remove(exit_flag_file)
    logging.info("Done")

if __name__ == '__main__':
    main()
