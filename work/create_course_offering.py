#!/usr/bin/python3

## Workflow operation to create a course template, course offering and enroll Lecturers
## REF: AMA-375

import sys
import os
import re
import argparse
import pymysql
import json
import lxml.etree as ET
import hashlib
import logging

from pymysql.cursors import DictCursor

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.logging_config
import lib.db
import lib.sakai
from lib.utils import middleware_api, sis_course_title, site_has_tool
from lib.d2l import middleware_d2l_api, enroll_in_site, get_brightspace_roles

def cheap_hash(input_str):
    return hashlib.md5(input_str.encode('utf-8')).hexdigest()[:8]

def enroll(SITE_ID, APP, import_id, role):
    logging.info(f'Enroll users for {SITE_ID}')
    dir = r'{}{}-archive'.format(APP['archive_folder'], SITE_ID)
    site_xml_src = f'{dir}/site.xml'
    user_xml_src = f'{dir}/user.xml'

    if os.path.exists(site_xml_src) and os.path.exists(user_xml_src):
        site_tree = ET.parse(site_xml_src)
        user_tree = ET.parse(user_xml_src)

        # Types to enroll
        enroll_types = APP['users']['enroll_account_type']

    # Sakai to Brightspace role map
    enroll_map = APP['users']['enroll_role_map']
    target_role_set = get_brightspace_roles(APP)

    if role in target_role_set.keys():
        target_role_id = target_role_set[role]
    else:
        logging.warning(f"Skipping enrolling users in Brightspace site {import_id}: role {role} not found")
        return

    if os.path.exists(site_xml_src) and os.path.exists(user_xml_src):
        site_tree = ET.parse(site_xml_src)
        user_tree = ET.parse(user_xml_src)

        try:
            # Enroll users whose role is in enroll_map and account_type in enroll_types
            for user_el in site_tree.xpath(".//ability"):
                user_id = user_el.get('userId')
                user_role = user_el.get('roleId')

                if user_role in enroll_map.keys():
                    details = user_tree.xpath(".//user[@id='{}']".format(user_id))

                    if len(details) > 0:
                        _eid = details[0].get('eid')
                        _type = details[0].get('type')
                        if (_type in enroll_types):
                            logging.info(f"Enrolling user eid {_eid} (type={_type}, role={user_role}) in Brightspace site {import_id} (role={role})")
                            enroll_in_site(APP, _eid, import_id, target_role_id)

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

def update_target_site(APP, db_config, link_id, site_id, org_unit_id, is_created, target_title):

    try:
        connection = pymysql.connect(**db_config, cursorclass=DictCursor)
        with connection:
            with connection.cursor() as cursor:
                # Create a new record
                sql = """UPDATE `migration_site` SET modified_at = NOW(), modified_by = 1,
                                target_site_id = %s, target_site_created = %s, target_title = %s
                         WHERE `link_id` = %s and site_id = %s;"""
                cursor.execute(sql, (org_unit_id, is_created, target_title, link_id, site_id))

            connection.commit()
            logging.debug("Update ({}-{}) target_site_id {} ".format(link_id, site_id, org_unit_id))

    except Exception as e:
        raise Exception(f'Could not update target_site_id for {link_id} : {site_id}') from e

# https://docs.valence.desire2learn.com/res/course.html#post--d2l-api-le-(version)-import-(orgUnitId)-copy-
# POST /d2l/api/le/(version)/import/(orgUnitId)/copy/
def copy_default_content(APP, target_site_id):

    src_org_unit = APP['middleware']['course_content_src']

    copy_payload = {
       "SourceOrgUnitId": src_org_unit,
       "Components": ["Checklists", "Content", "CourseFiles", "Dropbox", "Grades", "Quizzes", "Rubrics"],
    }

    payload = {
        'url': f"{APP['brightspace_api']['le_url']}/import/{target_site_id}/copy/",
        'method': 'POST',
        'payload': json.dumps(copy_payload)
    }

    json_response = middleware_d2l_api(APP, payload_data=payload, retries=0)
    return json_response

