#!/usr/bin/python3

## This script reviews the archive site and creates a report that shows what could be converted and what could not
## REF: AMA-36

import sys
import os
import json
import copy
import shutil
import argparse
import pymysql
import logging

from bs4 import BeautifulSoup
from datetime import datetime
from funcy import project
from pymysql.cursors import DictCursor

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.config
import config.logging_config
from lib.utils import init__soup
from lib.conversion import *

import lib.utils
import lib.local_auth

# fetch site info
#  in: site_folder
def site(site_folder):
    file = "site.xml"
    file_path = os.path.join(site_folder, file)
    with open(file_path) as fp:
        soup = BeautifulSoup(fp, 'xml')
        items = soup.find_all("site")
        # site.xml seems to have only 1 site element within the main site element
        site = items[1]
        return site


def populate_issue_details(dom, found_div, items):
    table_template = found_div.find('table', {'id': 'issue_details_table_template'})
    for issue_item in items:
        table = copy.copy(table_template)
        header = dom.new_tag('h3')
        header.string = issue_item['description']
        table['id'] = f'table_{issue_item["key"]}'
        table_head = table.find('th', {'id': 'head'})
        table_head['id'] = issue_item['key']
        if 'icon-class' in issue_item:
            table_head['class'] = issue_item['icon-class']
        table_head.string = ''
        table_head.append(header)
        table_row = table.find('tr', {'id': 'data-row'})
        table_data = table.find('td', {'id': 'data'})
        page = dom.new_tag('b')
        page.string = issue_item['detail-heading'] if 'detail-heading' in issue_item else "Item"
        row = copy.copy(table_row)
        data = copy.copy(table_data)
        data['id'] = f'page_{issue_item["key"]}'
        data.string = ''
        data.append(page)
        row.clear()
        row.append(data)
        table.append(row)
        for issue in issue_item['is_found']:
            list_row = copy.copy(table_row)
            list_data = copy.copy(table_data)
            list_data['id'] = f'data_{issue}'
            list_data.string = issue
            list_row.clear()
            list_row.append(list_data)
            table.append(list_row)

        table_data.decompose()
        found_div.append(table)

    table_template.decompose()


# populate lists
# in: dict (dictionary)
def populate_issues(dom, found_div, items, config, found_details):

    tool_icon = {}

    # Tool icon dict
    for tool in config['tools']:
        if 'icon-class' in tool:
            tool_icon[tool['key']] = tool['icon-class']

    # Find the template]
    card_template = found_div.find("div", {"id": "issue_card_template"})

    for line in items:

        card_item = copy.copy(card_template)
        key = line['key']

        # ID
        card_item['id'] = f"issue_{key}"

        # Class
        cls = [ 'card_icon' ]

        if 'icon-class' in line:
            cls.append(line['icon-class'])
        else:
            # Default for tool
            if line['tool'] in tool_icon:
                cls.append(tool_icon[line['tool']])
        if 'tool' in line:
            cls.append('tool_' + line['tool'])

        card_icon = card_item.find("div", {"id": "card_icon"})
        if card_icon:
            card_icon['class'] = cls

        # Description (title)
        if 'description' in line:
            card_item.find("h3", {"id": "issue_title"}).string = line['description']

        # Found text
        if 'found' in line:
            card_item.find("p", {"id": "issue_desc"}).string = line['found']

        # More info link
        if 'info' in line:
            moreinfo = dom.new_tag('a', **{"href": line['info']['url'], "target":"_blank"})
            moreinfo.string = line['info']['a']
            card_item.find("p", {"id": "issue_desc"}).append(moreinfo)

        if line in found_details:
            details = dom.new_tag('a', **{"href": f'#{line["key"]}'})
            details.string = 'Issue detail'
            p_tag = card_item.find("p", {"id": "issue_desc"})
            p_tag.append(details)

        # Make the id elements unique
        card_item['id'] = f"issue_{key}"
        card_icon['id'] = f"card_icon_{key}"
        card_item.find("h3", {"id": "issue_title"})['id'] = f"issue_title_{key}"
        card_item.find("p", {"id": "issue_desc"})['id'] = f"issue_desc_{key}"

        found_div.append(card_item)

    card_template.decompose()

def populate_tools(dom, found_ul, items):

    for line in items:
        key = line['key']

        # CSS
        cls = [ 'found' ]
        el = dom.new_tag('li', **{"class": ' '.join(cls), "id": key})

        tool_image = dom.new_tag('span',  **{"class" : "tool_image"})
        if 'class' in line:
            tool_image['class'] = f"tool_image {line['class']}"
        el.append(tool_image)

        # Name
        tool_name = dom.new_tag('span',  **{"class" : "tool_name"})
        tool_name.string = line['name']
        el.append(tool_name)

        # Detail
        if 'found' in line:
            detail = dom.new_tag('span',  **{"class" : "tool_detail"})
            detail.string = ' | ' + line['found']
            el.append(detail)

        if 'info' in line:
            moreinfo = dom.new_tag('a', **{"href": line['info']['url'], "target":"_blank"})
            moreinfo.string = line['info']['a']
            el.append(moreinfo)

        # Append tool
        found_ul.append(el)

