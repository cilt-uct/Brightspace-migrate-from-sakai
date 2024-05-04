#!/usr/bin/python3

## This script runs the update workflow for a site

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

import config.config
import lib.local_auth
import lib.db
import lib.sakai

from config.logging_config import formatter, logger
from lib.utils import get_log, send_template_email, send_email, create_jira
from lib.jira_rest import MyJira


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

def check_log_file_for_errors(filename):
    _file = open(filename, "r")
    lines = _file.readlines()
    _file.close()

    # number of ERROR log entries
    return len(list(filter(lambda s: re.match(r'.*(\[ERROR\]).*',s), lines)))

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

def close_jira(APP, site_id):
    with MyJira() as j:
        fields = {
            'project': {'key': APP['jira']['key']},
            'site_id': str(site_id),
            'comment': 'Update workflow complete'
        }

        j.closeIssue(fields)

def run_workflow_step(APP, step, site_id, log_file, db_config, **kwargs):

    provider = json.loads(kwargs['provider'])
    provider_count = len(provider)
    provider_list = ' '.join(provider)

    if step['action'] == "mail":
        if 'template' in step:
            return send_template_email(
                APP,
                template=step['template'] + ".html",
                to=kwargs['to'],
                started_by=kwargs['started_by'],
                subj=step['subject'],
                title=kwargs['title'],
                site_id=site_id,
                import_id=kwargs['import_id'],
                report_url=kwargs['report_url'],
                target_site_id=kwargs['target_site_id'],
                target_site_created=kwargs['target_site_created'],
                target_term=kwargs['target_term'],
                create_course_offering=kwargs['create_course_offering'],
                provider_count=provider_count,
                provider_list=provider_list,
                target_title=kwargs['target_title']
            )
        else:
            logging.warn("No template found in mail step")

    elif step['action'] == "sleep":
        if 'time' in step:
            logging.info("Sleeping for {} seconds".format(step['time']))
            time.sleep(int(step['time']))
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

            if 'use_transfer_id' in step:
                new_kwargs['transfer_id'] = kwargs['transfer_id']

            if 'use_target_site_id' in step:
                new_kwargs['target_site_id'] = kwargs['target_site_id']

            if 'use_import_id' in step:
                new_kwargs['import_id'] = kwargs['import_id']

            if 'use_started_by' in step:
                new_kwargs['started_by'] = kwargs['started_by']

            if 'use_title' in step:
                new_kwargs['title'] = kwargs['title']

            if 'conversion_success' in step:
                new_kwargs['brightspace_conversion_success'] = kwargs['now_st']
                new_kwargs['brightspace_conversion_status'] = 'completed'

            func(**new_kwargs)  # this runs the steps - and writes to log file
            return True

        except Exception as e:
            logging.exception(e)
            logging.error("Workflow operation {} = {} ".format(step['action'], e))
            return False

def start_workflow(workflow_file, link_id, site_id, APP):

    mdb = lib.db.MigrationDb(APP)

    # Sakai webservices
    sakai_ws = lib.sakai.Sakai(APP)

    # datetime object containing current date and time that the workflow was started
    now = datetime.now()
    now_st = now.strftime("%Y-%m-%d_%H%M%S")

    site_title = site_id
    site_url   = site_id

    failure_type = ''
    failure_detail = ''

    start_time = time.time()

    state = 'updating'
    record = None

    try:
        record = mdb.get_record(link_id=link_id, site_id=site_id)

        if (record is None):
            raise Exception(f'Could not find record to start update for {link_id} : {site_id}')

        site_title = record['title']
        site_url = record['url']
        failure_type = record['failure_type']
        failure_detail = record['failure_detail']

        log_file = '{}/{}_update_{}.log'.format(APP['log_folder'], site_id, now_st)
        setup_log_file(APP, log_file, site_id, record['workflow'])

        workflow_steps = lib.utils.read_yaml(workflow_file)
        update_record(mdb.db_config, link_id, site_id, state, get_log(log_file))

        if workflow_steps['STEPS'] is not None:

            for step in workflow_steps['STEPS']:
                logging.info("Executing update workflow step: {}".format(step['action']))
                if 'state' in step:
                    state = step['state']

                failure_type = f"exception:update:{step['action']}"

                # Read record again to get any updates from prior workflow steps
                record = mdb.get_record(link_id=link_id, site_id=site_id)

                if not run_workflow_step(APP, step, site_id, log_file, mdb.db_config,
                                         to=record['notification'],
                                         started_by=record['started_by_email'],
                                         now_st=now_st,
                                         transfer_id=record['transfer_site_id'],
                                         import_id=record['imported_site_id'],
                                         link_id=link_id,
                                         title=record['title'],
                                         target_site_id=record['target_site_id'],
                                         target_site_created=record['target_site_created'],
                                         target_term=record['target_term'],
                                         create_course_offering=record['create_course_offering'],
                                         provider=record['provider'],
                                         target_title=record['target_title'],
                                         report_url=record['report_url']):
                    # something went wrong while processing this step
                    raise Exception("On step: {}".format(step['action']))

                logging.info("Completed update workflow step: {}".format(step['action']))

            close_jira(APP, site_id=site_id)
        else:
            logging.warning("There are no workflows steps in this workflow.")

        logging.info("\t{}".format(str(timedelta(seconds=(time.time() - start_time)))))
        update_record(mdb.db_config, link_id, site_id, state, get_log(log_file))

    except Exception as e:

        failure_detail = str(e)

        msg_subject = f"{APP['sakai_name']} to {APP['brightspace_name']}: Import failed [{site_title}]"

        send_template_email(
            APP,
            template='error_import.html',
            to=None,
            started_by=record['started_by_email'],
            subj=msg_subject,
            title=site_title,
            site_id=site_id)

        logging.exception(e)

        state = 'error'
        log = get_log(log_file)
        update_record(mdb.db_config, link_id, site_id, state, log)
        create_jira(APP=APP, url=site_url, site_id=site_id, site_title=site_title, jira_state=state,
                    jira_log=log, failure_type=failure_type, failure_detail=failure_detail, user=record['started_by_email'])
        sakai_ws.set_site_property(site_id, 'brightspace_conversion_status', state)

    finally:
        if APP['email_logs']:
            BODY = json.loads(get_log(log_file))
            logging.info("Emailing job log for site {}".format(site_id))
            send_email(APP['helpdesk-email'], APP['admin_emails'], f"update_run : {site_title} {state}", '\n<br/>'.join(BODY))

        # Clean up log file
        os.remove(log_file)


def main():
    APP = config.config.APP
    parser = argparse.ArgumentParser(description="This script runs the update workflow for a site",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("LINK_ID", help="The Link ID to run the update workflow for")
    parser.add_argument("SITE_ID", help="The Site ID to run the update workflow for")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())
    APP['debug'] = APP['debug'] or args['debug']

    workflow = os.path.join(APP['config_folder'], "update.yaml")
    start_workflow(workflow, args['LINK_ID'], args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
