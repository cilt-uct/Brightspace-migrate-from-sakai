#!/usr/bin/python3

## This script runs the migration workflow for a site

import os
import re
import glob
import json
import argparse
import pymysql
import time
import importlib
import logging

from pymysql.cursors import DictCursor
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

import config.config
import lib.local_auth
import lib.utils
import lib.db
import lib.sakai

from config.logging_config import formatter, logger
from lib.utils import create_jira, send_email, send_template_email, get_log, get_size, create_folders
from lib.jira_rest import MyJira, close_jira


FILE_REGEX = re.compile(".*(file-.*):\s(.*)")

def update_record(db_config, link_id, site_id, state, log):

    logging.info(f"Updating record: {link_id} {site_id} {state}")

    try:
        connection = pymysql.connect(**db_config, cursorclass=DictCursor)
        with connection:
            with connection.cursor() as cursor:
                # Create a new record
                sql = """UPDATE `migration_site` SET modified_at = NOW(), modified_by = 1, active = %s, state = %s, workflow=%s
                         WHERE `link_id` = %s and site_id = %s;"""
                cursor.execute(sql, ('1', state, log, link_id, site_id))

            connection.commit()

    except Exception as e:
        logging.exception(e)
        logging.error(f"Could not update migration record {link_id} : {site_id}")
        return None

def update_record_title(db_config, link_id, site_id, title):
    try:
        connection = pymysql.connect(**db_config, cursorclass=DictCursor)
        with connection:
            with connection.cursor() as cursor:
                # Create a new record
                sql = """UPDATE `migration_site` SET modified_at = NOW(), modified_by = 1, title = %s
                         WHERE `link_id` = %s and site_id = %s;"""
                cursor.execute(sql, (title, link_id, site_id))

            connection.commit()
            logging.debug("Set title: {} ({}-{})".format(title, link_id, site_id))

    except Exception as e:
        logging.exception(e)
        logging.error(f"Could not update migration record {link_id} : {site_id}")
        return None

def update_record_ref_site_id(db_config, link_id, site_id, new_id):
    try:
        connection = pymysql.connect(**db_config, cursorclass=DictCursor)
        with connection:
            with connection.cursor() as cursor:
                # Create a new record
                sql = """UPDATE `migration_site` SET modified_at = NOW(), modified_by = 1, transfer_site_id = %s, imported_site_id = 0
                         WHERE `link_id` = %s and site_id = %s;"""
                cursor.execute(sql, (new_id, link_id, site_id))

            connection.commit()
            logging.debug("Set new_id: {} ({}-{})".format(new_id, link_id, site_id))

    except Exception as e:
        logging.exception(e)
        logging.error(f"Could not update migration record {link_id} : {site_id}")
        return None

def update_record_files(db_config, link_id, site_id, files, zip_file_size):

    str_files = json.dumps(files)
    try:
        connection = pymysql.connect(**db_config, cursorclass=DictCursor)
        with connection:
            with connection.cursor() as cursor:
                # Create a new record
                sql = """UPDATE `migration_site` SET modified_at = NOW(), modified_by = 1, files = %s, zip_size = %s
                         WHERE `link_id` = %s and site_id = %s;"""
                cursor.execute(sql, (str_files, zip_file_size, link_id, site_id))

            connection.commit()
            logging.debug("Set files: ({}-{})".format(link_id, site_id))

    except Exception as e:
        logging.exception(e)
        logging.error(f"Could not update migration record {link_id} : {site_id}")
        return None

def check_log_file_for_errors(filename):
    _file = open(filename, "r")
    lines = _file.readlines()
    _file.close()

    # check if log contains a line with ERROR in it ...
    return len(list(filter(lambda s: re.match(r'.*(\[ERROR\]).*',s), lines))) > 0

def setup_log_file(APP, filename, SITE_ID, logs):

    # remove previous log files
    for old_log_files in glob.glob('{}/{}_workflow_*.log'.format(APP['log_folder'], SITE_ID)):
        os.remove(old_log_files)

    with open(filename, "w") as f:
        for log_entry in json.loads(logs):
            f.write(f'{log_entry}\n')
        f.close()

    # create a log file so that we can track the progress of the workflow
    fh = logging.FileHandler(filename)
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