# create html output page
def html(APP, site_folder, output_file, output_url, config, SITE_ID):
    site_root = site(site_folder)
    now = datetime.now()
    dt_string = now.strftime("%-d %b %Y %H:%M")

    try:

        # Prefer the original title if available (which it should be)
        if site_root.get("original-title"):
            site_title = site_root.get("original-title")
        else:
            site_title = site_root.get("title")

        with open(f"{APP['report']['template']}", 'r') as f:
            contents = f.read()
            dom = BeautifulSoup(contents, "html.parser")

            # Document title
            head_container = dom.find("head")
            pagetitle = head_container.find("title")
            if pagetitle:
                pagetitle.string = f"{site_title} conversion report"

            # Page title
            header_title = dom.find("p", {"id" : "site_title"})
            header_title.string = f"{site_title}"

            # Report info strip
            site_title_tag = dom.find("p", {"id": "report_info"})
            site_title_tag.string = f"Report generated {dt_string} for {APP['sakai_name']} site"
            sitelink = dom.new_tag('a', **{"href": f"{APP['sakai_url']}/portal/site/{SITE_ID}", "target":"_blank"})
            sitelink.string = SITE_ID
            site_title_tag.append(sitelink)

            # Sort the issues list
            found_items = list(filter(lambda i: i['is_found'] or isinstance(i['is_found'], list), config['issues']))
            sorted_items = sorted(found_items, key=lambda i: i['tool'] + i['description'])

            found_details = list(filter(lambda i: isinstance(i['is_found'], list), sorted_items))
            all_items = set()
            for detail in found_details:
                for set_items in detail['is_found']:
                    all_items.add(set_items)

            # Have issues
            issues_container = dom.find("div", {"id": "issues-container"})
            issues_banner = dom.find("div", {"id": "issues-banner"})
            issues_detail_banner = dom.find("div", {"id": "issues-details-banner"})
            issues_detail_container = dom.find("div", {"id": "issues-details-container"})

            # No issues
            no_issues_banner = dom.find("div", {"id": "no-issues-banner"})

            if sorted_items:
                # Remove the no issues banner
                no_issues_banner.decompose()

                # Use the issues banner and container div
                issues_desc = dom.find("span", {"id": "issues_desc"})
                issues_desc.string = f"{len(sorted_items)} issue(s) flagged in this site may need further attention"

                issues_list = dom.find("div", {"id": "issues_list"})
                if issues_list:
                    populate_issues(dom, issues_list, sorted_items, config, found_details)

                if found_details:
                    issues_details_desc = dom.find("span", {"id": "issues_details_desc"})
                    issues_details_desc.string = f"The {len(all_items)} item(s) listed below may need further attention"
                    issues_detail_list = dom.find("div", {"id": "issues_details_list"})
                    if issues_detail_list:
                        populate_issue_details(dom, issues_detail_list, found_details)
                else:
                    issues_detail_banner.decompose()
                    issues_detail_container.decompose()

            else:
                # Remove the issues banner
                issues_banner.decompose()
                issues_container.decompose()
                issues_detail_banner.decompose()
                issues_detail_container.decompose()

                # Use the no issues banner
                #issues_desc.string = "Good news! No issues were flagged for attention while converting this site."

            tool_used_list = dom.find("ol", {"id": "tool_used_list"})
            if tool_used_list:
                found_tools = list(filter(lambda i: i['is_found'], config['tools']))
                populate_tools(dom, tool_used_list, found_tools)

            with open(output_file, "w", encoding = 'utf-8') as file:
                file.write(str(dom.prettify()))
                logging.info(f'\treport-file: {output_file}')
                logging.info(f'\treport-url: {output_url}')

    except Exception as e:
        logging.exception(e)
        raise e

# check the issue if it was found or not
def do_check(step, **soups):
    func = globals()[ step['key'] ]
    args = project(soups, step['args'])

    returned = func(**args)
    if isinstance(returned, list):
        return returned
    return returned is not None


