#!/usr/bin/python3

## Checks for sites that have been processed (state=queued) and runs the upload script for each

import sys
import os
import argparse
import time
import logging

from pathlib import Path
from datetime import timedelta
from subprocess import Popen

import config.config
import config.logging_config
import lib.local_auth
import lib.db

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


def upload(APP, mdb, link_id, site_id, title):

    try:
        mdb.set_to_state(link_id, site_id, "uploading")

        cmd = "python3 {}/run_upload.py {} {}".format(APP['script_folder'], link_id, site_id).split()
        if APP['debug']:
            cmd.append("-d")

        # async
        p = Popen(cmd)
        logging.info("Upload : starting PID[{}] for {} : {} ({})".format(p.pid, link_id, site_id, title))

    except Exception as e:
        logging.exception(e)

def check_upload(APP):

    logging.debug("##### Checking for uploads")

    mdb = lib.db.MigrationDb(APP)

    # Max permitted import jobs
    max_jobs = APP['import']['max_jobs']
    active_imports = mdb.get_state_count('importing')
    active_uploads = mdb.get_state_count('uploading')

    # datetime object containing current date and time that the workflow was started
    start_time = time.time()

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

            if APP['import']['hold_test_conversions'] and site['test_conversion']:
                logging.info(f"Skipping {site_id} {site_title} - test conversion")
                continue

            if not site['files'] or not site['workflow']:
                logging.warning(f"Skipping {site_id} {site_title} - missing files and/or workflow")
                continue

            logging.info(f"Upload for '{site_title}' {site_id}")

            # run upload workflow
            upload(APP, mdb, site['link_id'], site_id, site_title)

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

    while not os.path.exists(exit_flag_file):
        check_upload(APP)
        time.sleep(scan_interval)

    os.remove(exit_flag_file)
    logging.info("Done")

if __name__ == '__main__':
    main()
