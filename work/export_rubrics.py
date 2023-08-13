#!/usr/bin/python3
# -*- coding: iso-8859-15 -*-

## This script accesses a Sakai DB (config.py) and exports the rubrics of a site to a packaged zip file.
## REF: AMA-37

import sys
import os
import argparse
import pymysql
import shutil

from xml.etree import ElementTree

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *
from lib.local_auth import *

# Basic field limit & field name mapping mechanism
dictionary = {'rubric':
                  {'id': 'id', 'title': 'name'},
              'criteria_groups':
                  {'title': 'name', 'order_index': 'sort_order'},
              'criterion':
                  {'order_index': 'sort_order'},
              'level':
                  {'ratings_id': 'level_id', 'order_index': 'sort_order', 'points': 'level_value', 'title': 'name'},
              'cell':
                  {'ratings_id': 'level_id'}
              }


def find_element_key(li, key):
    # this function finds & returns elements in a dictionary
    for d in li:
        if key in d:
            return li[key]

def create_folders(dir_, clean = False):
    if clean:
        if os.path.exists(dir_):
            shutil.rmtree(dir_)

    if not os.path.exists("{}".format(dir_)):
        os.makedirs("{}".format(dir_))

    return r'{}/'.format(os.path.abspath(dir_))

# this function handles data within the Criterion XML element
#  in:  rubric criteria ID
#       XML row object - updated in function
def fetchCriterions(db, rubric_id, xmlRow):

    cursor_criterions = db.cursor()
    sql = "SELECT * " \
          "FROM rbc_rubric_criterions " \
          "INNER JOIN rbc_criterion ON rbc_rubric_criterions.criterions_id = rbc_criterion.id " \
          "WHERE rbc_rubric_id = %s;"
    cursor_criterions.execute(sql, rubric_id)
    columns = [i[0] for i in cursor_criterions.description]

    count = 0
    for row in cursor_criterions.fetchall():

        if (count == 0):
            RowLevelSet = ElementTree.SubElement(xmlRow, "level_set")
            RowLevels = ElementTree.SubElement(RowLevelSet, "levels")
            fetchLevels(db, row[1], RowLevels)

            RowCriteria = ElementTree.SubElement(xmlRow, "criteria")

        count+=1

        # add sub-element(s)
        fetchCriteria(db, row[1], RowCriteria, row)

# this function handles data within the Criteria XML element
#  in:  rubric criteria ID
#       XML row object - updated in function
def fetchCriteria(db, rbc_criterion_id, xmlRow, rowCriteria):

    Row = ElementTree.SubElement(xmlRow, "criterion")
    Row.set('name', rowCriteria[9])
    Row.set('sort_order', str(rowCriteria[2]))

    cursor_criterions = db.cursor()
    sql = "SELECT * FROM rbc_criterion_ratings " \
          "INNER JOIN rbc_rating ON rbc_criterion_ratings.ratings_id = rbc_rating.id " \
          "WHERE rbc_criterion_id = %s;"

    cursor_criterions.execute(sql, rbc_criterion_id)
    columns = [i[0] for i in cursor_criterions.description]

    RowCells = ElementTree.SubElement(Row, "cells")

    for row in cursor_criterions.fetchall():
        # add sub-element(s)
        Row = ElementTree.SubElement(RowCells, "cell")
        Row.set('cell_value', '')
        Row.set('level_id', str(row[1]))
        # create cell description element
        RowDesc = ElementTree.SubElement(Row, "description")
        RowFeedback = ElementTree.SubElement(Row, "feedback")

        if row[4] is not None:
            text = str(row[4]).strip().replace("’", "").replace("\u2019", "&rsquo;")
            fb = str(row[10]).strip().replace("’", "").replace("\u2019", "&rsquo;")
            ElementTree.SubElement(RowDesc, 'text').text = '<p>' + text + '</p>'
            ElementTree.SubElement(RowFeedback, 'text').text = '<p><strong>' + fb + '</strong></p>'

        RowDesc.set('text_type', 'text/html')
        RowFeedback.set('text_type', 'text/html')


# this function handles data within the Levels XML element
#  in:  rubric criteria ID
#       XML row object - updated in function
def fetchLevels(db, rbc_criterion_id, xmlRow):
    cursor_levels = db.cursor()
    sql = "SELECT rbc_criterion_id, ratings_id, order_index, points, title FROM rbc_criterion_ratings " \
          "INNER JOIN rbc_rating ON rbc_criterion_ratings.ratings_id = rbc_rating.id " \
          "WHERE rbc_criterion_id = %s ORDER BY order_index;"

    cursor_levels.execute(sql, rbc_criterion_id)
    columns = [i[0] for i in cursor_levels.description]
    allRows = cursor_levels.fetchall()
    for row in allRows:
        Row = ElementTree.SubElement(xmlRow, "level")
        columnNumber = 0
        for column in columns:

            data = row[columnNumber]
            if data is None:
                data = ''
            data = str(data).replace('&', '\&')
            li = dictionary['level']
            fieldName = find_element_key(li, column)
            if fieldName != None:
                Row.set(fieldName, data.strip().replace("’", "").replace("\u2019", "&rsquo;"))

            columnNumber += 1

