#!/usr/bin/env python
#

# An engine for processing bugs. The idea is to have a small config file, one
# element of which is a time-stamp of when the last time the engine ran looking for
# changes to LP bugs.
#

from sys                                import argv, exit
from datetime                           import datetime
from datetime                           import timedelta
import json

from lpltk.LaunchpadService             import LaunchpadService
from ktl.utils                          import error, date_to_string, string_to_date, stdo, json_load, FileDoesntExist
from ktl.std_app                        import StdApp
#from ktl.ubuntu                         import Ubuntu
from ktl.kernel_bug                     import KernelBug
from ktl.termcolor                      import colored
from bug_handler                        import BugHandler
from dbg                                import Dbg

from cmdline                            import Cmdline, CmdlineError

# BugEngineError
#
class BugEngineError(Exception):
    # __init__
    #
    def __init__(self, error):
        Dbg.enter("BugEngineError.__init__")
        self.msg = error
        Dbg.leave("BugEngineError.__init__")

# BugEngine
#
class BugEngine(StdApp):
    # __init__
    #
    def __init__(self, default_config={}, cmdline=None):
        Dbg.enter("BugEngine.__init__")

        self.defaults = default_config
        self.defaults['show'] = False
        self.defaults['search_all'] = False
        StdApp.__init__(self)
        self.bdb = None
        if cmdline is None:
            self.cmdline = Cmdline()
        else:
            self.cmdline = cmdline

        self.show_buff = ''

        Dbg.leave("BugEngine.__init__")

    # __initialize
    #
    # A separate initialize that we can control when it gets called (not
    # when the object is instantiated).
    #
    def __initialize(self):
        Dbg.enter("BugEngine.__initialize")

        #self.ubuntu = Ubuntu()

        Dbg.verbose('Connecting to LaunchPad')
        if 'staging' in self.cfg:
            Dbg.verbose(' (qastaging)')
            self.defaults['launchpad_services_root'] = 'qastaging'
        else:
            Dbg.verbose(' (production)')
        Dbg.verbose(' ... ')
        self.lp = LaunchpadService(self.defaults)
        Dbg.verbose('connected.\n')

        # The service.distributions property is a collection of distributions. We
        # pretty much only care about one, 'ubuntu'.
        #
        self.distro = self.lp.distributions['ubuntu']

        if 'debug' in self.cfg and 'kbug' in self.cfg['debug']:
            KernelBug.debug = True

        if 'sru_data_file' in self.cfg:
            try:
                self.cfg['sru_data'] = json_load(self.cfg['sru_data_file'])
            except FileDoesntExist as e:
                e.print_std_error()

        Dbg.leave("BugEngine.__initialize")
        return

    # startup
    #
    def startup(self):
        """
        Performs tasks that need to be done before "main" is run.
        """
        Dbg.enter("BugEngine.startup")
        Dbg.leave("BugEngine.startup")
        return

    # shutdown
    #
    def shutdown(self):
        """
        Performs any cleanup tasks.
        """
        Dbg.enter("BugEngine.shutdown")

        if self.bdb is not None:
            self.cfg['bugs_database'] = self.bdb
            if 'update-config' in self.cfg and self.cfg['update-config']:
                with open(self.cfg['configuration_file'], 'w') as f:
                    f.write(json.dumps(self.cfg, sort_keys=True, indent=4))

        Dbg.leave("BugEngine.shutdown")
        return

    # run
    #
    def run(self):
        Dbg.enter("BugEngine.run")

        using_search_since = False
        try:
            self.merge_config_options(self.defaults, self.cmdline.process(argv, self.defaults))
            self.cmdline.verify_options(self.cfg)

            self.__initialize()
            self.startup()

            if 'bug ids' in self.cfg:
                self.bug_handler_startup()
                for bug_id in self.cfg['bug ids']:
                    self.show_buff = ''

                    bug = KernelBug(self.lp.get_bug(bug_id))

                    try:
                        self.bug_handler(bug, self.cfg['package'])
                    except:
                        msg  = "An exception whas caught.\n"
                        msg += "            bug-id: %d.\n" % (bug.id)
                        msg += "           package: %s.\n" % (self.cfg['package'])
                        error(msg)
                        raise

                    if self.cfg['show']:
                        print(self.show_buff)
                self.bug_handler_shutdown()

            else:
                # Within the configuration file, there should be a section that is for bug information. If
                # it doesn't exist, create it.
                #
                if 'bugs_database' not in self.cfg:
                    self.cfg['bugs_database'] = {}
                    self.cfg['bugs_database']['packages'] = {}

                    six_months_ago = datetime.today() - timedelta(days=(31 * 6))
                    self.cfg['bugs_database']['updated'] = six_months_ago

                self.bdb = self.cfg['bugs_database']

                # Within the bug information in the configuration file should be a timestamp of the last
                # time this engine worked on the configuration file and worked on new bugs. If it doesn't
                # exist, this is a problem.
                #
                if 'updated' in self.bdb:
                    search_since = string_to_date(self.bdb['updated'])
                else:
                    raise BugEngineError("There is no timestamp in the configuration file. This is not good.")

                if 'search-criteria-status' in self.cfg:
                    search_criteria_status = self.cfg['search-criteria-status']
                else:
                    search_criteria_status = ["New"] # A list of the bug statuses that we care about

                try:
                    search_criteria_tags = self.cfg['search-criteria-tags']
                except KeyError:
                    search_criteria_tags = []

                try:
                    search_criteria_tags_combinator = self.cfg['search-criteria-tags-combinator']
                except KeyError:
                    search_criteria_tags_combinator = "Any"

                now = datetime.utcnow()
                self.bdb['updated'] = date_to_string(now)

                # Now find all the New bugs for all the packages we care about and do something with them.
                #
                #for package_name in self.ubuntu.active_packages: # FIXME bjf: do we want to do all the packages or just the linux
                                                                  #            package? there's plenty to work on with just the one
                                                                  #            but we don't want to ignore the others either.
                for package_name in ['linux']:
                    Dbg.verbose('Package: %s\n' % package_name)

                    try:
                        source_package = self.distro.get_source_package(package_name)
                        if source_package == None:
                            raise BugEngineError("The source package (%s) does not exist in LaunchPad." % (package_name))

                        Dbg.verbose('Search Criteria\n-------------------------------------------------------------------------------------\n')
                        if self.cfg['search_all']:
                            Dbg.verbose('              since: All\n')
                            Dbg.verbose('             status: "%s"\n' % ','.join(search_criteria_status))
                            if len(search_criteria_tags) > 0:
                                Dbg.verbose('               tags: "%s"\n' % ','.join(search_criteria_tags))
                                Dbg.verbose('    tags combinator: "%s"\n' % search_criteria_tags_combinator)
                                tasks = source_package.search_tasks(status=search_criteria_status,
                                                                    tags=search_criteria_tags,
                                                                    tags_combinator=search_criteria_tags_combinator)
                            else:
                                Dbg.verbose('    tags: None\n')
                                tasks = source_package.search_tasks(status=search_criteria_status)
                        else:
                            Dbg.verbose('              since: %s\n' % (search_since))
                            Dbg.verbose('             status: "%s"\n' % ','.join(search_criteria_status))
                            if len(search_criteria_tags) > 0:
                                Dbg.verbose('               tags: "%s"\n' % ','.join(search_criteria_tags))
                                Dbg.verbose('    tags combinator: "%s"\n' % search_criteria_tags_combinator)
                                tasks = source_package.search_tasks(status=search_criteria_status,
                                                                    tags=search_criteria_tags,
                                                                    tags_combinator=search_criteria_tags_combinator,
                                                                    modified_since=search_since)
                            else:
                                Dbg.verbose('    tags: None\n')
                                tasks = source_package.search_tasks(status=search_criteria_status,
                                                                    modified_since=search_since)

                        this_package_bugs = None
                        self.bug_handler_startup()
                        for task in tasks:
                            if package_name not in self.bdb['packages']:
                                self.bdb['packages'][package_name] = {}
                                self.bdb['packages'][package_name]['bugs'] = {}
                            this_package_bugs = self.bdb['packages'][package_name]['bugs']

                            bug = KernelBug(task.bug)
                            Dbg.what('%s (%s)\n' % (bug.id, package_name))
                            self.__verbose_bug_info(bug)

                            try:
                                self.show_buff = ''
                                self.bug_handler(bug, package_name)
                                if self.cfg['show']:
                                    if self.show_buff != '':
                                        print(self.show_buff)
                            except:
                                msg  = "An exception whas caught.\n"
                                msg += "            bug-id: %d.\n" % (bug.id)
                                if 'package' in self.cfg:
                                    msg += "           package: %s.\n" % (self.cfg['package'])
                                error(msg)
                                raise

                        self.bug_handler_shutdown()

                    except:
                        raise
                        raise BugEngineError("Exception caught processing the tasks, building the bugs database.\n")

            self.shutdown()

        # Handle command line errors.
        #
        except CmdlineError as e:
            self.cmdline.error(e.msg, self.defaults)
            Dbg.leave("BugEngine.run")
            exit(0)

        Dbg.leave("BugEngine.run")
        return

    # bug_handler_startup
    #
    def bug_handler_startup(self):
        """
        Setup the list of bug handler plugins that this script will use.

        The plugin list is pulled in here because we only want to do it once
        and not every time the bug_handler is called. And also, because this
        method is called after the base class has created self.lp.
        """
        Dbg.enter("BugEngine.bug_handler_startup")

        self.bug_handlers = BugHandler.get_plugins(self.cfg, self.lp, self.vout)

        # Yes, the verbose handling is a little stupid right now, it will get
        # cleaned up "soon".
        #
        if 'verbose' in self.cfg:
            BugHandler.verbose = self.cfg['verbose']

        if 'verbosity' in self.cfg:
            BugHandler.verbosity = self.cfg['verbosity']

        Dbg.leave("BugEngine.bug_handler_startup")

    # bug_handler_shutdown
    #
    def bug_handler_shutdown(self):
        Dbg.enter("BugEngine.bug_handler_shutdown")
        Dbg.leave("BugEngine.bug_handler_shutdown")

    # bug_handler
    #
    def bug_handler(self, bug, package_name):
        """
        Called for every bug that is found via a task search.
        """
        Dbg.enter("BugEngine.bug_handler")

        for handler in self.bug_handlers:
            handler.show_buff = ''
            result = handler.run(bug, self.get_relevant_task(bug, package_name), package_name)
            if not result: break
            self.show_buff += handler.show_buff

        Dbg.leave("BugEngine.bug_handler")
        return

    # main
    #
    def main(self):
        """
        Run the base class methods.
        """
        Dbg.enter("BugEngine.main")

        try:
            self.run()

        # Handle the user presses <ctrl-C>.
        #
        except KeyboardInterrupt:
            Dbg.leave("BugEngine.main")
            exit(0)

        # Handle application errors.
        #
        except BugEngineError as e:
            error(e.msg)

        Dbg.leave("BugEngine.main")
        return

    # __verbose_bug_info
    #
    def __verbose_bug_info(self, bug):
        if 'vbi' in Dbg.levels:
            print(" ")
            print(colored("    %s: %s" % (bug.id, bug.title), 'blue'))
            print(" ")
            print("        Owner: %s" % ("None" if bug.owner is None else bug.owner.display_name))

            tags = ""
            for t in bug.tags:
                tags += t
                tags += " "
            print("        Tags:")
            print("            %s" % (tags))

            tasks = bug.tasks
            print("        Tasks:")
            for task in tasks:
                print("            %45s %20s %20s" % (task.bug_target_name, task.status, task.importance))

    # get_relevant_task
    #
    def get_relevant_task(self, bug, pkg):
        retval = None
        for t in bug.tasks:
            name       = t.bug_target_name
            p = name.replace(' (Ubuntu)', '')
            if pkg == p:
                retval = t
                break
        return retval

# vi:set ts=4 sw=4 expandtab:
