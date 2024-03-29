#!/usr/bin/python3

## Execute upload.yaml workflow for uploading to sftp server

import sys
import os
import re
import glob
import json
import argparse
import pymysql
import time
import importlib


from pymysql.cursors import DictCursor
from datetime import datetime

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *
from lib.local_auth import *
import lib.local_auth
import lib.utils
import lib.db
from work.archive_site import *
from lib.jira_rest import MyJira

WORKFLOW_FILE = f'{SCRIPT_FOLDER}/config/upload.yaml'

FILE_REGEX = re.compile(".*(file-.*):\s(.*)")


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

def update_record(db_config, link_id, site_id, state, log):
    try:
        connection = pymysql.connect(**db_config, cursorclass=DictCursor)
        with connection:
            with connection.cursor() as cursor:
                # Create a new record
                sql = """UPDATE `migration_site` SET modified_at = NOW(), modified_by = 1, active = %s, state = %s, workflow=%s
                         WHERE `link_id` = %s and site_id = %s;"""
                cursor.execute(sql, ('1', state, log, link_id, site_id))

            connection.commit()

    except Exception:
        logging.error(f"Could not update migration record {link_id} : {site_id}")
        return None

def update_record_files(db_config, link_id, site_id, files):

    str_files = json.dumps(files)
    try:
        connection = pymysql.connect(**db_config, cursorclass=DictCursor)
        with connection:
            with connection.cursor() as cursor:
                # Create a new record
                sql = """UPDATE `migration_site` SET modified_at = NOW(), modified_by = 1, files = %s
                         WHERE `link_id` = %s and site_id = %s;"""
                cursor.execute(sql, (str_files, link_id, site_id))

            connection.commit()
            logging.debug("Set files: ({}-{})".format(link_id, site_id))

    except Exception:
        logging.error(f"Could not update migration record {link_id} : {site_id}")
        return None

def check_log_file_for_errors(filename):
    _file = open(filename, "r")
    lines = _file.readlines()
    _file.close()

    # check if log contains a line with ERROR in it ...
    return len(list(filter(lambda s: re.match(r'.*(\[ERROR\]).*',s), lines))) > 0

def setup_log_file(filename, SITE_ID, logs):

    # remove previous log files
    for old_log_files in glob.glob('{}/tmp/{}_workflow_*.log'.format(parent, SITE_ID)):
        os.remove(old_log_files)

    with open(filename, "w") as f:
        for l in json.loads(logs):
            f.write(f'{l}\n')
        f.close()

    # create a log file so that we can track the progress of the workflow
    fh = logging.FileHandler(filename)
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

def create_jira(url, site_id, site_title, jira_state, now, jira_log):
    jira_date_str = now.strftime("%a, %-d %b %-y %H:%M")
    jira_log = json.loads(jira_log)
    sakai_url = APP['sakai_url']

    if APP['jira']['last'] > 0:
        N = APP['jira']['last']
        jira_log = jira_log[-N:]

    with MyJira() as j:
        fields = {
            'project': {'key': APP['jira']['key']},
            'summary': "{} {} {}".format(APP['jira']['prefix'], site_title, jira_date_str),
            'description': "+SITE:+ {}\n+LINK:+ {}/{} \n\n+LOG:+\n{{noformat}}{}{{noformat}}".format(sakai_url, site_id, url,'\n'.join(jira_log)),
            'issuetype': {'name': 'Task'},
            'assignee': { 'name': APP['jira']['assignee'] },
            'customfield_10001': str(site_id)
        }

        if j.createIssue(fields) is not None:
            return True

    return False

def transition_jira(site_id):
    with MyJira() as j:
        fields = {
            'project': {'key': APP['jira']['key']},
            'site_id': str(site_id),
            'comment': 'Upload workflow complete'
        }

        j.setToInProgressIssue(fields)