def process(conf, issue_key, SITE_ID, APP, link_id, now_st):
    site_folder = os.path.join(APP['archive_folder'], f"{SITE_ID}-archive/")
    rubric_folder = os.path.join(APP['output'], f"{SITE_ID}-rubrics/")
    output_file = os.path.join(APP['report']['output'], f"{SITE_ID}_report{now_st}.html")
    output_url = f"{APP['report']['url']}/{SITE_ID}_report{now_st}.html"
    sakai_url = APP['sakai_url']

    logging.debug("Setting up conversion report arguments")

    # soups used in this dish
    site_soup = init__soup(site_folder, "site.xml")

    if not site_soup:
        raise Exception(f"site.xml not found - archive for {SITE_ID} may be incomplete or missing")

    content_soup = init__soup(site_folder, "content.xml")
    attachment_soup = init__soup(site_folder, "attachment.xml")
    assignment_soup = init__soup(site_folder, "assignment.xml")
    discussions_soup = init__soup(site_folder, "messageforum.xml")
    samigo_soup = init__soup(site_folder, "samigo.xml")
    samigo_question_pools_soup = init__soup(site_folder, "samigo_question_pools.xml")
    lti_soup = init__soup(site_folder, "basiclti.xml")
    lessons_soup = init__soup(site_folder, "lessonbuilder.xml")
    gradebook_soup = init__soup(site_folder, "GradebookNG.xml")

    # restricted extensions
    restricted_ext = lib.utils.read_yaml(APP['content']['restricted-ext'])

    # ignored collections
    ignored_collections = ["attachment", APP['quizzes']['media_collection'], APP['qna']['collection']]

    # run through all the tools and see
    for k in conf['tools']:
        k['is_found'] = True if site_soup.find("tool", {"toolId": k['key']}) else False

    # only get active issues
    if issue_key:
        conf['issues'] = list(filter(lambda i: i['key'] == issue_key, conf['issues']))
        if not len(conf['issues']):
            raise Exception(f"issue key {issue_key} not found")
    else:
        conf['issues'] = list(filter(lambda i: i['active'], conf['issues']))

    for k in conf['issues']:

        if k['key'] in globals():
            logging.debug(f"Running check for {k['key']}")

            k['is_found'] = do_check(k, site_folder = site_folder,
                                        rubric_folder = rubric_folder,
                                        site_soup = site_soup,
                                        assignment_soup = assignment_soup,
                                        discussions_soup = discussions_soup,
                                        samigo_soup = samigo_soup,
                                        content_soup = content_soup,
                                        attachment_soup = attachment_soup,
                                        samigo_question_pools_soup = samigo_question_pools_soup,
                                        lti_soup = lti_soup,
                                        lessons_soup = lessons_soup,
                                        gradebook_soup = gradebook_soup,
                                        restricted_ext = restricted_ext,
                                        ignored_collections = ignored_collections,
                                        sakai_url = sakai_url)

            result = k['is_found']

            if issue_key:
                logging.info(f'Executed conversion check {issue_key} for site {SITE_ID}: {result}')
                return

    # general conversion report document
    html(APP, site_folder, output_file, output_url, conf, SITE_ID)

    # copy the report into the output folder for D2L content import (optional)
    output_folder = "{}/{}-content".format(APP['output'], SITE_ID)
    if not os.path.exists(output_folder):
        os.mkdir(output_folder)
    report_content_file = os.path.join(output_folder, "conversion_report.html")

    if APP['report']['upload']:
        # Copy it
        shutil.copy(output_file, report_content_file)
    else:
        # Remove it
        if os.path.exists(report_content_file):
            os.remove(report_content_file)

    # update properties in db
    mdb = lib.db.MigrationDb(APP)

    try:
        connection = pymysql.connect(**mdb.db_config, cursorclass=DictCursor)
        with connection:
            with connection.cursor() as cursor:
                # Update report url
                sql = "update `migration_site` set report_url = %s WHERE `site_id` = %s"
                ar = [f"{APP['report']['url']}/{SITE_ID}_report{now_st}.html", SITE_ID]
                if link_id is not None:
                    sql += " and `link_id` = %s"
                    ar.append(link_id)
                cursor.execute(sql, ar)

                # Remove properties
                sql = """delete from `migration_site_property` WHERE `site_id` = %s;"""
                cursor.execute(sql, (SITE_ID))

                # map issues to list of values to insert into DB
                for line in conf['issues']:
                    sql = "INSERT INTO `migration_site_property` (`site_id`, `key`, `found`) VALUES (%s, %s, %s);"
                    cursor.execute(sql, (SITE_ID, line['key'], 1 if line.get('is_found', None) else 0))

            connection.commit()

    except Exception as e:
        raise Exception(f'Could not set conversion properties : {SITE_ID}') from e

def run(SITE_ID, APP, issue_key = None, link_id = None, now_st = None):

    if now_st is None:
        now_st = ""
    else:
        now_st = f"_{now_st}"

    try:
        with open(APP['report']['json']) as json_file:
            process(conf=json.load(json_file), issue_key=issue_key, SITE_ID=SITE_ID, APP=APP, link_id=link_id, now_st=now_st)

    except IOError as io:
        raise Exception("Conversion report config file doesn't exist {}".format(APP['report']['json'])) from io

    except Exception as e:
        raise e

def main():
    APP = config.config.APP
    parser = argparse.ArgumentParser(description="This script generates a site conversion report",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument("ISSUE_KEY", nargs='?', help="The ISSUE_KEY")  # optional arg
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    if APP['debug']:
        config.logging_config.logger.setLevel(logging.DEBUG)

    run(SITE_ID=args['SITE_ID'], APP=APP, issue_key=args['ISSUE_KEY'])

if __name__ == '__main__':
    main()
