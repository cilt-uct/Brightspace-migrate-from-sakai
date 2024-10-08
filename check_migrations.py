#!/usr/bin/python3

## Checks for sites to be migrated (state=starting) and starts the workflow script for each

import os
import argparse
import time
import logging

from datetime import timedelta
from subprocess import Popen, DEVNULL
from pathlib import Path

import config.config
import config.logging_config
import lib.local_auth
import lib.db

from lib.utils import process_check

def check_migrations(APP, process_list):

    logging.debug("Checking form migration records")

    start_time = time.time()

    # Database connection
    mdb = lib.db.MigrationDb(APP)

    want_to_migrate = mdb.get_records(state='starting')
    active_exports = mdb.get_state_count(state='exporting')
    active_workflows = mdb.get_state_count(state='running')

    max_jobs = APP['export']['max_jobs']
    max_workflows = APP['workflow']['max_jobs']

    if (len(want_to_migrate) + active_exports + active_workflows) > 0:
        logging.info(f"{len(want_to_migrate)} sites pending, {active_exports} / {max_jobs} sites exporting, {active_workflows} / {max_workflows} workflows running")

    if (active_exports >= max_jobs):
        logging.debug("Too many exports running - pausing")
        time.sleep(30)
        return

    if (active_workflows >= max_workflows):
        logging.debug("Too many workflows running - pausing")
        time.sleep(30)
        return

    started = 0

    for site in want_to_migrate:

        if (active_exports + started) >= max_jobs:
            break

        if (active_workflows + started) >= max_workflows:
            break

        started += 1
        site_id = site['site_id']
        link_id = site['link_id']

        try:

            if (not mdb.another_running(link_id, site_id)):
                mdb.set_running(link_id, site_id)

                logging.info(f"migration started for {site_id} from {link_id}")

                cmd = "python3 {}/run_workflow.py {} {}".format(APP['script_folder'],site['link_id'],site['site_id']).split()
                # if APP['debug']:
                #     cmd.append("-d")

                p = Popen(cmd, stderr=DEVNULL, stdout=DEVNULL)
                process_list.append(p)
                logging.info("\tRunning PID[{}] {} : {}".format(p.pid, site['link_id'],site['site_id']))

                time.sleep(5)
            else:
                logging.info(f"Migration for {site_id} from {link_id} queued, but another task is running for this site")

        except Exception:
            logging.exception(f"Error starting workflow for {site_id} from {link_id}")

    logging.debug("\t{}".format(str(timedelta(seconds=(time.time() - start_time)))))

def main():
    APP = config.config.APP
    parser = argparse.ArgumentParser(description="This runs periodically - start workflow on sites that want to migrate.",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())
    APP['debug'] = APP['debug'] or args['debug']

    if APP['debug']:
        config.logging_config.logger.setLevel(logging.DEBUG)

    scan_interval = APP['scan_interval']['workflow']
    exit_flag_file = APP['exit_flag']['workflow']

    logging.info(f"Scanning for new migrations every {scan_interval} seconds until {Path(exit_flag_file).name} exists")

    process_list = []

    while not os.path.exists(exit_flag_file):
        check_migrations(APP, process_list)
        time.sleep(scan_interval)
        process_check(process_list)

    os.remove(exit_flag_file)
    logging.info("Done")

if __name__ == '__main__':
    main()
