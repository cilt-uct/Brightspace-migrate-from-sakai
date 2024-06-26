#!/usr/bin/python3

import os
import sys
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from jira import JIRA
from jira import JIRAError

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from lib.local_auth import getAuth

## Util methods
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
                key=fields['project']['key'], comment=fields['description'], site_id=fields['customfield_10001'])
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
