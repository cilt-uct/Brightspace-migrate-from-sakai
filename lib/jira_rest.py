#!/usr/bin/python3

import os
import sys
import urllib3
import datetime
import logging
import json
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from jira import JIRA
from jira import JIRAError

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from lib.local_auth import getAuth

## Util methods
def create_jira(APP, url, site_id, site_title, jira_state, jira_log, failure_type: str = None, failure_detail: str = None, user: str = None):
    now = datetime.datetime.now()
    jira_date_str = now.strftime("%a, %-d %b %-y %H:%M")

    try:
        jira_log = json.loads(jira_log)
        if APP['jira']['last'] > 0:
            N = APP['jira']['last']
            jira_log = jira_log[-N:]
    except (TypeError, ValueError):
        pass

    if isinstance(jira_log, list):
        jira_log_str = "\n".join(jira_log)
    else:
        jira_log_str = jira_log

    sakai_url = APP['sakai_url']
    site_msg = f'+SITE:+ {site_id}\n'
    link_msg = f'+LINK:+ {sakai_url}/portal/site/{url}\n'
    fail_type_msg = f'+FAILURE TYPE:+ {failure_type}\n'
    fail_detail_msg = f'+FAILURE DETAIL:+ {failure_detail}\n'
    started_by = f'+STARTED-BY:+ {user if user else "Unknown"}\n\n'
    log_msg = f'+LOG:+\n{{noformat}}\n{jira_log_str}\n{{noformat}}'

    with MyJira() as j:
        fields = {
            'project': {'key': APP['jira']['key']},
            'summary': "{} {} {} {}".format(APP['jira']['prefix'], site_title, jira_date_str, " [Expired]" if jira_state == 'expire' else ''),
            'description': site_msg + link_msg + fail_type_msg + fail_detail_msg + started_by + log_msg,
            'issuetype': {'name': 'Task'},
            'customfield_10053': str(site_id),
            'labels': []
        }

        if jira_state == 'expire':
            fields['labels'].append('expire')

        if site_id in url:
            fields['labels'].append('self-service')

        logging.debug(f"Creating JIRA issue: {fields}")

        try:
            response = j.createIssue(fields)
        except Exception as e:
            logging.error("Unable to create JIRA issue")
            logging.exception(e)

        if response is not None:
            logging.debug("Created JIRA issue")
            return True

    return False

def close_jira(APP, site_id, comment):
    with MyJira() as j:
        fields = {
            'project': {'key': APP['jira']['key']},
            'site_id': str(site_id),
            'comment': str(comment)
        }

        j.closeIssue(fields)


## https://jira.readthedocs.io/examples.html
class MyJira(object):

    def __init__(self) -> None:
        self._jira = None

        try:
            JIRA_AUTH = getAuth('Jira', ['url', 'username', 'password'])
            if JIRA_AUTH['valid']:
                self._jira = JIRA(options={'server': JIRA_AUTH['url'], 'verify' : False}, basic_auth=(JIRA_AUTH['username'], JIRA_AUTH['password']))
        except JIRAError:
            self._jira = None

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        # We don't have to disconnect to JIRA REST as the session just expires
        # print("args: ", args)
        # print("kwargs: ", kwargs)
        pass


    def myself(self):
        if self._jira:
            return self._jira.myself()

        return None

    def getFilter(self, filter, maxResults = 0):
        if self._jira:
            kwargs = {}
            if maxResults > 0:
                kwargs['maxResults'] = maxResults
            return self._jira.search_issues(f'filter={filter}', **kwargs)

        return None

    def getJQL(self, jql, maxResults = 0):
        if self._jira:
            kwargs = {}
            if maxResults > 0:
                kwargs['maxResults'] = maxResults
            return self._jira.search_issues(jql, **kwargs)

        return None

    ## Manage issues
    # Get issue by key
    def getIssue(self, key):
        if self._jira:
            return self._jira.issue(key)
        return None

    # Create issue
    def createIssue(self, fields):
        if self._jira:
            update_issue = self.updateIssue(
                key=fields['project']['key'], comment=fields['description'], site_id=fields['customfield_10053'])
            if update_issue is None:
                return self._jira.create_issue(fields=fields)
            return update_issue
        return None

    def updateIssue(self, key, comment, site_id):
        if self._jira:
            issue = self.getJQL(jql=f'project={key} AND summary~"Migration ERR" AND "Site ID"~"{site_id}"', maxResults=1)
            if issue is not None and issue.total > 0:
                self._jira.add_comment(issue=issue[0].id, body=comment)
                self._jira.transition_issue(issue=issue[0].id, transition='11')
                return issue[0]
            return None

    def closeIssue(self, fields):
        if self._jira:
            key = fields['project']['key']
            site_id = fields['site_id']
            comment = fields['comment']
            issue = self.getJQL(jql=f'project={key} AND summary~"Migration ERR" AND "Site ID"~"{site_id}"', maxResults=1)
            if issue is not None and issue.total > 0:
                self._jira.add_comment(issue=issue[0].id, body=comment)
                self._jira.transition_issue(issue=issue[0].id, transition='31')

    def setToInProgressIssue(self, fields):
        if self._jira:
            key = fields['project']['key']
            site_id = fields['site_id']
            comment = fields['comment']
            issue = self.getJQL(jql=f'project={key} AND summary~"Migration ERR" AND "Site ID"~"{site_id}"', maxResults=1)
            if issue is not None and issue.total > 0 and issue[0].get_field('status') != 'In Progress':
                self._jira.add_comment(issue=issue[0].id, body=comment)
                self._jira.transition_issue(issue=issue[0].id, transition='21')
