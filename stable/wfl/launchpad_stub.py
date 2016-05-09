from ktl.ubuntu                         import Ubuntu
from datetime                           import date

import yaml

class AssigneeStub():
    def __init__(s, assignee):
        s.display_name = assignee

class BugTaskStub(object):
    '''
    Class to hold information regarding a bug task, including it's current state
    and attributes.
    '''
    def __init__(s, task, attr, bug):
        s.bug_target_name = task
        s.status = attr['initial-status']
        s.importance = attr['initial-importance']
        s.__assignee = AssigneeStub(attr['initial-assignee'])
        s.attr = attr
        s.bug = bug

    # assignee
    #
    @property
    def assignee(s):
        return s.__assignee

    @assignee.setter
    def assignee(s, val):
        s.__assignee = AssigneeStub(val)

class BugStub():
    '''
    Class to hold information related to a tracking bug, and a list of the bug
    tasks.
    '''
    def __init__(s, bugid, title, config):
        s.bugid = bugid
        s.id = bugid
        s.title = title
        s.config = config
        s.properties = []
        for bug in s.config['bugs']:
            b = s.config['bugs'][bug]
            if b['bugid'] == bugid:
                s.init_tasks(b['tasks'])

    def init_tasks(s, tasks):
        s.tasks = []
        for t in tasks:
            s.tasks.append(BugTaskStub(t, tasks[t], s))

class TaskStub():
    '''
    Class to hold info regarding a bug_task (currently only the actual bug)
    '''
    def __init__(s, bugid, title, config):
        s.config = config
        s.bug = BugStub(bugid, title, s.config)

class ProjectStub():
    '''
    Class to hold information regarding a LP Project
    (kernel-development-workflow' or 'kernel-sru-workflow).  It will be used to
    hold the list of bugs associated with the project.
    '''
    def __init__(s, project, config):
        s.project = project
        s.config = config
        s.tasks = []
        # load all the bugs associated to this project
        for b in s.config['bugs']:
            bug = s.config['bugs'][b]
            if bug['project'] == s.project:
                t = TaskStub(bug['bugid'], bug['title'], s.config)
                s.tasks.append(t)

    def search_tasks(s, status, tags, tags_combinator, modified_since):
        return s.tasks

    def get_bug(s, bugid):
        for t in s.tasks:
            if t.bug.id == bugid:
                return t.bug
        return None

class PublishedSourcesStub():
    '''
    Class to hold the build results
    '''
    def __init__(s, distro_series, pocket, source_name, version):
        s.distro_series = distro_series
        s.pocket = pocket
        s.source_name = source_name
        s.source_package_version = version
        s.abi_only = False
        if s.source_package_version == None:
            s.abi_only = True
        s.is_built = False
        s.date_published = date.today()
        s.index = 0
        # s.self is used to get the src ID of a build, and this test framework
        # will always assume it is 0.  It is built using:
        #   str(pkg.self).rsplit('/', 1)[1]
        s.self = "0/0"
    def __iter__(s):
        return s
    def next(s):
        if s.is_built == False or s.index == 0:
            raise StopIteration
        s.index = s.index - 1
        return s
    def add(s, pocket, pkg):
        s.source_package_version = pkg['version'] # in case it's ABI only, keep the version
        s.status = pkg['status']
        s.package_creator = pkg['creator']
        s.package_signer = pkg['signer']
        s.is_built = True
        s.index = 1

class PPAStub():
    '''
    PPA stub.  The main goal of this class is to return a fake list of packages
    builds.
    '''
    def __init__(s, name, config):
        s.name = name
        s.config = config
        s.ps = None

    def getPublishedSources(s, distro_series, exact_match, source_name, status, version=None, pocket='PPA'):
        '''
        Return list of builds for package 'source_name'.  The builds are stored
        in the YAML file, and it is assumed that only a build is available
        (although the object returned needs to be iterable).
        '''
        ps = PublishedSourcesStub(distro_series, pocket, source_name, version)
        for p in s.config['builds']:
            if p == source_name:
                pkg = s.config['builds'][p]
                # check if pocket and series are correct...
                if pocket in pkg['pocket'] and distro_series.name == pkg['series']:
                    # ... and if version is 'None', it means we just care about
                    # the ABI, so just return it, and let the caller decide.
                    if version == None or version == pkg['version']:
                        ps.add(pocket, pkg)
        s.ps = ps
        return ps
    def getBuildSummariesForSourceIds(s, source_ids):
        # just ignore sources_ids, which shall *always* be 0
        return {"0": {'status': s.ps.status}}

class SeriesCollectionStub():
    '''Just an object to old a series'''
    def __init__(s, series):
        s.name = series

class LpPeoplePpaDistributionsStub():
    '''
    *VERY* generic class that will mimic several LP objects (in the future this
    may need to be split into different classes).  For example, it will mimic
    people, PPA, and distributions.  A mess!
    '''
    def __init__(s, config):
        s.config = config
        s.ubuntu = Ubuntu()
        s.main_archive = PPAStub('main-archive', s.config)
        s.people = {'canonical-kernel-team': s}
        s.distributions = {'ubuntu': s}

        # Get a list of series
        s.series_collection = []
        for n in s.ubuntu.index_by_series_name.keys():
            s.series_collection.append(SeriesCollectionStub(n))

    def getPPAByName(s, name):
        return PPAStub(name, s.config)

class LaunchpadStub():
    '''
    A test class that shall be used for testing purposes only.  It stubs the
    services provided by LP required in shankbot.
    These services shall be configured through YAML files, passed into this
    class constructor.
    '''
    def __init__(s, args):
        s.args = args
        s.args.lp = s
        s.production_service = s
        s.default_service = s

        # Read testcase file
        with open(args.testcase, 'r') as f:
            s.config = yaml.safe_load(f)

        # Get the projects list.  Only kernel-development-workflow and
        # kernel-sru-workflow are expected at the moment.
        s.projects = {}
        for p in s.config['projects']:
            s.projects[p] = ProjectStub(p, s.config)

        s.launchpad = LpPeoplePpaDistributionsStub(s.config)

    def get_bug(s, bugid):
        for p in s.projects:
            b = s.projects[p].get_bug(bugid)
            if b != None:
                return b
        return None

    def bug_url(s, bug_id):
        retval = 'https://bugs.launchpad.net/bugs/%s' % (bug_id)
        return retval
