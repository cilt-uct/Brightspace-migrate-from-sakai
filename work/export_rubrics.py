#!/usr/bin/python3
# -*- coding: iso-8859-15 -*-

## This script accesses a Sakai DB (config.py) and exports the rubrics of a site to a packaged zip file.
## REF: AMA-37

import sys
import os
import argparse
import pymysql
import shutil
import unicodedata
import lxml.etree as ET

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *
from lib.local_auth import *

# Map table columns to XML attributes
def remove_control_characters(s):
    return "".join(ch for ch in s if unicodedata.category(ch)[0]!="C")

# Sanitize free-form text fields
def sanitize(txt):
    txt = txt.replace("’", "").replace("\u2019", "'")
    return remove_control_characters(txt)

def create_folders(dir_, clean = False):
    if clean:
        if os.path.exists(dir_):
            shutil.rmtree(dir_)

    if not os.path.exists("{}".format(dir_)):
        os.makedirs("{}".format(dir_))

    return r'{}/'.format(os.path.abspath(dir_))

# this function adds one or more multiple criteria_group elements
#  in:  rubric criteria ID
#       XML CriteriaGroups element
def fetchCriteriaGroups(db, rubric_id, RowCriteria_Groups):

    cursor_criterions = db.cursor(pymysql.cursors.DictCursor)
    sql = "SELECT criterions_id, title, order_index " \
          "FROM rbc_rubric_criterions " \
          "INNER JOIN rbc_criterion ON rbc_rubric_criterions.criterions_id = rbc_criterion.id " \
          "WHERE rbc_rubric_id = %s"
    cursor_criterions.execute(sql, rubric_id)

    count = 0
    start_group = True
    cg = 0
    last_levels = ""
    level_ids = []

    for row in cursor_criterions.fetchall():

        criterions_id = row['criterions_id']
        levels_info = getLevelsHash(db, criterions_id)

        if (levels_info['levels_hash'] != last_levels):

            # Start a new criteria group
            last_levels = levels_info['levels_hash']
            level_ids = levels_info['level_ids']
            cg += 1

            RowCriteria_Group = ET.SubElement(RowCriteria_Groups, "criteria_group")
            RowCriteria_Group.set("name", f"Criteria {cg}")
            RowCriteria_Group.set("sort_order", str(row['order_index']))

            RowLevelSet = ET.SubElement(RowCriteria_Group, "level_set")
            RowLevels = ET.SubElement(RowLevelSet, "levels")
            fetchLevels(db, criterions_id, RowLevels)

            RowCriteria = ET.SubElement(RowCriteria_Group, "criteria")

        count+=1

        # add sub-element(s)
        fetchCriteria(db, row['criterions_id'], RowCriteria, row, level_ids)

# this function handles data within the Criteria XML element
#  in:  rubric criteria ID
#       XML row object - updated in function
def fetchCriteria(db, rbc_criterion_id, xmlRow, rowCriteria, level_ids):

    Row = ET.SubElement(xmlRow, "criterion")
    Row.set('name', rowCriteria['title'])
    Row.set('sort_order', str(rowCriteria['order_index']))

    RowCells = ET.SubElement(Row, "cells")

    # <cell cell_value="" level_id="65914">
    #    <description text_type="text/html">
    #      <text>&lt;p&gt;&lt;/p&gt;</text>
    #    </description>
    #    <feedback text_type="text/html">
    #      <text>&lt;p&gt;&lt;strong&gt;Inadequate&lt;/strong&gt;&lt;/p&gt;</text>
    #    </feedback>
    #  </cell>

    cursor_criterions = db.cursor(pymysql.cursors.DictCursor)
    sql = "SELECT * FROM rbc_criterion_ratings " \
          "INNER JOIN rbc_rating ON rbc_criterion_ratings.ratings_id = rbc_rating.id " \
          "WHERE rbc_criterion_id = %s"
    cursor_criterions.execute(sql, rbc_criterion_id)

    cell = 0

    for row in cursor_criterions.fetchall():

        # add sub-element(s)
        Row = ET.SubElement(RowCells, "cell")
        Row.set('cell_value', '')
        Row.set('level_id', str(level_ids[cell]))
        # create cell description element
        RowDesc = ET.SubElement(Row, "description")
        RowDesc.set('text_type', 'text/html')

        RowFeedback = ET.SubElement(Row, "feedback")
        RowFeedback.set('text_type', 'text/html')

        if row['description'] is not None:
            text = str(row['description']).strip()
            fb = str(row['title']).strip()
            ET.SubElement(RowDesc, 'text').text = f'<p>{sanitize(text)}</p>'
            ET.SubElement(RowFeedback, 'text').text = f'<p><strong>{sanitize(fb)}</strong></p>'

        cell += 1

    return

# return { count: #, hash: string, ids: [list] }
def getLevelsHash(db, rbc_criterion_id):
    cursor_levels = db.cursor(pymysql.cursors.DictCursor)
    sql = "SELECT rbc_criterion_id, ratings_id, order_index, points, title FROM rbc_criterion_ratings " \
          "INNER JOIN rbc_rating ON rbc_criterion_ratings.ratings_id = rbc_rating.id " \
          "WHERE rbc_criterion_id = %s ORDER BY order_index"

    cursor_levels.execute(sql, rbc_criterion_id)
    allRows = cursor_levels.fetchall()

    levels = 0
    levels_hash = ""
    level_ids = []

    for row in allRows:
        levels += 1
        levels_hash += f"{row['order_index']}:{row['points']}:{sanitize(row['title'].strip())}|"
        level_ids.append(row['ratings_id'])

    return { 'levels' : levels, 'levels_hash' : levels_hash, 'level_ids' : level_ids }