def run_workflow_step(step, site_id, log_file, db_config, **kwargs):

    if step['action'] == "mail":
        if 'template' in step:

            # print("sending email with template: '{}'".format(step['template']))

            return send_template_email(
                APP,
                template=step['template'] + ".html",
                to=kwargs['to'],
                started_by=kwargs['started_by'],
                subj=step['subject'],
                title=kwargs['title'],
                site_id=site_id,
                import_id=kwargs['import_id']
            )

    elif step['action'] == "get_files":
        # print("getting files from log file and adding them to DB")

        _file = open(log_file, "r")
        lines = _file.readlines()
        _file.close()

        # check if log contains files ...
        rough_list = list(filter(lambda s: FILE_REGEX.match(s), lines))

        output_files = dict()
        for l in rough_list:
            m = re.findall(r'(file-.*):\s(.*)', l)
            output_files[ m[0][0] ] = m[0][1]

        update_record_files(db_config, kwargs['link_id'], site_id, output_files)

        return True
    else:

        try:
            mod = importlib.import_module('work.{}'.format(step['action']))
            func = getattr(mod, 'run')
            new_kwargs = {'SITE_ID' : site_id, 'APP': APP}

            if 'use_date' in step:
                new_kwargs['now_st'] = kwargs['now_st']

            if 'use_new_id' in step:
                new_kwargs['new_id'] = kwargs['new_id']

            if 'use_link_id' in step:
                new_kwargs['link_id'] = kwargs['link_id']

            if 'use_file' in step:
                new_kwargs['zip_file'] = kwargs['zip_file']

            func(**new_kwargs)  # this runs the steps - and writes to log file

            # after execution of workflow step check log to see if it contains an error
            return check_log_file_for_errors(log_file) == False

        except Exception as e:
            logging.exception(e)
            return False

def start_workflow(link_id, site_id, APP):

    tmp = lib.local_auth.getAuth(APP['auth']['db'])
    if (tmp is not None):
        DB_AUTH = {'host' : tmp[0], 'database': tmp[1], 'user': tmp[2], 'password' : tmp[3]}
    else:
        logging.error("Authentication required")
        return 0

    site_title = site_id
    site_url   = site_id

    # datetime object containing current date and time that the workflow was started
    now = datetime.now()
    now_st = now.strftime("%Y-%m-%d_%H%M%S")

    start_time = time.time()

    log_file = '{}/tmp/{}_workflow_{}.log'.format(parent, site_id, now_st)
    setup_log_file(log_file, site_id, '[]')

    record = None

    logging.info(f"Upload workflow starting for {site_id}")

    record = lib.db.get_record(db_config=DB_AUTH, link_id=link_id, site_id=site_id)
    if record['state'] != "uploading":
        raise Exception(f"Unexpected state {record['state']} for site {record['site_id']}")

    if (record is None):
        raise Exception(f'Could not find record to start workflow for {link_id} : {site_id}')

    try:
        files = json.loads(record['files'])

        if (record['test_conversion'] == 1):
            APP['site']['prefix'] = APP['site']['test_prefix']

        site_url = record['url']
        log_file = '{}/tmp/{}_workflow_{}.log'.format(parent, site_id, now_st)
        setup_log_file(log_file, site_id, record['workflow'])

        new_id = '{}_{}'.format(site_id, now.strftime("%Y%m%d_%H%M"))

        workflow_steps = lib.utils.read_yaml(WORKFLOW_FILE)

        if workflow_steps['STEPS'] is not None:
            for step in workflow_steps['STEPS']:
                logging.info("Executing workflow step: {}".format(step['action']))

                new_state = None
                if 'state' in step:
                    new_state = step['state']
                    logging.info(f"New state: {new_state}")

                if run_workflow_step(step=step, site_id=site_id, log_file=log_file, db_config=DB_AUTH,
                                         to=record['notification'], started_by=record['started_by_email'],
                                         now_st=now_st, new_id=new_id, import_id=record['imported_site_id'],
                                         link_id=link_id, title=site_title, zip_file=files['file-fixed-zip']):
                    logging.info("Completed workflow step: {}".format(step['action']))
                else:
                    # something went wrong while processing this step
                    logging.error("Failed workflow step: {}".format(step['action']))
                    raise Exception("Workflow failed")

                if new_state:
                    set_to_state(DB_AUTH, link_id, site_id, new_state)

            # Completed
            transition_jira(site_id=site_id)

        else:
            logging.warning("There are no workflow steps in this workflow.")

    except Exception:
        # Failed
        logging.error("Upload workflow did not complete")

        # Reset to queued state
        update_record(DB_AUTH, link_id, site_id, "queued", get_log(log_file))


def main():
    global APP
    parser = argparse.ArgumentParser(description="This script runs the upload workflow for a site",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("LINK_ID", help="The Link ID to run the update workflow for")
    parser.add_argument("SITE_ID", help="The Site ID to run the update workflow for")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())
    APP['debug'] = APP['debug'] or args['debug']

    start_workflow(args['LINK_ID'], args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
