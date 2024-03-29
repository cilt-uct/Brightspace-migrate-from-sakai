#!/usr/bin/python3

## Checks the DB for sites that are imported and need to be updated
## REF:

import sys
import os
import argparse
import pymysql
import time
import logging
import json
import importlib
import re
import paramiko

from pathlib import Path
from stat import S_ISREG
from pymysql.cursors import DictCursor
from datetime import datetime, timedelta
from subprocess import Popen

import lib.local_auth
import lib.db

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.config import APP, SCRIPT_FOLDER
from lib.utils import send_template_email, create_jira
from lib.d2l import middleware_d2l_api, web_login

# log file of this script
LOG_FILE = 'brightspace_updating_list.log'

def set_site_property(site_id, key, value):
    try:
        mod = importlib.import_module('work.set_site_property')
        func = getattr(mod, 'run')
        new_kwargs = {'SITE_ID' : site_id, 'APP': APP}

        new_kwargs[key] = value
        func(**new_kwargs)  # this runs the steps - and writes to log file

    except Exception as e:
        logging.exception(e)
        logging.error("Workflow operation {} = {} ".format('set_site_property', e))
        return False

def set_to_updating(db_config, link_id, site_id):

    try:
        connection = pymysql.connect(**db_config, cursorclass=DictCursor)
        with connection:
            with connection.cursor() as cursor:
                # Create a new record
                sql = """UPDATE `migration_site` SET modified_at = NOW(), modified_by = 1, state = 'updating'
                         WHERE `link_id` = %s and site_id = %s;"""
                cursor.execute(sql, (link_id, site_id))

            connection.commit()
            logging.debug("Set to updating for ({}-{})".format(link_id, site_id))

    except Exception as e:
        raise Exception(f'Could not set_to_updating for {link_id} : {site_id}') from e

def update_import_id(db_config, link_id, site_id, org_unit_id, log):

    set_site_property(site_id, 'brightspace_imported_site_id', org_unit_id)

    try:
        connection = pymysql.connect(**db_config, cursorclass=DictCursor)
        with connection:
            with connection.cursor() as cursor:
                # Create a new record
                sql = """UPDATE `migration_site` SET modified_at = NOW(), modified_by = 1, imported_site_id = %s, workflow=%s
                         WHERE `link_id` = %s and site_id = %s;"""
                cursor.execute(sql, (org_unit_id, json.dumps(log), link_id, site_id))

            connection.commit()
            logging.debug("Update ({}-{}) imported_site_id {} ".format(link_id, site_id, org_unit_id))

    except Exception as e:
        raise Exception(f'Could not update import_site_id for {link_id} : {site_id}') from e

def migration_site_expired(APP, db_config, link_id, site_id, started_by, notification, log, title, url):

    try:
        connection = pymysql.connect(**db_config, cursorclass=DictCursor)
        with connection:
            with connection.cursor() as cursor:
                sql = """UPDATE `migration_site` SET modified_at = NOW(), modified_by = 1,
                        active = 0, state = 'error', failure_type = 'expired', workflow=%s
                         WHERE `link_id` = %s and site_id = %s;"""
                cursor.execute(sql, (json.dumps(log), link_id, site_id))

            connection.commit()
            logging.debug("Set error state or: ({}-{})".format(link_id, site_id))

    except Exception as e:
        raise Exception(f'Could not update record in migration_site_expired() for {link_id} : {site_id}') from e

    # Send expired email
    msg_subject = f"{APP['sakai_name']} to {APP['brightspace_name']}: Import timed out [{title}]"
    send_template_email(
        APP,
        template='error_import_timeout.html',
        to=notification,
        subj=msg_subject,
        started_by=started_by,
        title=title,
        site_id=site_id)

    # Create MIG JIRA
    failure_type = 'expired'
    log = f"Import timed out after {APP['import']['expiry']} minutes"
    create_jira(APP=APP, url=url, site_id=site_id, site_title=title, jira_state='expire', failure_type=failure_type, jira_log=log, user=started_by)

