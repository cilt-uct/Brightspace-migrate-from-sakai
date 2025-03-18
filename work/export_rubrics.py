#!/usr/bin/python3
# -*- coding: iso-8859-15 -*-

## This script accesses a Sakai DB (config.py) and exports the rubrics of a site to a packaged zip file.
## REF: AMA-37

import sys
import os
import json
import argparse
import pymysql
import unicodedata
import lxml.etree as ET
import logging

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.config
import config.logging_config
import lib.sakai
import lib.sakai_db

def truncate(txt):

    # D2L rubric criteria group and criteria names have a limit of 255 characters
    if len(txt) > 255:
        txt = txt[0:250] + " ..."

    return txt

# Map table columns to XML attributes
def remove_control_characters(s):
    return "".join(ch for ch in s if unicodedata.category(ch)[0]!="C")

# Sanitize free-form text fields
def sanitize(txt):
    txt = txt.replace("’", "").replace("\u2019", "'")
    return remove_control_characters(txt)

# this function adds one or more multiple criteria_group elements
#  in:  rubric criteria ID
#       XML CriteriaGroups element
def fetchCriteriaGroups(db, rbc_schema, rubric_id, RowCriteria_Groups):

    if rbc_schema == 21:
        sql = """
            SELECT id, title, description, order_index
            FROM rbc_rubric_criterions
            INNER JOIN rbc_criterion ON rbc_rubric_criterions.criterions_id = rbc_criterion.id
            WHERE rbc_rubric_id = %s"""
    else:
        sql = """
            SELECT id, title, description, order_index
            FROM rbc_criterion
            WHERE rubric_id = %s"""

    logging.debug(f"Fetching criteria groups for rubric id {rubric_id}: {sql}")

    cursor_criterions = db.cursor(pymysql.cursors.DictCursor)
    cursor_criterions.execute(sql, rubric_id)

    count = 0
    cg = 0
    last_levels = ""
    level_ids = []
    RowCriteria = None
    next_cg_title = None

    for row in cursor_criterions.fetchall():

        criterions_id = row['id']
        levels_info = getLevelsHash(db, rbc_schema, criterions_id)

        if levels_info['levels'] == 0:
            # Use this as the title for the next criteria group
            next_cg_title = row['title'].strip()
            if row['description'] is not None and len(row['description'].strip()) > 0:
                next_cg_title += ": " + sanitize(row['description'].strip())
            continue

        logging.debug(f"Criterion {criterions_id} '{row['title']}'")

        if (levels_info['levels_hash'] != last_levels):

            logging.debug(f"Starting new criteria group for {levels_info}")

            # Start a new criteria group
            last_levels = levels_info['levels_hash']
            level_ids = levels_info['level_ids']
            cg += 1

            RowCriteria_Group = ET.SubElement(RowCriteria_Groups, "criteria_group")

            if next_cg_title:
                RowCriteria_Group.set("name", truncate(next_cg_title))
                next_cg_title = None
            else:
                RowCriteria_Group.set("name", f"Criteria {cg}")

            RowCriteria_Group.set("sort_order", str(row['order_index']))

            RowLevelSet = ET.SubElement(RowCriteria_Group, "level_set")
            RowLevels = ET.SubElement(RowLevelSet, "levels")
            fetchLevels(db, rbc_schema, criterions_id, RowLevels)

            RowCriteria = ET.SubElement(RowCriteria_Group, "criteria")

        count+=1

        # add sub-element(s)
        fetchCriteria(db, rbc_schema, criterions_id, RowCriteria, row, level_ids)

# this function handles data within the Criteria XML element
#  in:  rubric criteria ID
#       XML row object - updated in function
def fetchCriteria(db, rbc_schema, rbc_criterion_id, xmlRow, rowCriteria, level_ids):

    Row = ET.SubElement(xmlRow, "criterion")

    criteria_name = rowCriteria['title'].strip()
    criteria_desc = rowCriteria['description']
    if criteria_desc is not None and len(criteria_desc.strip()) > 0:
        criteria_name += ": " + sanitize(criteria_desc.strip())

    Row.set('name', truncate(criteria_name))
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

    if rbc_schema == 21:
        sql = """
            SELECT title, description FROM rbc_criterion_ratings
            INNER JOIN rbc_rating ON rbc_criterion_ratings.ratings_id = rbc_rating.id
            WHERE rbc_criterion_id = %s"""
    else:
        sql = """
            SELECT title, description FROM rbc_rating
            WHERE criterion_id = %s ORDER BY order_index"""

    logging.debug(f"Fetching criteria for rubric criterion id {rbc_criterion_id}: {sql}")

    cursor_criterions = db.cursor(pymysql.cursors.DictCursor)
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
def getLevelsHash(db, rbc_schema, rbc_criterion_id):

    if rbc_schema == 21:
        sql = """
            SELECT id, order_index, points, title FROM rbc_criterion_ratings
            INNER JOIN rbc_rating ON rbc_criterion_ratings.ratings_id = rbc_rating.id
            WHERE rbc_criterion_id = %s ORDER BY order_index"""
    else:
        sql = """
            SELECT id, order_index, points, title
            FROM rbc_rating WHERE criterion_id = %s ORDER BY order_index"""

    logging.debug(f"Fetching levels hash for rubric criterion id {rbc_criterion_id}: {sql}")

    cursor_levels = db.cursor(pymysql.cursors.DictCursor)
    cursor_levels.execute(sql, rbc_criterion_id)
    allRows = cursor_levels.fetchall()

    levels = 0
    levels_hash = ""
    level_ids = []

    for row in allRows:
        levels += 1
        levels_hash += f"{row['order_index']}:{row['points']}:{sanitize(row['title'].strip())}|"
        level_ids.append(row['id'])

    return { 'levels' : levels, 'levels_hash' : levels_hash, 'level_ids' : level_ids }

