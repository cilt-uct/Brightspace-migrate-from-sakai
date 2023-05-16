#!/usr/bin/python3

## Workflow operation to create a course template, course offering and enroll Lecturers
## REF: AMA-375

import sys
import os
import re
import argparse
import pymysql
import json
import requests
import lxml.etree as ET
import importlib
import hashlib

from pymysql.cursors import DictCursor
from requests.exceptions import HTTPError

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *
from lib.local_auth import *

# Departments options if term is "other"            
other_departments = {
    'other' : 'other',     # University - wide Community or Activity
    'COM' : 'COM-other',   # Faculty of Commerce
    'EBE' : 'EBE-other',   # Faculty of Engineering & Built Environment
    'FHS' : 'FHS-other',   # Faculty of Health Sciences
    'HUM' : 'HUM-other',   # Faculty of Humanities
    'LAW' : 'LAW-other',   # Faculty of Law
    'SCI' : 'SCI-other',   # Faculty of Science
    'GSB' : 'GSB',         # Graduate School of Business (GSB)
    'CHED' : 'CHED-other', # Centre for Higher Education Development
}

cheap_hash = lambda input: hashlib.md5(input.encode('utf-8')).hexdigest()[:8]


def enroll(SITE_ID, APP, import_id, role):
    logging.info(f'Enroll users for {SITE_ID}')
    dir = r'{}{}-archive'.format(APP['archive_folder'], SITE_ID)
    site_xml_src = f'{dir}/site.xml'
    user_xml_src = f'{dir}/user.xml'

    # it would be beter to split this out into the original workflow and 
    # create a column entry for this field so that even if the archive folder disapears
    # it can still be processed

    if os.path.exists(site_xml_src) and os.path.exists(user_xml_src):
        site_tree = ET.parse(site_xml_src)
        user_tree = ET.parse(user_xml_src)

        try:
            # get a array of role abilities for which the role is 'Support staff' or 'Site owner' 
            # return the userId's in a list
            user_ids = list(map( lambda el: el.get('userId'), site_tree.xpath(".//ability[@roleId='Support staff']") + \
                                                            site_tree.xpath(".//ability[@roleId='Site owner']")))
            for user_id in user_ids:
                details = user_tree.xpath(".//user[@id='{}']".format(user_id))

                if len(details) > 0:
                    _eid = details[0].get('eid')
                    _type = details[0].get('type')
                    if (_type in APP['course']['enroll_user_type']):
                        find_user_and_enroll_in_site(APP, _eid, import_id, role)

        except Exception as e:
            raise Exception(f'Could not enroll users in {SITE_ID}') from e
    else:
        raise Exception(f'XML file does not exist anymore {dir}/site.xml or user.xml')

def get_record(db_config, link_id, site_id):
    try:
        connection = pymysql.connect(**db_config, cursorclass=DictCursor)
        with connection:
            with connection.cursor() as cursor:
                sql = """SELECT IFNUll(`A`.target_title, `A`.title) as `name`, 
                                IFNULL(`A`.target_course, '') as `course`, 
                                IFNULL(`A`.target_dept, '') as `dept`, 
                                IF(IFNULL(`A`.target_term, 0) = 9999, 'other', IFNULL(`A`.target_term, 0))  as `term`,
                                `A`.create_course_offering,
                                `A`.provider
                    FROM migration_site `A`
                    where `A`.link_id = %s and `A`.site_id=%s and `A`.create_course_offering = 1 limit 1;"""
                cursor.execute(sql, (link_id, site_id))
                return cursor.fetchone()

    except Exception as e:
        logging.exception(e)
        logging.error(f"Could not retrieve migration record {link_id} : {site_id}")
        return None

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

def update_target_site(db_config, link_id, site_id, org_unit_id, is_created):
    set_site_property(site_id, 'amathuba_course_site_id', org_unit_id)

    try:
        connection = pymysql.connect(**db_config, cursorclass=DictCursor)
        with connection:
            with connection.cursor() as cursor:
                # Create a new record
                sql = """UPDATE `migration_site` SET modified_at = NOW(), modified_by = 1, 
                                target_site_id = %s, target_site_created = %s
                         WHERE `link_id` = %s and site_id = %s;"""
                cursor.execute(sql, (org_unit_id, is_created, link_id, site_id))

            connection.commit()
            logging.debug("Update ({}-{}) target_site_id {} ".format(link_id, site_id, org_unit_id))

    except Exception as e:
        raise Exception(f'Could not update target_site_id for {link_id} : {site_id}') from e

def run(SITE_ID, APP, link_id):
    logging.info(f'Create Course Template and Offering for {link_id} {SITE_ID}')

    tmp = getAuth(APP['auth']['db'])
    if (tmp is not None):
        DB_AUTH = {'host' : tmp[0], 'database': tmp[1], 'user': tmp[2], 'password' : tmp[3]}
    else:
        logging.error("Authentication required {}".format(APP['auth']['db']))
        return 0     

    record = get_record(DB_AUTH, link_id, SITE_ID)
    if record:
        try: 
            name = "{} {}".format(record['course'], record['term'])
            course = record['course']
            dept = record['dept']
            term = record['term']
            role = 'Lecturer'
            provider = record['provider']

            if term == 'other':
                # so we are processing a project or community site
                name = re.sub("(20\d{2})", "", record['name'])
                course = f'{dept}_{cheap_hash(name)}'
                dept = other_departments[dept]
                role = 'Owner'

            if course == 'other':
                name = re.sub("(20\d{2})", term, record['name'])
                course = f'{dept}_{cheap_hash(name)}'
                
            # 4 required fields for course creation, 
            # optional are:
            #     'provider': Add enrollment information for the provided courses per term
            #       'create': True will create the course even if it already exists
            #   'check_name': True will also check the name of the course with course code for uniqueness
            payload = {'name': name, 
                        'course': course,
                        'dept': dept, 
                        'term': term,
                        'provider': provider}

            create_url = "{}{}".format(APP['middleware']['base_url'], APP['middleware']['create_url'])

            json_response = middleware_api(APP, create_url, payload_data=payload)

            if json_response and 'status' in json_response and json_response['status'] == 'success':
                update_target_site(DB_AUTH, link_id, SITE_ID, json_response['data']['Identifier'], json_response['data']['created'])
                enroll(SITE_ID, APP, json_response['data']['Identifier'], role)
                # if appropriate (not project site [OTHER]) - copy over content
            else:
                raise Exception(f'Unable to create course for {SITE_ID}: {json_response}')

        except Exception as err:
            logging.exception(err)
            raise Exception(f'Encountered: {err} in creating course for {SITE_ID}')

    else:
        logging.info(f'Record for {SITE_ID} - not creating (Create Course Offering = 0)')

    
def main():
    global APP
    parser = argparse.ArgumentParser(description="Workflow operation to create a course template, course offering and enroll Lecturers",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("LINK_ID", help="The Link ID to run the workflow for")
    parser.add_argument("SITE_ID", help="The Site ID to run the workflow for")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())
    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP, args['LINK_ID'])

if __name__ == '__main__':
    main()