def migration_site_failed(APP, db_config, link_id, site_id, started_by, notification, log, title, url):

    try:
        connection = pymysql.connect(**db_config, cursorclass=DictCursor)
        with connection:
            with connection.cursor() as cursor:
                sql = """UPDATE `migration_site` SET modified_at = NOW(), modified_by = 1,
                            active = 0, state = 'error', failure_type = 'import-error', workflow=%s
                         WHERE `link_id` = %s and site_id = %s;"""
                cursor.execute(sql, (json.dumps(log), link_id, site_id))

            connection.commit()
            logging.debug("Set error state or: ({}-{})".format(link_id, site_id))

    except Exception as e:
        raise Exception(f'Could not update in migration_site_failed for {link_id} : {site_id}') from e

    # Send expired email
    msg_subject = f"{APP['sakai_name']} to {APP['brightspace_name']}: Import failed [{title}]"
    send_template_email(
        APP,
        template='error_import_failed.html',
        to=notification,
        subj=msg_subject,
        started_by=started_by,
        title=title,
        site_id=site_id)

    # Create MIG JIRA
    create_jira(APP=APP, url=url, site_id=site_id, site_title=title, jira_state='failed', jira_log=log, failure_type="import-error", user=started_by)

# Unused
def sftp_file_list(sftp, remotedir):

    filelist = dict()

    # Count the zip files in inbox and outbox, ignoring .tmp files
    for entry in sftp.listdir_attr(remotedir):
        if S_ISREG(entry.st_mode) and entry.filename.endswith('.zip'):
            filelist[entry.filename] = entry.st_size

    return filelist

# Unused
def check_sftp(inbox, outbox):

    ftpAuth = lib.local_auth.getAuth('BrightspaceFTP')
    if (ftpAuth is not None):
        SFTP = {'host' : ftpAuth[0], 'username': ftpAuth[1], 'password' : ftpAuth[2]}
    else:
        raise Exception('SFTP Authentication required [getBrightspaceFTP]')

    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    logging.getLogger("paramiko").setLevel(logging.WARNING)

    logging.debug(f"Checking sftp {SFTP['host']}:{inbox}:{outbox}")

    try:
        ssh_client.connect(SFTP['host'], 22, SFTP['username'], SFTP['password'])
        sftp = ssh_client.open_sftp()

        inbox_files = sftp_file_list(sftp, inbox)
        outbox_files = sftp_file_list(sftp, outbox)

        ssh_client.close()

    except paramiko.SSHException:
        raise Exception(f'sftp connection error checking for files in {inbox} and {outbox}')

    logging.info(f"{SFTP['host']} has size inbox={len(inbox_files)} outbox={len(outbox_files)}")

    return (inbox_files, outbox_files)

def check_for_brightspace_id(search_site_id):

    # We want to swallow exceptions and failures here because if we can't search successfully,
    # it's not a workflow failure, we just retry again later.

    # GET /d2l/api/lp/(version)/orgstructure/?orgUnitCode={search_site_id}

    payload = {
        'url': f"{APP['brightspace_api']['lp_url']}/orgstructure/?orgUnitCode={search_site_id}",
        'method': 'GET'
    }

    try:

        json_response = middleware_d2l_api(APP, payload_data=payload, retries=0)

        if 'status' in json_response:
            if (json_response['status'] == 'success'):
                # We expect this to be unique, so take the first result
                if len(json_response['data']['Items']) == 1:
                    return int(json_response['data']['Items'][0]['Identifier'])
                else:
                    logging.debug(f"No results for search on {search_site_id}")
            if (json_response['status'] == "ERR"):
                logging.warning(f"Unexpected response {json_response} checking for {search_site_id}")
        else:
            logging.warning(f"Unexpected response {json_response} checking for {search_site_id}")

    except Exception:
        logging.exception(f"Exception in fetch_course_info for {search_site_id}")

    # Error or not found
    return 0