# this function handles data within the Levels XML element
#  in:  rubric criteria ID
#       XML row object - updated in function

def fetchLevels(db, rbc_schema, rbc_criterion_id, xmlRow):

    if rbc_schema == 21:
        sql = """
            SELECT id, order_index, points, title FROM rbc_criterion_ratings
            INNER JOIN rbc_rating ON rbc_criterion_ratings.ratings_id = rbc_rating.id
            WHERE rbc_criterion_id = %s ORDER BY order_index"""
    else:
        sql = """
            SELECT id, order_index, points, title
            FROM rbc_rating WHERE criterion_id = %s ORDER BY order_index"""

    logging.debug(f"Fetching levels for rubric criterion id {rbc_criterion_id}: {sql}")

    cursor_levels = db.cursor(pymysql.cursors.DictCursor)
    cursor_levels.execute(sql, rbc_criterion_id)
    allRows = cursor_levels.fetchall()

    # <level level_id="65914" sort_order="0" level_value="0.0" name="Inadequate"/>
    # <level level_id="65915" sort_order="1" level_value="1.0" name="Meets expectations"/>
    # <level level_id="65916" sort_order="2" level_value="2.0" name="Exceeds expectations"/>

    row_num = 1
    for row in allRows:

        row_points = row['points']

        # D2L rubrics do not allow negative points
        if row_points < 0:
            # TODO flag in conversion report
            row_points = 0

        Row = ET.SubElement(xmlRow, "level")
        Row.set('level_id', str(row['id']))
        Row.set('sort_order', str(row['order_index']))
        Row.set('level_value', str(row_points))

        row_name = sanitize(row['title'].strip())
        if not row_name:
            row_name = f"Level {row_num}"

        Row.set('name', row_name)
        row_num += 1

# export rubrics for a site to xml file
#  in: site_id
# out: rubric.xml

def exportSakaiRubric(db_config, rbc_schema, site_id, rubrics_file):
    db = pymysql.connect(**db_config)
    cursor = db.cursor(pymysql.cursors.DictCursor)

    SQL = "SELECT id, title FROM rbc_rubric WHERE ownerId = %s"
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

        # Brightspace rubrics have a description but we don't have anything to put here
        RowDesc = ET.SubElement(Row, "description")
        ET.SubElement(RowDesc, 'text').text = ""
        RowDesc.set('text_type', 'text')

        # Rubric detail
        RowCriteria_Groups = ET.SubElement(Row, "criteria_groups")
        fetchCriteriaGroups(db, rbc_schema, row['id'], RowCriteria_Groups)

    # Write the XML to file
    xmlstr = ET.tostring(xmlDoc, encoding='unicode', method='xml', pretty_print=True)
    with open(rubrics_file, "w") as f:
            f.write(xmlstr)

    return os.path.exists(rubrics_file)

# Export rubric details for conversion report
def exportRubricAssociations(db_config, rbc_schema, site_id, output_folder):
    db = pymysql.connect(**db_config)
    cursor = db.cursor(pymysql.cursors.DictCursor)

    sql = """
        SELECT rubric_id, title, toolId
        FROM rbc_tool_item_rbc_assoc RA inner join rbc_rubric RR on RA.rubric_id = RR.id
        WHERE RR.ownerId = %s ORDER BY rubric_id"""

    logging.debug(f"Fetching rubric associations for rubrics in site {site_id}: {sql}")

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

    # Check which version of Sakai
    sakai_ws = lib.sakai.Sakai(APP)
    sakai_version = sakai_ws.config("version.sakai")

    if sakai_version is None:
        logging.warning("Unknown Sakai version, unable to proceed.")
        return

    logging.info(f"Sakai system {sakai_ws.url()} version is {sakai_version}")

    # Connect to the Sakai database for the rubrics tables
    sdb = lib.sakai_db.SakaiDb(APP)
    rubrics_tables = sdb.table_count("rbc_")

    logging.info(f"Sakai database has {rubrics_tables} rbc_ tables")

    rbc_schema = None

    if sakai_version.startswith("21") and rubrics_tables == 13:
        rbc_schema = 21
    else:
        rbc_schema = 22

    logging.info(f"Using rubrics table schema {rbc_schema}")

    # generate the rubrics export file
    rubrics_file = os.path.join(output_folder, "rubrics_d2l.xml")
    if exportSakaiRubric(sdb.db_config, rbc_schema, SITE_ID, rubrics_file):
        logging.info(f"Created {rubrics_file}")
        exportRubricAssociations(sdb.db_config, rbc_schema, SITE_ID, output_folder)
    else:
        logging.info("Rubrics XML not created")

def main():

    APP = config.config.APP

    parser = argparse.ArgumentParser(description="This script accesses a Sakai DB and exports the rubrics in D2L XML format.",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID from which to create a rubrics file")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    if APP['debug']:
        config.logging_config.logger.setLevel(logging.DEBUG)

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
