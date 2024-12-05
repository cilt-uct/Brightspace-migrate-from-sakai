#!/usr/bin/python3

## Checks for sites that have been processed (state=queued) and runs the upload script for each

import sys
import os
import argparse
import time
import logging
import pymysql

from pathlib import Path
from datetime import datetime, timedelta
from subprocess import Popen, DEVNULL
from pymysql.cursors import DictCursor

import config.config
import config.logging_config
import lib.local_auth
import lib.db

from lib.utils import send_template_email, process_check
from lib.jira_rest import create_jira

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


def upload_site_expired(APP, db_config, link_id, site_id, started_by, notification, title, url):

    try:
        connection = pymysql.connect(**db_config, cursorclass=DictCursor)
        with connection:
            with connection.cursor() as cursor:
                sql = """UPDATE `migration_site` SET modified_at = NOW(), modified_by = 1,
                        active = 0, state = 'error', failure_type = 'expired'
                         WHERE `link_id` = %s and site_id = %s;"""
                cursor.execute(sql, (link_id, site_id))

            connection.commit()
            logging.debug("Set error state or: ({}-{})".format(link_id, site_id))

    except Exception as e:
        raise Exception(f'Could not update record in migration_site_expired() for {link_id} : {site_id}') from e

    # Send expired email
    msg_subject = f"{APP['sakai_name']} to {APP['brightspace_name']}: Upload timed out [{title}]"
    send_template_email(
        APP,
        template='error_import_timeout.html',
        to=notification,
        subj=msg_subject,
        started_by=started_by,
        title=title,
        site_id=site_id)

    # Create MIG JIRA
    failure_type = 'upload-timeout'
    log = f"Upload timed out after {APP['ftp']['expiry']} minutes"
    create_jira(APP=APP, url=url, site_id=site_id, site_title=title, jira_state='expire', failure_type=failure_type, jira_log=log, user=started_by)

def upload(APP, mdb, link_id, site_id, title):

    try:
        mdb.set_to_state(link_id, site_id, "uploading")

        cmd = "python3 {}/run_upload.py {} {}".format(APP['script_folder'], link_id, site_id).split()
        if APP['debug']:
            cmd.append("-d")

        # async
        p = Popen(cmd, stdout=DEVNULL, stderr=DEVNULL)
        logging.info("Upload : starting PID[{}] for {} : {} ({})".format(p.pid, link_id, site_id, title))

        return p

    except Exception as e:
        logging.exception(e)

def upload_expired(upload_started, expiry_minutes):
    current_time = datetime.now()
    expiration_time = upload_started + timedelta(minutes=expiry_minutes)
    return current_time > expiration_time

def check_upload(APP, process_list):

    logging.debug("##### Checking for uploads")

    mdb = lib.db.MigrationDb(APP)

    # Max permitted import jobs
    max_jobs = APP['import']['max_jobs']
    active_imports = mdb.get_state_count('importing')
    active_uploads = mdb.get_state_count('uploading')

    # datetime object containing current date and time that the workflow was started
    start_time = time.time()

    # Check expiry of uploading jobs
    if active_uploads:

        # Upload expiry time in minutes since modified_at
        upload_expiry = APP['ftp']['expiry']

        sites_uploading = mdb.get_records(state='uploading')
        for site in sites_uploading:
            site_id = site['site_id']
            site_title = site['title']
            upload_started = site['modified_at']
            if 'started_by_email' in site:
                started_by = site['started_by_email']
            else:
                started_by = None

            if upload_expired(upload_started, upload_expiry):
                logging.warning(f"Upload expired for site {site_id} title '{site_title}' (started more than {upload_expiry} minutes ago)")
                upload_site_expired(APP, mdb.db_config, site['link_id'], site_id, started_by, site['notification'], site_title, site['url'])
            else:
                logging.debug(f"Site {site_id} title '{site_title}' is uploading since {upload_started}")

    # Jobs pending
    want_to_process = mdb.get_records(state='queued', order_by_zip=True)

    if (active_uploads + len(want_to_process)) > 0:
        logging.info(f"{len(want_to_process)} site(s) queued, {active_uploads} site(s) uploading, {active_imports} site(s) importing out of maximum {max_jobs}")

    if len(want_to_process) == 0:
        logging.debug("----- No sites to upload")
        return

    for site in want_to_process:

        active_imports = mdb.get_state_count('importing')
        active_uploads = mdb.get_state_count('uploading')

        if (active_imports + active_uploads) >= max_jobs:
            break

        site_id = site['site_id']
        site_title = site['title']
        try:

            if not site['files'] or not site['workflow']:
                logging.warning(f"Skipping {site_id} {site_title} - missing files and/or workflow")
                continue

            logging.info(f"Upload for '{site_title}' {site_id}")

            # run upload workflow
            p = upload(APP, mdb, site['link_id'], site_id, site_title)
            process_list.append(p)

        except Exception as e:
            logging.exception(e)

    logging.info("##### Finished. Elapsed time {}".format(str(timedelta(seconds=(time.time() - start_time)))))

def main():
    APP = config.config.APP

    parser = argparse.ArgumentParser(description="This runs periodically - start workflow on sites that need to be uploaded.",
                                formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())
    APP['debug'] = APP['debug'] or args['debug']

    if APP['debug']:
        config.logging_config.logger.setLevel(logging.DEBUG)

    scan_interval = APP['scan_interval']['upload']
    exit_flag_file = APP['exit_flag']['upload']

    logging.info(f"Scanning for new uploads every {scan_interval} seconds until {Path(exit_flag_file).name} exists")

    process_list = []

    while not os.path.exists(exit_flag_file):
        check_upload(APP, process_list)
        time.sleep(scan_interval)
        process_check(process_list)

    os.remove(exit_flag_file)
    logging.info("Done")

if __name__ == '__main__':
    main()