# this function handles data within the Levels XML element
#  in:  rubric criteria ID
#       XML row object - updated in function

def fetchLevels(db, rbc_criterion_id, xmlRow):
    cursor_levels = db.cursor(pymysql.cursors.DictCursor)
    sql = "SELECT rbc_criterion_id, ratings_id, order_index, points, title FROM rbc_criterion_ratings " \
          "INNER JOIN rbc_rating ON rbc_criterion_ratings.ratings_id = rbc_rating.id " \
          "WHERE rbc_criterion_id = %s ORDER BY order_index"

    cursor_levels.execute(sql, rbc_criterion_id)
    allRows = cursor_levels.fetchall()

    # <level level_id="65914" sort_order="0" level_value="0.0" name="Inadequate"/>
    # <level level_id="65915" sort_order="1" level_value="1.0" name="Meets expectations"/>
    # <level level_id="65916" sort_order="2" level_value="2.0" name="Exceeds expectations"/>

    for row in allRows:
        Row = ET.SubElement(xmlRow, "level")
        Row.set('level_id', str(row['ratings_id']))
        Row.set('sort_order', str(row['order_index']))
        Row.set('level_value', str(row['points']))
        Row.set('name', sanitize(row['title'].strip()))

# export rubrics for a site to xml file
#  in: site_id
# out: rubric.xml

def exportSakaiRubric(db_config, site_id, rubrics_file):
    db = pymysql.connect(**db_config)
    cursor = db.cursor(pymysql.cursors.DictCursor)

    SQL = "SELECT * FROM rbc_rubric WHERE ownerId = %s"
    cursor.execute(SQL, site_id)

    siteRubrics = cursor.fetchall()

    if len(siteRubrics) == 0:
        logging.info(f'No rubrics found in site {site_id}')
        return

    # create rubric XML export document
    xmlDoc = ET.Element("rubrics")
    xmlDoc.set('schemaversion', 'v2011')
    export_rubric_id = 0

    for row in siteRubrics:

        export_rubric_id +=1

        Row = ET.SubElement(xmlDoc, "rubric")
        Row.set('id', f'{export_rubric_id}')
        Row.set('name', sanitize(row['title'].strip()))
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
        RowDesc = ET.SubElement(Row, "description")
        ET.SubElement(RowDesc, 'text').text = row['description']
        RowDesc.set('text_type', 'text')

        RowCriteria_Groups = ET.SubElement(Row, "criteria_groups")
        fetchCriteriaGroups(db, row['id'], RowCriteria_Groups)

    # Write the XML to file
    xmlstr = ET.tostring(xmlDoc, encoding='unicode', method='xml', pretty_print=True)
    with open(rubrics_file, "w") as f:
            f.write(xmlstr)

    return os.path.exists(rubrics_file)

# Export details of where Rubrics are used, for conversion report
def exportRubricAssociations(db_config, site_id, output_folder):
    db = pymysql.connect(**db_config)
    cursor = db.cursor(pymysql.cursors.DictCursor)

    sql = "SELECT rubric_id, title, toolId " \
          "FROM rbc_tool_item_rbc_assoc RA inner join rbc_rubric RR on RA.rubric_id = RR.id " \
          "WHERE RA.ownerId = %s and RA.ownerType = 'site'"

    cursor.execute(sql, site_id)
    siteRubricAssoc = cursor.fetchall()

    if len(siteRubricAssoc) == 0:
        logging.info(f'No rubric associations found in {site_id}')
    else:
        logging.info(f"{len(siteRubricAssoc)} rubric tool association(s) in {site_id}")

    rubric_assoc = { 'rubric_tool' : [] }

    for ra in siteRubricAssoc:
        ra_info = {
                'rubric_id' : ra['rubric_id'],
                'title' : ra['title'],
                'toolId' : ra['toolId']
        }
        rubric_assoc['rubric_tool'].append(ra_info)

    # Write to a json file

    rubrics_assoc_file = f"{output_folder}/rubric_tools.json"
    with open(rubrics_assoc_file, "w") as f:
        json.dump(rubric_assoc, f, indent=4)

    return

def run(SITE_ID, APP):

    logging.info(f'Rubrics: export {SITE_ID}')

    output_folder = r'{}{}-rubrics/'.format(APP['output'], SITE_ID)
    if not os.path.exists(output_folder):
        os.mkdir(output_folder)

    tmp = getAuth(APP['auth']['sakai_db'])
    if (tmp is not None):
        DB_AUTH = {'host' : tmp[0], 'database': tmp[1], 'user': tmp[2], 'password' : tmp[3]}
    else:
        raise Exception("db authentication required")

    rubrics_file = os.path.join(output_folder, "rubrics_d2l.xml")

    # generate the rubrics export file
    if exportSakaiRubric(DB_AUTH, SITE_ID, rubrics_file):
        logging.info(f"Created {rubrics_file}")
        exportRubricAssociations(DB_AUTH, SITE_ID, output_folder)
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
