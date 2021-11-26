import os
import re
import yaml

from collections import namedtuple
from datetime import datetime, timezone, timedelta

from jira import JIRA
from jira.exceptions import JIRAError
from jira.resources import GreenHopperResource


class SRUBoardError(Exception):
    pass


class SRUBoard:
    def __init__(self, cycle, create_sprint=False, dryrun=False):
        '''
        :param cycle: The SRU cycle date of the board
        '''
        self.jira = JIRA('https://warthogs.atlassian.net/',
            options={'agile_rest_path': GreenHopperResource.AGILE_BASE_REST_PATH})

        self.cycle = cycle
        self.dryrun = dryrun

        self.project_key = 'KSRU'
        self.sprint_name = cycle

        self.board = self.jira.boards(projectKeyOrID=self.project_key, name='SRU Cycles')[0]
        for sprint in self.jira.sprints(board_id=self.board.id, state='active,future'):
            if sprint.name == cycle:
                self.sprint = sprint
                break
        else:
            if not create_sprint:
                raise SRUBoardError("{}: cycle sprint not found".format(cycle))

            start_date = datetime.strptime(self.cycle, '%Y.%m.%d').replace(tzinfo=timezone.utc, microsecond=0)
            end_date = start_date + timedelta(days=21)
            self.sprint = self.jira.create_sprint(name=self.cycle, board_id=self.board.id, startDate=start_date.isoformat(), endDate=end_date.isoformat())

    def add_issue(self, name, desc=None, state=None):
        """
        Add the given card to the board.

        :param name: card name
        :param desc: card description
        :param list_name: optional alternative target state
        :return: None
        """

        params = {
            'project': {'key': self.project_key},
            'summary': name,
            'issuetype': {'name': 'Task'},
        }
        if desc is not None:
            params['description'] = desc

        issue = None
        if self.dryrun:
            print('DRY: Add "{}" issue in "{}"'.format(name, state))
            if desc:
                print('DRY:     "{}"'.format(desc))
        else:
            issue = self.jira.create_issue(fields=params)
            print('Added respin: {} ({})'.format(name, issue.permalink()))
            self.jira.add_issues_to_sprint(sprint_id=self.sprint.id, issue_keys=[issue.key])
            if state is not None:
                self.jira.transition_issue(issue, transition=state)

        return issue

    def order_issue(self, issue, before):
        self.jira.rank(issue, before)

    LatestSpin = namedtuple("LatestSpin", ['spin', 'issue'])
    respin_re = re.compile("^Re-spin \(#([0-9]+)\) *(.*)?$")
    def get_latest_spin(self):
        '''
        Get all respin issues from the project.

        :returns: list()
        '''
        latest = 0
        latest_issue = None
        chunk_offset = 0
        chunk_size = 50
        while True:
            issues = self.jira.search_issues('project="{}" and sprint={} and summary~"Re-spin #"'.format(self.project_key, self.sprint.id), startAt=chunk_offset, maxResults=chunk_size)
            chunk_offset += chunk_size
            if len(issues) == 0:
                break

            for issue in issues:
                title = issue.fields.summary
                match = self.respin_re.match(title)
                if not match:
                    continue
                print("Existing respin: {} ({})".format(issue.fields.summary, issue))
                this_spin = int(match.group(1))
                if this_spin > latest:
                    latest = this_spin
                    latest_issue = issue

        print("Latest respin: {} ({})".format(latest, latest_issue))
        return self.LatestSpin(latest, latest_issue)
