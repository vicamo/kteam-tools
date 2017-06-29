#!/usr/bin/python3

import os
import sys
import json
import httplib2
import launchpadlib
from launchpadlib.launchpad     import *
from .debug                     import *
from .bug                       import Bug
from .distributions             import Distributions
from .projects                  import Projects
from .person                    import Person

class LaunchpadServiceError(Exception):
    """LaunchpadServiceError

    An exception class that will be raised if there are any errors initializing
    a LaunchpadService instance.
    """

    # __init__
    #
    def __init__(self, error):
        self.msg = error

class LaunchpadService:
    """
    Manages connection to Launchpad services.
    """

    def __init__(self, config=None):
        """Initialize the Arsenal instance.

        The user's configuration (if one exists) is loaded and
        incorporated into the standard options. Access to Launchpad is
        initialized.

        Configuration values to override can be passed in through config.
        For example:

        lp = LaunchpadService(config={
                'launchpad_services_root': 'edge',
                'read_only':               True
                })

        lp = LaunchpadService(config={
                'launchpad_client_name':   'my-lpltoolkit-project',
                'launchpad_services_root': 'https://api.launchpad.dev'
                })

        lp = LaunchpadService(config={
                'launchpad_version':       '1.0',
                'bot':                     True
                })
        """

        self.project = None

        # Setting LPLTK_DEBUG environment variable enables debug messages in this
        # class and in httplib2 as well.
        #
        if "LPLTK_DEBUG" in os.environ:
            httplib2.debuglevel = os.getenv("LPLTK_DEBUG", None)
            sys.stdout = DebugStdOut()

        # Default configuration parameters
        #
        self.config = {}
        self.config['launchpad_client_name']   = 'lpltk'
        self.config['launchpad_services_root'] = 'production' # 'staging' 'edge' 'production'
        self.config['project_name']            = ''
        self.config['bot']                     = False
        self.config['read_only']               = False        # FIXME: 'read_only' doesn't seem very descriptive here.
        self.config['launchpad_version']       = 'devel'

        # The configuration dictionary which is ~/.lpltkrc will override the
        # default configuration parameters.
        #
        self._load_user_config()

        # The config dictionary passed into this method override all config parameters.
        #
        if config != None:
            for k in config.keys():
                self.config[k] = config[k]

        # So that we can use any change a user may have made via their
        # config file, we need to set the 'launchpad_cachedir' and
        # 'launchpad_creddir' after loading the user's config file.
        #
        if 'launchpad_cachedir' not in self.config:
            self.config['launchpad_cachedir'] = os.path.join(os.path.expanduser('~'),
                                                             '.cache',
                                                             self.config['launchpad_client_name'])
        if 'launchpad_creddir' not in self.config:
            self.config['launchpad_creddir']  = os.path.join(os.path.expanduser('~'),
                                                             '.config',
                                                             self.config['launchpad_client_name'])

        if self.config['launchpad_services_root'] == 'qastaging':
            self.config['launchpad_services_root'] = 'https://api.qastaging.launchpad.net'

        if self.config['launchpad_creddir']:
            filename_parts = [
                'credentials',
                self.config['launchpad_services_root'].replace('/','_')
                ]
            if self.config['bot']:
                filename_parts.insert(0, 'bot')
            self.config['launchpad_credentials_file'] = os.path.join(
                self.config['launchpad_creddir'],
                '-'.join(filename_parts))

            if not os.path.exists(self.config['launchpad_creddir']):
                os.makedirs(self.config['launchpad_creddir'], 0o700)

        self.reset()
        return

    def reset(self):
        """
        Re-establish access to Launchpad and reload the specific project if one is
        specified.
        """
        dbg("Launchpadlib Version: %s" %(launchpadlib.__version__))
        dbg("Login With:  %s %s %s" %(self.config['launchpad_client_name'],
                                      self.config['launchpad_services_root'],
                                      self.config['launchpad_credentials_file']))
        dbg("Read Only:  %s" %(self.config['read_only']))
        dbg("Bot:  %s" %(self.config['bot']))

        try:
            if self.config['read_only']:
                self.launchpad = Launchpad.login_anonymously(
                    self.config['launchpad_client_name'],
                    service_root=self.config['launchpad_services_root'],
                    version=self.config['launchpad_version'])
            else:
                self.launchpad = Launchpad.login_with(
                    self.config['launchpad_client_name'],
                    service_root=self.config['launchpad_services_root'],
                    launchpadlib_dir=self.config['launchpad_cachedir'],
                    credentials_file=self.config['launchpad_credentials_file'],
                    version=self.config['launchpad_version'])
            if self.config['project_name'] != '':
                self.load_project(self.config['project_name'])
        except:
            # Eventually, it would be nice if this handled LP exceptions and gave more helpful
            # error messages. But for now it should just raise what it's given.
            #
            raise
        return

    # get_bug
    #
    def get_bug(self, bug_number):
        return Bug(self, bug_number)

    # get_launchpad_bug
    #
    def get_launchpad_bug(self, bug_number):
        """ Fetch a Launchpad bug object for a specific Launchpad bug id. """
        return self.launchpad.bugs[bug_number]

    def load_project(self, project):
        """ Connect to a specific Launchpad project. """
        try:
            self.project = self.launchpad.projects[project]
        except KeyError:
            raise LaunchpadServiceError("%s is not a recognized Launchpad project." % (project))
        if self.project is None:
            try:
                self.project = self.launchpad.distributions[project]
            except KeyError:
                raise LaunchpadServiceError("%s is not a recognized Launchpad distribution." % (project))
        self.config['project_name'] = project
        return self.project

    def person(self, name):
        """ Get a Person by the given name. """
        try:
            person = Person(None, self.launchpad.people[name])
        except KeyError:
            raise LaunchpadServiceError("%s is not a person or team in Launchpad." % (name))
        return person

    def get_team_members(self, team):
        """ Get the direct members of a Launchpad team. """
        try:
            self.team = self.launchpad.people[team]
        except KeyError:
            raise LaunchpadServiceError("%s is not a person or team in Launchpad." % (team))
        if self.team.is_team is False:
            raise LaunchpadServiceError("%s is not a team so has no members." % (team))
        return self.team.participants

    def _load_user_config(self):
        """ Load configuration from ~/.lpltkrc

        If the users home directory contains a configuration file, load that in. The
        name of the configuration file is '.lpltkrc'. The format of the file is
        json. The json format should be an array. The contents of that array will
        be merged with the default one 'self.config' in this class.
        """
        if 'configuration_file' in self.config:
            cfg_path = self.config['configuration_file']
        else:
            cfg_path = os.path.join(os.path.expanduser('~'), ".lpltkrc")
        if os.path.exists(cfg_path):
            with open(cfg_path, 'r') as f:
                user_config = json.load(f)
            for k in user_config.keys():
                self.config[k] = user_config[k]

    #--------------------------------------------------------------------------
    # distributions
    #
    @property
    def distributions(self):
        return Distributions(self)

    #--------------------------------------------------------------------------
    # projects
    #
    @property
    def projects(self):
        return Projects(self)

    #--------------------------------------------------------------------------
    # create_bug
    #
    #    Create a new, launchpad bug.
    #
    def create_bug(self, project, package, title, description, tags=[], private=False):
        proj    = self.projects[project]
        target  = self.launchpad.load(proj.self_link + "/+source/" + package)
        lp_bug = self.launchpad.bugs.createBug(target=target, title=title, description=description, tags=[], private=private)
        return self.get_bug(lp_bug.id)

# vi:set ts=4 sw=4 expandtab:
