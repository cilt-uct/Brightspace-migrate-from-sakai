#!/usr/bin/python3

## Workflow operation to remove archive files when completed:
## - /data/sakai/otherdata/archive-site/
## - /data/sakai/otherdata/brightspace-import/
## - sftp inbox and outbox when complete

import sys
import os
import argparse
import shutil
import glob
import paramiko
import time
import logging
from stat import S_ISREG

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.logging_config
from lib.local_auth import getAuth

def cleanup_sftp(APP, sftp_folder, site_id):

    removed = False

    SFTP = getAuth('BrightspaceFTP', ['hostname', 'username', 'password'])
    if not SFTP['valid']:
        raise Exception('SFTP Authentication required [BrightspaceFTP]')

    ssh_client = paramiko.SSHClient()
    ssh_client.load_system_host_keys()
    ssh_client.set_missing_host_key_policy(paramiko.RejectPolicy())
    logging.getLogger("paramiko").setLevel(logging.WARNING)

    try:
        ssh_client.connect(SFTP['hostname'], 22, SFTP['username'], SFTP['password'], timeout=60)
        sftp = ssh_client.open_sftp()
        sftp.get_channel().settimeout(300)

        for entry in sftp.listdir_attr(sftp_folder):
            prefix = "{}{}".format(APP['zip']['site'], site_id)
            if S_ISREG(entry.st_mode) and entry.filename.startswith(prefix) and entry.filename.endswith('.zip'):
                sftp.remove(f"{sftp_folder}/{entry.filename}")
                logging.info(f" - removed {entry.filename} from sftp {sftp_folder}")
                removed = True

        ssh_client.close()

    except paramiko.SSHException:
        logging.warning(f'sftp connection error cleaning up {site_id} in {sftp_folder}')

    return removed

def run(SITE_ID, APP, **kwargs):

    if APP['clean_up']:
        logging.info(f"Cleanup for {SITE_ID}")
    else:
        logging.info("Skipping cleanup")
        return False

    if '/' in SITE_ID:
        logging.warning(f"Unexpected site ID '{SITE_ID}' - skipping cleanup")
        return False

    try:
        # Archive folder
        src_folder = r'{}{}-archive/'.format(APP['archive_folder'], SITE_ID)
        if os.path.isdir(src_folder):
            shutil.rmtree(src_folder)
            logging.info(f" - removed {src_folder}")

        # Output folders (e.g. content, rubrics, qti)
        for output_folder in glob.glob('{}/{}-*/'.format(APP['output'], SITE_ID)):
            if os.path.isdir(output_folder):
                shutil.rmtree(output_folder)
                logging.info(f" - removed {output_folder}")

        # Zipfiles
        for zipfile in glob.glob('{}/*{}*.zip'.format(APP['output'], SITE_ID)):
            os.remove(zipfile)
            logging.info(f" - removed {zipfile}")

        # FTP logs and SFTP inbox and outbox
        ftp_log = f"{APP['log_folder']}/{SITE_ID}_ftp.log"
        if os.path.exists(ftp_log):

            # Remove logs
            os.remove(ftp_log)
            logging.info(f" - removed {ftp_log}")

            # SFTP inbox and outbox
            tries = 1
            max_tries = 15
            sleeptime = 60
            while tries <= max_tries:
                if cleanup_sftp(APP, APP['ftp']['outbox'], SITE_ID):
                    break
                logging.info(f"Sleeping {sleeptime}s for retry {tries} / {max_tries} for cleanup of {SITE_ID} in outbox")
                tries += 1
                time.sleep(sleeptime)

            if tries > max_tries:
                logging.warning(f"No files for {SITE_ID} found in outbox")

            cleanup_sftp(APP, APP['ftp']['inbox'], SITE_ID)

    except Exception:
        logging.exception(f"Exception during cleanup for {SITE_ID} (ignoring)")
        return False

    logging.info("Done")
    return True

def main():
    APP = config.config.APP
    parser = argparse.ArgumentParser(description="Workflow operation to remove zip file from sftp inbox and outbox",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('-f', '--force', help="Cleanup regardless of cleanup config setting", action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']
    if args['force']:
        APP['clean_up'] = True

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