def check_for_update(APP, db_config, link_id, site_id, started_by, notification, search_site_id, refsite_id, expired, files, log, title, url, import_status):

    logging.info(f": check_for_update {site_id} brightspace id {refsite_id} import status {import_status}")

    try:

        if expired:
            logging.warn(f"The import for site {site_id} has expired")

            # log error in database and create corresponding jira
            migration_site_expired(APP, db_config, link_id, site_id, started_by, notification, log, title, url)
            return False

        # if we have an refsite_id and import is complete then let's run the rest of the update workflow
        if (refsite_id > 0) and ('status' in import_status) and (import_status['status'] == "Complete"):
            set_to_updating(db_config, link_id, site_id)

            cmd = "python3 {}/run_update.py {} {}".format(SCRIPT_FOLDER, link_id, site_id).split()
            if APP['debug']:
                cmd.append("-d")

            # async
            p = Popen(cmd)
            logging.info("Import completed: starting PID[{}] for {} : {} ({})".format(p.pid, link_id, site_id, title))
            return True

        if (refsite_id > 0) and ('status' in import_status) and (import_status['status'] == "Failed"):
            migration_site_failed(APP, db_config, link_id, site_id, started_by, notification, import_status, title, url)
            return False

    except Exception as e:
        logging.exception(e)
        return False

def get_import_history(brightspace_url, org_unit, session):
    url = f'{brightspace_url}/d2l/le/conversion/import/{org_unit}/history/display?ou={org_unit}'
    r = session.get(url, timeout=30)
    return r.text

def get_first_import_status(content):
    pattern = re.compile('<d2l-status-indicator state="(.*?)" text="(.*?)"(.*?)>')
    if pattern.search(content):
        return pattern.search(content).group(2)

def get_first_import_job_log(content):
    pattern = re.compile('<a class=(.*?) href=(.*?)logs/(.*?)/Display">View Import Log(.*?)')
    if pattern.search(content):
        return pattern.search(content).group(3)

def get_import_status_collection(brightspace_url, WEB_AUTH, orgunit_ids):

    global brightspace_last_login, brightspace_session

    if (brightspace_last_login is None) or ((datetime.now() - brightspace_last_login).total_seconds() > 1800):
        login_url = f"{brightspace_url}/d2l/lp/auth/login/login.d2l"
        brightspace_session = web_login(login_url, WEB_AUTH['username'], WEB_AUTH['password'])
        brightspace_last_login = datetime.now()

    status_list = { }
    for orgunit_id in orgunit_ids:
        content = get_import_history(brightspace_url, orgunit_id, brightspace_session)
        status_list[orgunit_id] = {
                'status': get_first_import_status(content),
                'job_id': get_first_import_job_log(content)
        }

    return status_list