# retrieve title of site from Archive site.xml
def get_title(site_xml):
    with open(site_xml, 'r', encoding='utf8') as f:
        contents = f.read()

    tree = BeautifulSoup(contents, 'xml')
    site = tree.select_one("site[title]")

    if site:
        return site.attrs['title']
    else:
        logging.warn(f"Unable to get site title from {site_xml}")

    return None

def transition_jira(APP, site_id):
    with MyJira() as j:
        fields = {
            'project': {'key': APP['jira']['key']},
            'site_id': str(site_id),
            'comment': 'Export workflow complete'
        }

        j.setToInProgressIssue(fields)

def run_workflow_step(APP, step, site_id, log_file, db_config, **kwargs):

    ## mail
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
                import_id=kwargs['import_id'],
                report_url=kwargs['report_url']
            )

        else:
            logging.warning("Workflow operation 'mail' missing template perameter")
            return False

    ## get_files
    if step['action'] == "get_files":
        # print("getting files from log file and adding them to DB")

        _file = open(log_file, "r")
        lines = _file.readlines()
        _file.close()

        # check if log contains files ...
        rough_list = list(filter(lambda s: FILE_REGEX.match(s), lines))

        output_files = dict()
        for file_entry in rough_list:
            m = re.findall(r'(file-.*):\s(.*)', file_entry)
            output_files[ m[0][0] ] = m[0][1]

        if 'file-fixed-zip' in output_files:
            filename = output_files['file-fixed-zip']
            zip_size = get_size(filename)
        else:
            zip_size = None

        update_record_files(db_config, kwargs['link_id'], site_id, output_files, zip_size)

        return True

    ## all other operations defined in work/ modules

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

        func(**new_kwargs)  # this runs the steps - and writes to log file

        # after execution of workflow step check log to see if it contains an error
        return not check_log_file_for_errors(log_file)

    except Exception as e:
        logging.exception(e)
        logging.error("Workflow operation {} = {} ".format(step['action'], e))
        return False

# States
## enum('init','starting','exporting','running','importing','updating','completed','error')