# export rubrics for a site to xml file
#  in: site_id
# out: rubric.xml

def exportVulaRubric(db_config, site_id, rubrics_file):
    db = pymysql.connect(**db_config)
    cursor = db.cursor()

    SQL = "SELECT * FROM rbc_rubric WHERE ownerId = %s;"
    cursor.execute(SQL, site_id)
    resp = {"success": 0, "message": ""}

    columns = [i[0] for i in cursor.description]
    allRows = cursor.fetchall()

    if len(allRows) == 0:
        resp["message"] = "No rubrics found in site: {}".format(site_id)
        logging.info('No rubrics found in site: {}'.format(site_id))
        return

    # create rubric XML export document
    xmlDoc = ElementTree.Element("rubrics")
    xmlDoc.set('schemaversion', 'v2011')
    try:
        for row in allRows:
            Row = ElementTree.SubElement(xmlDoc, "rubric")
            columnNumber = 0
            for column in columns:

                data = row[columnNumber]
                if data == None:
                    data = ''

                data = str(data).replace('&', '\&')
                li = dictionary['rubric']
                fieldName = find_element_key(li, column)
                if fieldName != None:
                    Row.set(fieldName, data)

                columnNumber += 1

            # required fields not found in VR
            Row.set('resource_code', '35D32CCE-0F88-4787-B38F-467A98F7D70D-847')
            Row.set('type', '1')
            Row.set('scoring_method', '2')
            Row.set('display_levels_in_des_order', 'True')
            Row.set('state', '0')
            Row.set('visibility', '0')
            Row.set('uses_overall_score', 'True')
            Row.set('has_manual_alignment', 'False')
            Row.set('score_visible_to_assessed_users', 'True')
            Row.set('enabled_feedback_copy', 'False')
            Row.set('usage_restrictions', 'Competency')

            # add sub-element(s)
            RowDesc = ElementTree.SubElement(Row, "description")
            ElementTree.SubElement(RowDesc, 'text').text = row[1]
            RowDesc.set('text_type', 'text')

            RowCriteria_Groups = ElementTree.SubElement(Row, "criteria_groups")

            # new code
            RowCriteria_Group = ElementTree.SubElement(RowCriteria_Groups, "criteria_group")
            RowCriteria_Group.set("name", "Criteria")
            RowCriteria_Group.set("sort_order", "0")

            fetchCriterions(db, row[0], RowCriteria_Group)

        xmlstr = ElementTree.tostring(xmlDoc, encoding='unicode', method='xml')

        # print(xmlstr)
        with open(rubrics_file, "w") as f:
            f.write(xmlstr)

        resp["success"] = 1
        resp["message"] = "XML successfully created"

        # print(json.dumps(resp, indent=4, sort_keys=True))

    except Exception as e:
        resp["success"] = 0
        resp["message"] = e

    finally:
        logging.debug(f'\t{resp}')

    return os.path.exists(rubrics_file)


def run(SITE_ID, APP, now_st = None):

    if now_st is None:
        now_st = ""
    else:
        now_st = f"_{now_st}"

    logging.info('Rubrics: export {} at {}'.format(SITE_ID, now_st))

    output_folder = r'{}{}-rubrics/'.format(APP['output'], SITE_ID)
    if not os.path.exists(output_folder):
        os.mkdir(output_folder)

    tmp = getAuth(APP['auth']['sakai_db'])
    if (tmp is not None):
        DB_AUTH = {'host' : tmp[0], 'database': tmp[1], 'user': tmp[2], 'password' : tmp[3]}
    else:
        logging.error("Authentication required")
        return 0

    if (APP['debug']):
        print(f'{SITE_ID}\n{APP}\n{DB_AUTH}')

    rubrics_file = os.path.join(output_folder, "rubrics_d2l.xml")

    # generate the rubrics export file
    if exportVulaRubric(DB_AUTH, SITE_ID, rubrics_file):
        logging.info(f"Created {rubrics_file}")
    else:
        logging.info("Rubrics XML not created")

def main():

    global APP

    parser = argparse.ArgumentParser(description="This script accesses a Sakai DB and exports the rubrics in D2L XML format.",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID from which to create a rubrics file")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['output'] = create_folders(APP['output'])
    APP['tmp'] = create_folders(APP['tmp'])
    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