def run(SITE_ID, APP, link_id):
    logging.info(f'Create Course Template and Offering for {link_id} {SITE_ID}')

    # Migration db
    mdb = lib.db.MigrationDb(APP)

    # Sakai webservices
    sakai_ws = lib.sakai.Sakai(APP)

    record = get_record(mdb.db_config, link_id, SITE_ID)
    if record:
        try:
            course = record['course']
            term = record['term']
            dept = record['dept']
            provider = json.loads(record['provider'])

            # Default naming for a single-roster course
            name = f"{course} {term}"
            role = 'Lecturer'
            site_type = 'course'

            if term == 'other':
                # processing a project or community site
                # Use the original site title as the new name
                name = record['name']
                role = 'Owner'
                site_type = 'community'
                course = f'{dept}_{cheap_hash(name)}'
            else:
                # processing a course site
                if course == 'other':
                    # this course has multiple provider IDs (attached rosters)
                    # Use the original site title for the new name, but replace 20xx with the new year
                    name = re.sub("(20\d{2})", term, record['name'])
                    course = f'{dept}_{cheap_hash(name)}'
                else:
                    # single course
                    title = sis_course_title(APP, course, term)

                    # Add the course title
                    if title:
                        name = f"{course} {term} | {title}"

            # If there are provider codes attached, publish as inactive
            if len(provider):
                active = 'false'
            else:
                active = 'true'

            # optional are:
            #  'course_code': Generated name to re-use in migration checks
            #       'create': True will create the course even if it already exists
            #   'check_name': True will also check the name of the course with course code for uniqueness

            payload = {
                'user': 'migration',
                'faculty': dept,
                'type': site_type,
                'codes': ','.join(provider),
                'name': name,
                'course_code': course,
                'year': term,
                'active': active,
                'role': role
            }

            create_url = "{}{}".format(APP['middleware']['base_url'], APP['middleware']['create_url'])
            json_response = middleware_api(APP, create_url, payload_data=payload)

            if json_response and 'status' in json_response and json_response['status'] == 'success':

                target_site_id = json_response['data']['Identifier']
                target_site_created = json_response['data']['created']

                update_target_site(APP, mdb.db_config, link_id, SITE_ID, target_site_id, target_site_created, name)
                sakai_ws.set_site_property(SITE_ID, 'brightspace_course_site_id', target_site_id)

                # AMA-983 Enroll users only if a new target site was created
                if target_site_created:
                    logging.info(f"New target site created for '{name}' with id {target_site_id} active: {active}")

                    # 1: Enroll users
                    enroll(SITE_ID, APP, json_response['data']['Identifier'], role)
                    logging.info(f"- enrolled site owners in {target_site_id}")

                    # 2: Copy default site content if appropriate (not project site [OTHER])
                    json_response = copy_default_content(APP, target_site_id)

                    if 'status' not in json_response:
                        raise Exception(f'Unable to copy content for {SITE_ID}: {json_response}')
                    else:
                        if json_response['status'] != 'success':
                            raise Exception(f'Unable to copy content for {SITE_ID}: {json_response}')

                    logging.info(f"- copied default course content into {target_site_id}")

                    # 3: Create an Opencast series and LTI tool if the source site had one
                    # https://github.com/cilt-uct/Brightspace-Middleware/blob/main/d2l/services/web/project/api/routes.py#L2369
                    # params: org_id, force
                    if site_has_tool(APP, SITE_ID, "sakai.opencast.series"):
                        # print(f"Site has Opencast LTI tool")
                        payload = {
                            'org_id': target_site_id,
                            'force': 0
                        }

                        add_opencast_url = "{}{}".format(APP['middleware']['base_url'], APP['middleware']['add_opencast_url'])
                        # print(f"Calling endpoint: {add_opencast_url} with payload {payload}")
                        json_response = middleware_api(APP, add_opencast_url, payload_data=payload, method='POST')

                        if json_response and 'status' in json_response and json_response['status'] == 'success':
                            logging.info(f"- added Opencast Lecture Videos tool to {target_site_id}")
                        else:
                            logging.warning(f"- error adding Opencast Lecture Videos tool to {target_site_id}: {json_response}")
                    else:
                        logging.debug(f"Site {SITE_ID} does not have Opencast LTI tool")

                else:
                    logging.info(f"Target site with title '{name}' already exists with id {target_site_id}")

            else:
                # Unexpected error
                raise Exception(f'Unable to create course for {SITE_ID}: {json_response}')

        except Exception as err:
            logging.exception(err)
            raise Exception(f'Encountered: {err} in creating course for {SITE_ID}')

    else:
        logging.info(f'Record for {SITE_ID} - not creating (Create Course Offering = 0)')


def main():
    APP = config.config.APP
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
