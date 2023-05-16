#!/usr/bin/python3

import sys
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from jira import JIRA
from jira import JIRAError

from lib.local_auth import *

## https://jira.readthedocs.io/examples.html
class MyJira(object):

    def __init__(self) -> None:        
        self._jira = None

        try:
            tmp = getAuth('Jira')
            if (tmp is not None):
                self._jira = JIRA(options={'server': tmp[0], 'verify' : False}, basic_auth=(tmp[1], tmp[2]))
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

def main():
    with MyJira() as j:
        # Who has authenticated
        myself = j.myself()
        print(myself)

        # test filter
        for i in j.getFilter(10641, 3):
            print(i.key)

        for i in j.getJQL('assignee = currentUser() AND resolution = Unresolved order by updated DESC'):
            print(i.key)

        fields = {
            'project': {'key': 'TSUG'},
            'summary': 'New issue from jira-python',
            'description': 'Look into this one',
            'issuetype': {'name': 'Task'}
        }

if __name__ == '__main__':
    main()