def check_imported(APP):

    # Number of hours for Brightspace to import a site - longer than that and we assume it failed
    expiry_minutes = APP['import']['expiry']
    brightspace_url = APP['brightspace_url']

    tmp = lib.local_auth.getAuth(APP['auth']['db'])
    if (tmp is not None):
        DB_AUTH = {'host' : tmp[0], 'database': tmp[1], 'user': tmp[2], 'password' : tmp[3]}
    else:
        raise Exception("DB Authentication required")

    webAuth = lib.local_auth.getAuth('BrightspaceWeb')
    if (webAuth is not None):
        WEB_AUTH = {'username': webAuth[0], 'password' : webAuth[1]}
    else:
        raise Exception('Web Authentication required [BrightspaceWeb]')

    start_time = time.time()

    want_to_process = lib.db.get_records(db_config=DB_AUTH, expiry_minutes=expiry_minutes, state='importing')

    if not want_to_process:
        logging.debug("----- No sites to check")
        return

    imported_sites = len(list(filter(lambda x: x['imported_site_id'] > 0, want_to_process)))

    logging.info(f"##### Started (expiry={expiry_minutes} minutes)")
    logging.info("Checking import status for {} site(s) including {} with Brightspace id(s)".format(len(want_to_process), imported_sites))

    # Check for new Brightspace IDs
    refsite_ids = []
    for site in want_to_process:

        site_id = site['site_id']
        refsite_id = site['imported_site_id']

        # Check to see if a site has been created
        if refsite_id == 0:
            refsite_id = check_for_brightspace_id(site['transfer_site_id'])
            if refsite_id > 0:
                logging.info(f"Site {site_id} has new Brightspace Id {refsite_id}")
                update_import_id(DB_AUTH, site['link_id'], site_id, refsite_id, json.loads(site['workflow']))
                site['imported_site_id'] = refsite_id

        # If we have a Brightspace site, add to the import status check list
        if refsite_id > 0:
            refsite_ids.append(refsite_id)

    # Check import status collection for sites with Brightspace ids
    import_status_set = {}
    if refsite_ids:
        import_status_set = get_import_status_collection(brightspace_url, WEB_AUTH, refsite_ids)
        logging.info(f"Import status: {import_status_set}")
    else:
        logging.debug("No sites yet with Brightspace ids")

    # Now decide what to do with each site
    for site in want_to_process:
        site_id = site['site_id']
        site_url = site['url']
        site_title = site['title']
        imported_site_id = site['imported_site_id']
        failure_type = site['failure_type']
        failure_detail = site['failure_detail']
        notification = site['notification']

        import_status = {}
        if imported_site_id in import_status_set:
            import_status = import_status_set[imported_site_id]

        try:
            logging.debug("{} : {} ({})".format(site['link_id'], site['site_id'], site['expired'], ))

            if not site['files'] or not site['workflow']:
                logging.warning(f"Skipping {site_id} {site_title} - missing files and/or workflow")
                continue

            # check if it exist in Brightspace and then run update workflow on it.
            check_for_update(APP, DB_AUTH, site['link_id'], site['site_id'],
                                    site['started_by_email'],
                                    site['notification'],
                                    site['transfer_site_id'],
                                    site['imported_site_id'],
                                    site['expired'] == 'Y',
                                    json.loads(site['files']),
                                    json.loads(site['workflow']),
                                    site['title'], site['url'],
                                    import_status)

        except Exception as e:

            # Unexpected failure (neither timeout nor import failed)
            logging.error("Unexpected failure processing site")

            logging.exception(e)

            if 'started_by_email' in site:
                started_by = site['started_by_email']
            else:
                started_by = None

            msg_subject = f"{APP['sakai_name']} to {APP['brightspace_name']}: Import workflow error [{site_title}]"
            send_template_email(
                APP,
                template='error_import.html',
                to=notification,
                subj=msg_subject,
                started_by=started_by,
                title=site_title,
                site_id=site_id)

            create_jira(APP=APP, url=site_url, site_id=site_id, site_title=site_title, jira_state='error',
                        jira_log=str(e), failure_type=failure_type, failure_detail=failure_detail, user=started_by)

    logging.info("##### Finished. Elapsed time {}".format(str(timedelta(seconds=(time.time() - start_time)))))

def main():
    global APP
    parser = argparse.ArgumentParser(description="This runs periodically - start workflow on sites that have been imported and need to be updated.",
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

    global brightspace_last_login, brightspace_session
    brightspace_last_login = None
    brightspace_session = None

    scan_interval = APP['scan_interval']['import']
    exit_flag_file = APP['exit_flag']['import']

    logging.info(f"Scanning for new imports every {scan_interval} seconds until {Path(exit_flag_file).name} exists")

    while not os.path.exists(exit_flag_file):
        check_imported(APP)
        time.sleep(scan_interval)

    os.remove(exit_flag_file)
    logging.info("Done")

if __name__ == '__main__':
    main()
