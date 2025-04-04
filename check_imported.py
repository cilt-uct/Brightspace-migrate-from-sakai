#!/usr/bin/python3

## Checks the import status on Brightspace for uploaded sites (state=importing)
## Executes the update workflow for completed sites, or set error state if the import
## has failed or timed out.

import os
import argparse
import pymysql
import time
import logging
import json

from pathlib import Path
from stat import S_ISREG
from pymysql.cursors import DictCursor
from datetime import datetime, timedelta
from subprocess import Popen, DEVNULL

import config.config
import config.logging_config
import lib.local_auth
import lib.db
import lib.sakai

from lib.utils import send_template_email, process_check
from lib.jira_rest import create_jira
from lib.d2l import middleware_d2l_api, d2l_api_version, web_login, get_import_history, get_first_import_status, get_first_import_job_log


def update_import_id(APP, db_config, link_id, site_id, org_unit_id, log):

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

def check_for_brightspace_id(APP, search_site_id):

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

def check_for_update(APP, mdb, link_id, site_id, started_by, notification, search_site_id, refsite_id, expired, files, log, title, url, import_status):

    logging.info(f": check_for_update {site_id} brightspace id {refsite_id} import status {import_status}")

    try:

        if expired:
            logging.warn(f"The import for site {site_id} has expired")

            # log error in database and create corresponding jira
            migration_site_expired(APP, mdb.db_config, link_id, site_id, started_by, notification, log, title, url)
            return None

        # if we have an refsite_id and import is complete then let's run the rest of the update workflow
        if (refsite_id > 0) and ('status' in import_status) and (import_status['status'] == "Complete"):
            mdb.set_to_state(link_id, site_id, "updating")

            cmd = "python3 {}/run_update.py {} {}".format(APP['script_folder'], link_id, site_id).split()
            if APP['debug']:
                cmd.append("-d")

            # async
            p = Popen(cmd, stdout=DEVNULL, stderr=DEVNULL)
            logging.info("Import completed: starting PID[{}] for {} : {} ({})".format(p.pid, link_id, site_id, title))
            return p

        if (refsite_id > 0) and ('status' in import_status) and (import_status['status'] == "Failed"):
            migration_site_failed(APP, mdb.db_config, link_id, site_id, started_by, notification, import_status, title, url)
            return None

    except Exception as e:
        logging.exception(e)
        return None

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

def check_imported(APP, sakai_ws, process_list):

    # Number of hours for Brightspace to import a site - longer than that and we assume it failed
    expiry_minutes = APP['import']['expiry']
    brightspace_url = APP['brightspace_url']

    # Migration database
    mdb = lib.db.MigrationDb(APP)

    WEB_AUTH = lib.local_auth.getAuth('BrightspaceWeb', ['username', 'password'])
    if not WEB_AUTH['valid']:
        raise Exception('Web Authentication required [BrightspaceWeb]')

    start_time = time.time()

    busy_updating = mdb.get_state_count('updating')
    if busy_updating:
        logging.info(f"{busy_updating} site(s) updating")

    want_to_process = mdb.get_records(expiry_minutes=expiry_minutes, state='importing')

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
            refsite_id = check_for_brightspace_id(APP, site['transfer_site_id'])
            if refsite_id > 0:
                logging.info(f"Site {site_id} has new Brightspace Id {refsite_id}")
                update_import_id(APP, mdb.db_config, site['link_id'], site_id, refsite_id, json.loads(site['workflow']))
                sakai_ws.set_site_property(site_id, 'brightspace_imported_site_id', refsite_id)
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
            p = check_for_update(APP, mdb, site['link_id'], site['site_id'],
                                    site['started_by_email'],
                                    site['notification'],
                                    site['transfer_site_id'],
                                    site['imported_site_id'],
                                    site['expired'] == 'Y',
                                    json.loads(site['files']),
                                    json.loads(site['workflow']),
                                    site['title'], site['url'],
                                    import_status)

            if p is not None:
                process_list.append(p)

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
    APP = config.config.APP
    parser = argparse.ArgumentParser(description="This runs periodically - start workflow on sites that have been imported and need to be updated.",
                                formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())
    APP['debug'] = APP['debug'] or args['debug']

    if APP['debug']:
        config.logging_config.logger.setLevel(logging.DEBUG)

    global brightspace_last_login, brightspace_session
    brightspace_last_login = None
    brightspace_session = None

    scan_interval = APP['scan_interval']['import']
    exit_flag_file = APP['exit_flag']['import']

    # Sakai webservices
    sakai_ws = lib.sakai.Sakai(APP)
    sakai_version = sakai_ws.config("version.sakai")
    logging.info(f"Sakai at {sakai_ws.url()} version is version {sakai_version}")

    # Brightspace webservices
    base_url = APP['brightspace_api']['base_url']
    le_version = d2l_api_version(APP, "le")
    lp_version = d2l_api_version(APP, "lp")
    logging.info(f"Brightspace at {base_url} has API versions le:{le_version} lp:{lp_version}")

    logging.info(f"Scanning for new imports every {scan_interval} seconds until {Path(exit_flag_file).name} exists")

    process_list = []

    while not os.path.exists(exit_flag_file):
        check_imported(APP, sakai_ws, process_list)
        time.sleep(scan_interval)
        process_check(process_list)

    os.remove(exit_flag_file)
    logging.info("Done")

if __name__ == '__main__':
    main()
