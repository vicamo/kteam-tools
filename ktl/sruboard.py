import os
import re
import yaml

from collections import namedtuple
from datetime import datetime, timezone, timedelta

from jira import JIRA
from jira.exceptions import JIRAError
# GreenHopperResource has been renamed to AgileResource in Jira 3.3.0, make
# sure to support both classes.
try:
    from jira.resources import AgileResource
except ImportError:
    from jira.resources import GreenHopperResource as AgileResource


class SRUBoardError(Exception):
    pass


class SRUBoard:
    def __init__(self, cycle, create_range=None, dryrun=False, cve=False):
        '''
        :param cycle: The cycle name for the sprint ([s]<YYYY.MM.DD>)
        :param create_range: Optionally pass in a tuple of (<start date>,<end date>) to
                             let a new sprint be created if not found. Both dates are
                             datetime objects.
        :param dryrun: If true, only simulate anything which would be done
        :param cve: If true, put the sprint into the security project, otherwise
                    use the SRU project.
        '''
        self.jira = JIRA('https://warthogs.atlassian.net/',
            options={'agile_rest_path': AgileResource.AGILE_BASE_REST_PATH})

        self.cycle = cycle
        self.dryrun = dryrun

        self.project_key = 'KSRU'
        if cve:
            self.project_key = 'KSEC'

        self.sprint_name = cycle

        self.board = self.jira.boards(projectKeyOrID=self.project_key, name='SRU Cycles')[0]
        for sprint in self.jira.sprints(board_id=self.board.id, state='active,future'):
            if sprint.name == cycle:
                self.sprint = sprint
                break
        else:
            if create_range is None:
                raise SRUBoardError("{}: cycle sprint not found".format(cycle))

            start_date, end_date = create_range
            try:
                start_date.replace(tzinfo=timezone.utc, microsecond=0)
                end_date.replace(tzinfo=timezone.utc, microsecond=0)
            except BaseException as ex:
                raise SRUBoardError("Failed to normalize start/end range ({})".format(ex))

            if not dryrun:
                self.sprint = self.jira.create_sprint(name=self.cycle, board_id=self.board.id, startDate=start_date.isoformat(), endDate=end_date.isoformat())
            else:
                self.sprint = 'DRY:{}'.format(self.cycle)

    def add_issue(self, name, desc=None, state=None, owner=None):
        """
        Add the given card to the board.

        :param name: card name
        :param desc: card description
        :param list_name: optional alternative target state
        :return: A Jira Issue resource.
        :rtype: Issue
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
            
            if owner is not None:
                self.jira.assign_issue(issue, owner)

        return issue

    def order_issue(self, issue, before):
        self.jira.rank(issue, before)

    LatestSpin = namedtuple("LatestSpin", ['spin', 'issue'])
    respin_re = re.compile(r"^Re-spin \(#([0-9]+)\) *(.*)?$")
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