def start_workflow(workflow_file, link_id, site_id, APP):

    mdb = lib.db.MigrationDb(APP)

    site_title = site_id
    site_url   = site_id

    failure_type = ''
    failure_detail = ''

    # datetime object containing current date and time that the workflow was started
    now = datetime.now()
    now_st = now.strftime("%Y-%m-%d_%H%M%S")

    start_time = time.time()

    state = 'error'
    log_file = '{}/{}_workflow_{}.log'.format(APP['log_folder'], site_id, now_st)
    setup_log_file(APP, log_file, site_id, '[]')

    record = None

    # Sakai webservices
    sakai_ws = lib.sakai.Sakai(APP)

    try:
        record = mdb.get_record(link_id=link_id, site_id=site_id)

        if (record is None):
            raise Exception(f'Could not find record to start workflow for {link_id} : {site_id}')

        if record['state'] != "exporting":
            raise Exception(f"Unexpected state {record['state']} for site {record['site_id']}")

        test_conversion = False

        if (record['test_conversion'] == 1):
            APP['site']['prefix'] = APP['site']['test_prefix']
            logging.info(f"{site_id} is a test conversion")
            test_conversion = True

        site_url = record['url']
        failure_type = record['failure_type']
        failure_detail = record['failure_detail']

        log_file = '{}/{}_workflow_{}.log'.format(APP['log_folder'], site_id, now_st)
        setup_log_file(APP, log_file, site_id, record['workflow'])

        new_id = '{}_{}'.format(site_id, now.strftime("%Y%m%d_%H%M"))
        update_record_ref_site_id(mdb.db_config, link_id, site_id, new_id)

        sakai_ws.set_site_property(site_id, 'brightspace_conversion_date', now.strftime("%Y-%m-%d %H:%M:%S"))

        # Get the site title
        site_title = sakai_ws.get_site_title(site_id)
        if site_title:
            update_record_title(mdb.db_config, link_id, site_id, site_title)

        logging.info(f"Starting workflow for {site_id} '{site_title}'")

        # run the archiving of the site
        update_record(mdb.db_config, link_id, site_id, 'exporting', get_log(log_file))
        state = 'exporting'

        if sakai_ws.archive_site_retry(site_id):

            # Create some output files which workflow steps may need
            output_folder = "{}/{}-content".format(APP['output'], site_id)
            create_folders(output_folder)

            workflow_steps = lib.utils.read_yaml(workflow_file)

            state = 'running'
            update_record(mdb.db_config, link_id, site_id, state, get_log(log_file))

            if workflow_steps['STEPS'] is not None:
                for step in workflow_steps['STEPS']:

                    condition = step['condition'] if 'condition' in step else None

                    # Skip workflow steps if condition does not match
                    if condition and condition == "test_conversion" and not test_conversion:
                        logging.info(f"Skipping workflow step: {step['action']} (only for test conversions)")
                        continue

                    if condition and condition == "full_conversion" and test_conversion:
                        logging.info(f"Skipping workflow step: {step['action']} (only for full conversions)")
                        continue

                    logging.info("Executing workflow step: {}".format(step['action']))

                    if 'state' in step:
                        state = step['state']

                    # Read db record for updates from workflow steps
                    record = mdb.get_record(link_id=link_id, site_id=site_id)

                    if run_workflow_step(
                            APP,
                            step=step,
                            site_id=site_id,
                            log_file=log_file,
                            db_config=mdb.db_config,
                            to=record['notification'],
                            started_by=record['started_by_email'],
                            now_st=now_st,
                            new_id=new_id,
                            import_id=record['imported_site_id'],
                            report_url=record['report_url'],
                            link_id=link_id,
                            title=site_title):

                        logging.info("Completed workflow step: {}".format(step['action']))
                    else:
                        # something went wrong while processing this step
                        raise Exception("On step: {}".format(step['action']))

                transition_jira(APP, site_id=site_id)
            else:
                logging.warning("There are no workflows steps in this workflow.")
        else:
            raise Exception(f'Archive failed for {link_id} : {site_id}')

        logging.info("\t{}".format(str(timedelta(seconds=(time.time() - start_time)))))
        update_record(mdb.db_config, link_id, site_id, state, get_log(log_file))

        if test_conversion:
            close_jira(APP, site_id=site_id, comment='Test conversion workflow complete')

    except Exception as e:

        job_started_by = record['started_by_email'] if (record is not None and 'started_by_email' in record) else 'unknown'
        msg_subject = f"{APP['sakai_name']} to {APP['brightspace_name']}: Failed [{site_title}]"

        try:
            send_template_email(
                APP,
                template='error_workflow.html',
                to=None,
                started_by=job_started_by,
                subj=msg_subject,
                title=site_title,
                site_id=site_id)

        except Exception as em:
            logging.exception(em)

        logging.exception(e)
        state = 'error'
        log = get_log(log_file)

        failure_type = 'exception:workflow'
        failure_detail = str(e)

        update_record(mdb.db_config, link_id, site_id, state, log)
        create_jira(APP=APP, url=site_url, site_id=site_id, site_title=site_title, jira_state=state,
                    jira_log=log, failure_type=failure_type, failure_detail=failure_detail, user=job_started_by)

    finally:
        if APP['email_logs']:
            BODY = json.loads(get_log(log_file))
            logging.info("Emailing job log for site {}".format(site_id))
            send_email(APP['helpdesk-email'], APP['admin_emails'], f"workflow_run : {site_title} {state}", '\n<br/>'.join(BODY))

        sakai_ws.set_site_property(site_id, 'brightspace_conversion_status', state)

def main():
    APP = config.config.APP
    parser = argparse.ArgumentParser(description="This script runs the workflow for a site",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("LINK_ID", help="The Link ID to run the workflow for")
    parser.add_argument("SITE_ID", help="The Site ID to run the workflow for")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())
    APP['debug'] = APP['debug'] or args['debug']

    workflow = os.path.join(APP['config_folder'], "workflow.yaml")
    start_workflow(workflow, args['LINK_ID'], args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
