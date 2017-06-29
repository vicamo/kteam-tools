#!/usr/bin/python3

import re
import sys
from .utils                     import o2str
from datetime                   import datetime
from .tags                      import BugTags
from .attachments               import Attachments
from .person                    import Person
from .messages                  import Messages
from .nominations               import Nominations
from .bug_activity              import Activity

def fix_time(t):
    return t

# Bug
#
# A class that provides a convenient interface to a Launchpad bug.
#
class Bug(object):
    # __init__
    #
    # Initialize the Bug instance from a Launchpad bug.
    #
    def __init__(self, service, bug_number, commit_changes=True):
        self.service        = service
        launchpad           = service.launchpad
        self.lpbug          = launchpad.bugs[bug_number]
        self.id             = self.lpbug.id
        self.commit_changes = commit_changes

        # As defined in: https://wiki.canonical.com/UbuntuEngineering/DefectAnalysts/GravityHeuristics
        #
        self.tag_weights = {
            'apport-bug'         : 50,
            'apport-package'     : 100,
            'apport-crash'       : 100,
            'apport-kerneloops'  : 150,
            'regression-release' : 200,
            'regression-proposed': 250,
            'regression-updates' : 300,
            'iso-tracker'        : 300
        }
        # Cached copies so we don't go back to launchpad as often
        #
        self.__activity                   = None
        self.__attachments                = None
        self.__date_created               = None
        self.__date_last_message          = None
        self.__date_last_updated          = None
        self.__date_latest_patch_uploaded = None
        self.__description                = None
        self.__duplicate_of               = None
        self.__gravity                    = None
        self.__heat                       = None
        self.__nominations                = None
        self.__owner                      = None
        self.__private                    = None
        self.__properties                 = None
        self.__releases                   = None
        self.__security_related           = None
        self.__tags                       = None
        self.__title                      = None
        self.__users_affected_count       = None
        self.__users_unaffected_count     = None

    #--------------------------------------------------------------------------
    # date_created / age
    #
    # (read-only)
    #
    @property
    def date_created(self):
        if self.__date_created is None:
            self.__date_created = fix_time(self.lpbug.date_created)
        return self.__date_created

    def age(self):
        ''' Age of bug in days '''
        dlm = self.date_created
        now = dlm.now(dlm.tzinfo)
        return (now - dlm).days

    #--------------------------------------------------------------------------
    # date_last_updated / age_last_updated
    #
    # (read-only)
    #
    @property
    def date_last_updated(self):
        if self.__date_last_updated is None:
            self.__date_last_updated = fix_time(self.lpbug.date_last_updated)
        return self.__date_last_updated

    def age_last_updated(self):
        ''' Age of last update to bug in days '''
        dlm = self.date_last_updated
        now = dlm.now(dlm.tzinfo)
        return (now - dlm).days

    #--------------------------------------------------------------------------
    # date_last_message / age_last_message
    #
    # (read-only)
    #
    @property
    def date_last_message(self):
        if self.__date_last_message is None:
            self.__date_last_message = fix_time(self.lpbug.date_last_message)
        return self.__date_last_message

    def age_last_message(self):
        ''' Age of last comment to bug in days '''
        dlm = self.date_last_message
        now = dlm.now(dlm.tzinfo)
        return (now - dlm).days

    #--------------------------------------------------------------------------
    # private
    #
    # (read-only)
    #
    @property
    def private(self):
        if self.__private is None:
            self.__private = self.lpbug.private
        return self.__private

    # private
    #
    # (read-only)
    #
    @private.setter
    def private(self, value):
        self.lpbug.private = value
        if self.commit_changes:
            self.lpbug.lp_save()
        self.__private = value
        return

    #--------------------------------------------------------------------------
    # security_related
    #
    # (read-only)
    #
    @property
    def security_related(self):
        if self.__security_related is None:
            self.__security_related = self.lpbug.security_related
        return self.__security_related

    # security_related
    #
    # (read-only)
    #
    @security_related.setter
    def security_related(self, value):
        self.lpbug.security_related = value
        if self.commit_changes:
            self.lpbug.lp_save()
        self.__security_related = value
        return

    #--------------------------------------------------------------------------
    # title
    #
    @property
    def title(self):
        '''A one-line summary of the problem being described by the bug.'''
        if self.__title is None:
            self.__title = o2str(self.lpbug.title)
        return self.__title

    @title.setter
    def title(self, value):
        if not isinstance(value, str):
            raise TypeError("Must be a string")
        self.lpbug.title = value
        if self.commit_changes:
            self.lpbug.lp_save()
        self.__title = value

    #--------------------------------------------------------------------------
    # description
    #
    @property
    def description(self):
        '''As complete as possible description of the bug/issue being reported as a bug.'''
        if self.__description is None:
            self.__description = o2str(self.lpbug.description)
        return self.__description

    @description.setter
    def description(self, value):
        if not isinstance(value, str):
            raise TypeError("Must be a string")
        self.lpbug.description = value
        if self.commit_changes:
            self.lpbug.lp_save()
        self.__description = value

    #--------------------------------------------------------------------------
    # tags
    #
    @property
    def tags(self):
        return BugTags(self)

    #--------------------------------------------------------------------------
    # releases - List of Ubuntu releases tagged as being affected
    #
    @property
    def releases(self):
        if self.__releases is None:
            self.__releases = []

            ubuntu_releases = []
            d = self.service.launchpad.distributions['ubuntu']
            for s in d.series:
                ubuntu_releases.append("%s" %(s.name))

            for bug_tag in self.tags:
                tag = o2str(bug_tag)
                if tag in ubuntu_releases:
                    self.__releases.append(tag)
        return self.__releases

    #--------------------------------------------------------------------------
    # owner
    #
    @property
    def owner(self):
        if self.__owner is None:
            self.__owner = Person(self, self.lpbug.owner)
        return self.__owner

    @property
    def owner_name(self):
        if self.owner is not None:
            return o2str(self.owner.username)
        else:
            return None

    #--------------------------------------------------------------------------
    # attachments
    #
    @property
    def attachments(self):
        return Attachments(self)

    #--------------------------------------------------------------------------
    # properties
    #
    @property
    def properties(self):
        '''Returns dict of key: value pairs found in the bug description

        This parses the bug report description into a more
        programmatically digestable dictionary form.
        '''
        if self.__properties is None:
            re_kvp            = re.compile("^(\s*)([\.\-\w]+):\s*(.*)$")
            re_error          = re.compile("^Error:\s*(.*)$")
            self.__properties = {}
            last_key = {'': 'bar'}
            for line in self.description.split("\n"):
                m = re_kvp.match(line)
                if not m:
                    continue

                level = m.group(1)
                item = m.group(2)
                value = m.group(3)
                key = item

                if len(level) > 0:
                    key = "%s.%s" %(last_key[''], item)
                last_key[level] = item

                m = re_error.match(value)
                if not m:
                    self.__properties[key] = value

        return self.__properties

    #--------------------------------------------------------------------------
    # messages
    #
    @property
    def messages(self):
        return Messages(self)

    @property
    def messages_count(self):
        return len(self.messages)

    #--------------------------------------------------------------------------
    # tasks
    #
    @property
    def tasks(self):
        # The following import is done here to work around a circular import
        # issue. bug_tasks imports bug.
        #
        from .bug_tasks import BugTasks

        return BugTasks(self.service, self.lpbug.bug_tasks_collection)

    #--------------------------------------------------------------------------
    # add_comment
    #
    def add_comment(self, content, subject=None, avoid_dupes=False):
        '''Add a new comment to an existing bug.

        This is the equivalent of newMessage.  If no subject is provided,
        it will craft one using the bug title.  If avoid_dupes is set, the
        routine will check to see if this comment has already been posted,
        to avoid accidentally spamming; the routine will return False in
        this case.
        '''
        if avoid_dupes:
            # TODO: Actually only need to consider the last ~40 messages
            for m in self.lpbug.messages:
                if m.content == content:
                    return False
        self.lpbug.newMessage(content=content, subject=subject)
        return True

    #--------------------------------------------------------------------------
    # nominations
    #
    @property
    def nominations(self):
        return Nominations(self.service, self)

    # add a nomination
    #
    def add_nomination(self, series):
        self.lpbug.addNomination(target=series)

    #--------------------------------------------------------------------------
    # activity
    #
    @property
    def activity(self):
        return Activity(self.service, self)

    # duplicate_of
    #
    @property
    def duplicate_of(self):
        if self.__duplicate_of is None:
            self.__duplicate_of = self.lpbug.duplicate_of
        return self.__duplicate_of

    # duplicates_count
    @property
    def duplicates_count(self):
        return self.lpbug.number_of_duplicates

    # subscriptions_count
    @property
    def subscriptions_count(self):
        return len(list(self.lpbug.subscriptions))

    # heat
    #
    @property
    def heat(self):
        if self.__heat is None:
            self.__heat = self.lpbug.heat
        return self.__heat

    # date_latest_patch_uploaded
    #
    @property
    def date_latest_patch_uploaded(self):
        if self.__date_latest_patch_uploaded is None:
            self.__date_latest_patch_uploaded = self.lpbug.latest_patch_uploaded
        return self.__date_latest_patch_uploaded

    # has_patch
    #
    def has_patch(self):
        if self.date_latest_patch_uploaded is None:
            return False
        return True

    # is_expirable
    #
    def is_expirable(self, days_old=None):
        return self.lpbug.isExpirable(days_old=days_old)

    #--------------------------------------------------------------------------
    # users (un)affected
    #
    @property
    def users_affected_count(self):
        if self.__users_affected_count is None:
            self.__users_affected_count = self.lpbug.users_affected_count
        return self.__users_affected_count

    @property
    def users_unaffected_count(self):
        if self.__users_unaffected_count is None:
            self.__users_unaffected_count = self.lpbug.users_unaffected_count
        return self.__users_unaffected_count

    #--------------------------------------------------------------------------
    # gravity
    #
    def gravity(self):
        '''
        An implementation of the "gravity" value as defined at:
            https://wiki.canonical.com/UbuntuEngineering/DefectAnalysts/GravityHeuristics
        '''
        if self.__gravity is None:
            self.__gravity = (6 * self.duplicates_count +
                              4 * self.subscriptions_count +
                              2 * self.users_affected_count)

            # Add the weights associated with certain tags.
            #
            for tag in self.tags:
                try:
                    self.__gravity += self.tag_weights[tag]
                except KeyError:
                    pass # Just ignore any tags on the bug that we don't have a weight for

        return self.__gravity

    def to_dict(self, quick=False):
        '''Converts the bug to a serializable dict.

        Specify quick=True to skip data which can be more expensive to
        look up.  Execution should be about twice as fast.
        '''
        data = {
            'id': self.id,
            'title': self.title,
            'duplicate_of': self.duplicate_of,
            'date_created': o2str(self.date_created),
            'age': self.age(),
            'date_last_updated': o2str(self.date_last_updated),
            'age_last_updated': self.age_last_updated(),
            'date_last_message': o2str(self.date_last_message),
            'age_last_message': self.age_last_message(),
            'date_latest_patch_uploaded': o2str(self.date_latest_patch_uploaded),
            'gravity': self.gravity(),
            'heat': self.heat,
            'tags': o2str(list(self.tags)),
            'description': self.description,
            'properties': self.properties,
            }
        if not quick:
            # These items are a bit more heavy; omit them for better performance
            details = {
                # Costs about 20%
                'has_patch': self.has_patch(),
                'private': self.private,
                'security_related': self.security_related,
                'is_expirable': self.is_expirable(),

                # Cost about 20%
                'messages_count': self.messages_count,
                'duplicates_count': self.duplicates_count,
                'subscriptions_count': self.subscriptions_count,
                'users_affected_count': self.users_affected_count,
                'users_unaffected_count': self.users_unaffected_count,

                # Costs 15%
                'owner_name': self.owner_name,

                # Costs 80%!
                'releases': self.releases,
                }
            data.update(details)
        return data

# vi:set ts=4 sw=4 expandtab:
