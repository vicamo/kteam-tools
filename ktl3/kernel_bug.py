#!/usr/bin/env python
#

from lpltk.LaunchpadService             import LaunchpadService
from lpltk.bug                          import Bug
from ktl3.bugs                          import DeltaTime
from ktl3.ubuntu                        import Ubuntu
from ktl3.utils                         import debug as dout
from ktl3.dbg                           import Dbg
from ktl3.termcolor                     import colored
from datetime                           import datetime
import re

# KernelLPService
#
class KernelLPService(LaunchpadService):
    """
    A customized version of the LPLTK LaunchpadService class. The reason for
    this is that I wanted to subclass the LPLTK Bug class. Since the LaunchpadService
    method get_bug returns an instance of a Bug class, and since I couldn't figure
    out how to cast a Bug object into a KernelBug object, I needed this subclass.
    """

    def __init__(self, config=None):
        """
        See: lpltk.LaunchpadService.__init__
        """
        LaunchpadService.__init__(self, config)


    # get_bug
    #
    def get_bug(self, bug_id):
        """
        Return an instance of a KernelBug object based on the LP object related
        to the specified bug_number.
        """
        return KernelBug(self, bug_id)

# KernelBug
#
class KernelBug(Bug):
    """
    A subclass of the standard lpltk bug class which adds methods of interest
    to the kernel team.
    """
    debug  = False

    # __init__
    #
    #def __init__(self, bug_id, commit_changes=True):
    def __init__(self, bug):
        Bug.__init__(self, bug.service, bug.id, bug.commit_changes)

        self.file_regexes = [
            # added via ubuntu-bug or apport-collect
            {'name':'BootDmesg',        're':'BootDmesg\.txt',               'type' : 'dmesg',           },
            {'name':'CurrentDmesg',     're':'CurrentDmesg\.txt',            'type' : 'dmesg',           },
            {'name':'Dependencies',     're':'Dependencies\.txt',            'type' : 'dependencies',    },
            {'name':'HalComputerInfo',  're':'HalComputerInfo\.txt',         'type' : 'hal',             },
            {'name':'LsUsb',            're':'LsUsb\.txt',                   'type' : 'lsusb',           },
            {'name':'Lspci',            're':'Lspci\.txt',                   'type' : 'lspci',           },
            {'name':'ProcCpuInfo',      're':'ProcCpuInfo\.txt',             'type' : 'proc_cpu',        },
            {'name':'ProcInterrupts',   're':'ProcInterrupts\.txt',          'type' : 'proc_interrupts', },
            {'name':'ProcModules',      're':'ProcModules\.txt',             'type' : 'proc_modules',    },

            {'name':'kernlog',          're':'kern\.log',                    'type' : 'dmesg',           },
            {'name':'dmesg',            're':'dmesg',                        'type' : 'dmesg',           },
            {'name':'lshw',             're':'lshw',                         'type' : 'lshw',            },
            {'name':'lspci',            're':'lspci',                        'type' : 'lspci',           },
            {'name':'lsusb',            're':'lsusb',                        'type' : 'lsusb',           },
            {'name':'lshal',            're':'lshal',                        'type' : 'lshal',           },
            {'name':'lsmod',            're':'lsmod',                        'type' : 'lsmod',           },
        ]

        for file_regex in self.file_regexes:
            file_regex['rc'] = re.compile(file_regex['re'], re.IGNORECASE)

        self.ubuntu = Ubuntu()
        return

    # dbg
    #
    def dbg(self, msg):
        dout(msg, self.debug)

    # has_required_logs
    #
    @property
    def has_required_logs(self):
        """
        Examines a bug and determines if it has all the logs that the kernel
        team requires.
        """
        retval = False

        # If we've determined the problem type to be "Package" and the bug has been
        # tagged with "apport-package" then it's pretty safe to assume that apport
        # collected the necessary logs.
        #
        if (self.problem_type == 'Package') and (('apport-package' in self.tags) or ('apport-collected' in self.tags)):
            retval = True
            return retval # FIXME bjf - I don't like returning out of the middle of functions/methods

        # For the kernel, I want at least one Dmesg and one Lspci log file.
        #
        required = ['dmesg', 'lspci']

        try:
            owner = self.owner.display_name

        except:
            pass

        else:
            try:
                for attachment in self.attachments:
                    self.dbg("Attachment title: '%s'\n" % (attachment.title))

                    try:
                        msg = attachment.message
                        if msg is None:
                            continue

                        attachment_owner = msg.owner
                        if attachment_owner is None:
                            continue

                        if attachment_owner.display_name != owner:
                            continue

                        for file_regex in self.file_regexes:
                            if not file_regex['rc'].search(attachment.title):
                                continue

                            if file_regex['type'] in required:
                                required.remove(file_regex['type'])
                            break

                        if len(required) == 0:
                            # We have all required logs
                            retval = True
                            break
                    except:
                        continue # If any exceptions are thrown for a given attachment, it is skipped

            except:
                print("Exception encountered while going through attachments for bug (%s)\n" % (self.id))
                raise

        return retval

    # kernel_gravity
    #
    @property
    def kernel_gravity(self):
        """
        Try to come up with an integer value that represents the need of this
        bug to be addressed. The higher the number, the more attention it deserves.
        """
        gravity = 0

        now = datetime.utcnow()

        # Calculate a value based on how long before now the bug was created. The longer
        # ago, the lower the value.
        #
        ago = DeltaTime(self.date_created, now)
        if   ago.days <  7: gravity += 1000
        elif ago.days < 14: gravity += 500
        elif ago.days < 21: gravity += 250
        elif ago.days < 30: gravity += 100

        ago = DeltaTime(self.date_last_message, now)
        if   ago.days <  7: gravity += 1000
        elif ago.days < 14: gravity += 500
        elif ago.days < 21: gravity += 250
        elif ago.days < 30: gravity += 100

        return gravity

    # _ubuntu_series_lookup
    #
    def _ubuntu_series_lookup(self, version):
        """
        Given a version find the corresponding series name and version. The version
        could be a kernel version or a series version.

        This method returns a (series_name, series_version) tuple.
        """
        self.dbg(' . Looking up the series name for (%s)\n' % version)
        series_name = ''
        series_version = ''
        if series_name == '':
            m = re.search('([0-9]+)\.([0-9]+)\.([0-9]+)\-([0-9]+)\-(.*?)', version)
            if m is not None:
                kver = "%s.%s.%s" % (m.group(1), m.group(2), m.group(3))
                if kver in self.ubuntu.index_by_kernel_version:
                    series_name    = self.ubuntu.index_by_kernel_version[kver]['name']
                    series_version = self.ubuntu.index_by_kernel_version[kver]['series_version']
                    self.dbg('    - found kernel version in the db\n')
            else:
                self.dbg('    - didn\'t match kernel version pattern\n')

        if series_name == '':
            m = re.search('([0-9+)\.([0-9]+)', version)
            if m is not None:
                dnum = m.group(1)
                if dnum in self.ubuntu.db:
                    series_name   = self.ubuntu.db[dnum]['name']
                    series_version = dnum
                    self.dbg('    - found series version in the db\n')
            else:
                self.dbg('    - didn\'t match series version pattern\n')

        if series_name == '':
            try:
                rec = self.ubuntu.lookup(version)
                series_name = rec['name']
                series_version = rec['series_version']
            except KeyError:
                pass

        self.dbg('    - returning (%s)\n' % series_name)
        return (series_name, series_version)

    # _ubuntu_series_version_lookup
    #
    def _ubuntu_series_version_lookup(self, series_name):
        self.dbg(' . Looking up the series version for (%s)\n' % series_name)
        retval = ''
        for version in self.ubuntu.index_by_kernel_version:
            if series_name == self.ubuntu.index_by_kernel_version[version]['name']:
                retval = version
                break
        return retval

    # problem_type
    #
    @property
    def problem_type(self):
        """
        Look in the bug description to see if we can determine the type of problem
        that the bug is about. We are looking for a "ProblemType:" line in the
        description to help.
        """
        retval = None
        for line in self.description.split('\n'):
            m = re.search('ProblemType:\s*(.*)', line)
            if m is not None:
                retval = m.group(1)
        return retval


    # _find_series_in_description
    #
    def _find_series_in_description(self, bug):
        """
        Look in the bugs description to see if we can determine which distro the
        the user is running (hardy/intrepid/jaunty/karmic/lucid/etc.).
        """
        self.dbg(' . Looking for the series in the description\n')
        series_name = ''
        series_version = ''

        desc_lines = bug.description.split('\n')
        for line in desc_lines:
            # Sometimes there is a "DistroRelease:" line in the description.
            #
            m = re.search('DistroRelease:\s*(.*)', line)
            if m is not None:
                (series_name, series_version) = self._ubuntu_series_lookup(m.group(1))
                if series_name != '':
                    break

            # Sometimes there is the results of 'uname -a' or a dmesg in
            # the description.
            #
            m = re.search('Linux version ([0-9]+)\.([0-9]+)\.([0-9]+)\-([0-9]+)\-(.*?) .*', line)
            if m is not None:
                kernel_version = "%s.%s.%s-%s-%s" % (m.group(1), m.group(2), m.group(3), m.group(4), m.group(5))
                (series_name, series_version) = self._ubuntu_series_lookup(kernel_version)
                if series_name != '':
                    break

            if 'Description:' in line:
                m = re.search('Description:\s*([0-9]+\.[0-9]+)', line)
                if m is not None:
                    (series_name, series_version) = self._ubuntu_series_lookup(m.group(1))
                    if series_name != '':
                        break

            if 'Release:' in line:
                m = re.search('Release:\s+([0-9]+\.[0-9]+)', line)
                if m is not None:
                    (series_name, series_version) = self._ubuntu_series_lookup(m.group(1))
                    if series_name != '':
                        break

            m = re.search('([0-9]+)\.([0-9]+)\.([0-9]+)\-([0-9]+)\-(.*?) .*', line)
            if m is not None:
                kernel_version = "%s.%s.%s-%s-%s" % (m.group(1), m.group(2), m.group(3), m.group(4), m.group(5))
                (series_name, series_version) = self._ubuntu_series_lookup(kernel_version)
                if series_name != '':
                    break

            # Sometimes it's just in the description
            #
            m = re.search('Ubuntu ((hardy|intrepid|jaunty|karmic|lucid|maverick|natty|oneiric)) [0-9]+\.[0-9]+', line)
            if (m != None):
                series_name = m.group(1)
                series_version = self._ubuntu_series_version_lookup(series_name)

        if series_name == '':
            self.dbg('     - Not found\n')
        return (series_name, series_version)

    # _find_linux_version
    #
    def _find_linux_version(self, attachment, bug):
        retval = ''
        try:
            file = attachment.data.open()
            for line in file:
                m = re.search('Linux version ([0-9]+)\.([0-9]+)\.([0-9]+)\-([0-9]+)\-(.*?) .*', line)
                if (m != None):
                    self.dbg('       - found\n')
                    retval = "%s.%s.%s-%s-%s" % (m.group(1), m.group(2), m.group(3), m.group(4), m.group(5))
                    break
            file.close()
        except:
            print("  ** Warning: Exception thrown attempting to open an attachment. (%s) [%s]" % (attachment.title, bug.id))
            pass
        return retval

    # _find_series_in_attachments
    #
    def _find_series_in_attachments(self, bug):
        """
        Look through the various files attached to the bug, by the original
        submitter/owner and see if we can determine the distro from there.
        """
        self.dbg(' . Looking for the series in the attachments\n')
        series_name = ''
        series_version = ''
        kernel_version = ''

        try:
            owner = bug.owner
            if owner is None:
                raise # Will get eaten at the bottom

            owner = bug.owner.display_name.encode('utf-8')
            for attachment in bug.attachments:
                self.dbg('     - attachment: "%s"\n' % (attachment.title))
                try:
                    # Short circuit the loop, if the attachment isn't from the bug
                    # submitter, we don't really care.
                    #
                    if (attachment.message.owner.display_name.encode('utf-8') != owner):
                        self.dbg('     - skipped, not the original bug submitter\n')
                        continue

                    # kern.log
                    #
                    m = re.search('kern.log]*', attachment.title)
                    if m != None:
                        self.dbg('         - examining\n')
                        kernel_version = self._find_linux_version(attachment, bug)
                        if kernel_version != '':
                            (series_name, series_version) = self._ubuntu_series_lookup(kernel_version)
                            if series_name != '':
                                break

                    # BootDmesg.txt
                    #
                    m = re.search('Boot[Dd]mesg[.txt|.log]*', attachment.title)
                    if m != None:
                        self.dbg('     - BootDmesg.log\n')
                        kernel_version = self._find_linux_version(attachment, bug)
                        if kernel_version != '':
                            (series_name, series_version) = self._ubuntu_series_lookup(kernel_version)
                            if series_name != '':
                                break

                    # Dmesg.txt / dmesg.log
                    #
                    m = re.search('[Dd]mesg[.txt|.log]*', attachment.title)
                    if m != None:
                        self.dbg('     - Dmesg.log\n')
                        kernel_version = self._find_linux_version(attachment, bug)
                        if kernel_version != '':
                            (series_name, series_version) = self._ubuntu_series_lookup(kernel_version)
                            if series_name != '':
                                break

                    # alsa-info
                    #
                    if series_name == '':
                        if 'alsa-info' in attachment.title:
                            self.dbg('     - alsa-info.log\n')
                            try:
                                file = attachment.data.open()
                                for line in file:
                                    m = re.search('Kernel release:\s+([0-9]+)\.([0-9]+)\.([0-9]+)\-([0-9]+)\-(.*?)', line)
                                    if (m != None):
                                        self.dbg('       - found\n')
                                        kernel_version = "%s.%s.%s-%s-%s" % (m.group(1), m.group(2), m.group(3), m.group(4), m.group(5))
                                        break
                                file.close()
                            except:
                                print("  ** Warning: Exception thrown attempting to open an attachment. (%s) [%s]" % (attachment.title, bug.id))
                                pass
                            if kernel_version != '':
                                (series_name, series_version) = self._ubuntu_series_lookup(kernel_version)
                                if series_name != '':
                                    break

                    # xorg.0.log
                    #
                    if series_name == '':
                        m = re.search('[Xx]org\.0\.log.*', attachment.title)
                        if m != None:
                            self.dbg('     - Xorg.0.log\n')
                            try:
                                file = attachment.data.open()
                                for line in file:
                                    if "Current Operating System" not in line: continue
                                    m = re.search('Linux \S+ ([0-9]+)\.([0-9]+)\.([0-9]+)\-([0-9]+)\-(.*?) .*', line)
                                    if (m != None):
                                        self.dbg('       - found\n')
                                        kernel_version = "%s.%s.%s-%s-%s" % (m.group(1), m.group(2), m.group(3), m.group(4), m.group(5))
                                        break
                                file.close()
                            except:
                                print("  ** Warning: Exception thrown attempting to open an attachment. (%s) [%s]" % (attachment.title, bug.id))
                                pass
                            if kernel_version != '':
                                (series_name, series_version) = self._ubuntu_series_lookup(kernel_version)
                                if series_name != '':
                                    break

                except:
                    pass # Just eat any exceptions
        except:
            pass # Just eat any exceptions

        return (series_name, series_version)

    # _find_series_in_title
    #
    # Scan title for a pattern that looks like a distro name or version, and
    # return the newest release version found.
    #
    def _find_series_in_title(self, bug):
        self.dbg(' . Looking for the series in the title\n')
        series_name = ''
        series_version = ''
        for rel_num, rel in self.ubuntu.db.items():
            pat = "(%s|[^0-9\.\-]%s[^0-9\.\-])" %(rel['name'], rel_num.replace(".", "\."))
            regex = re.compile(pat, re.IGNORECASE)
            if regex.search(bug.title):
                (series_name, series_version) = self._ubuntu_series_lookup(rel['name'])
        return (series_name, series_version)

    # _find_series_in_tags
    #
    def _find_series_in_tags(self, bug):
        """
        Search through all the tags on a bug to see if we can find the series that the
        bug was filed against.
        """
        self.dbg(' . Looking for the series in the tags\n')
        series_name = ''
        series_version = ''

        for series in Ubuntu.index_by_series_name:
            if series in bug.tags:
                (series_name, series_version) = self._ubuntu_series_lookup(series)
                if series_name != '':
                    break

        return (series_name, series_version)

    # series
    #
    # Try to figure out which distro version the bug submitter is running
    # and has file the bug against.
    #
    @property
    def series(self):
        result = ''
        (series_name, series_version) = self._find_series_in_description(self)

        if (series_name == ''):
            (series_name, series_version) = self._find_series_in_attachments(self)

        if (series_name == ''):
            (series_name, series_version) = self._find_series_in_tags(self)

        if (series_name == ''):
            (series_name, series_version) = self._find_series_in_title(self)

        return (series_name, series_version)

    # find_attachment
    #
    def find_attachment(self, attachment_title):
        """
        Return a list of all the lines in the desired attachment.

        NOTE: This isn't really the right way to do this, I think I should return a file handle
              which gets cleaned up when it goes out of scope.
        """
        retval = None
        try:
            if self.owner is None:
                raise # Will get eaten at the bottom

            owner = self.owner.display_name.encode('utf-8')
            for attachment in self.attachments:
                self.dbg('     - attachment: "%s"\n' % (attachment.title))

                # Short circuit the loop, if the attachment isn't from the bug
                # submitter, we don't really care.
                #
                if (attachment.message.owner.display_name.encode('utf-8') != owner):
                    self.dbg('     - skipped, not the original bug submitter\n')
                    continue

                if attachment_title == attachment.title:
                    retval = attachment.content
        except:
            if self.dbg:
                raise
            pass # Just eat any exceptions
        return retval

    # get_relevant_task
    #
    def get_relevant_task(self, pkg):
        retval = None
        for t in self.tasks:
            task       = t.bug_target_name
            p = task.replace(' (Ubuntu)', '')
            if pkg == p:
                retval = t
                break
        return retval

    def print_verbose_info(self):
        if 'verbose' in Dbg.levels:
            print(" ")
            print(colored("    %s: %s" % (self.id, self.title), 'blue'))
            print(" ")
            print("        Owner: %s" % ("None" if self.owner is None else self.owner.display_name))

    # _get_version_from_property
    #
    def _get_version_from_property(self, key):
        Dbg.enter('DecodeKernelVersion._get_version_from_property')

        retval = None
        m = re.search('([0-9]+)\.([0-9]+)\.([0-9]+)\-([0-9]+)\.([0-9]+)', self.properties[key])
        Dbg.verbose('%s found\n' % key)
        if m is not None:
            Dbg.verbose('%s match found\n' % key)
            retval = "%s.%s.%s-%s.%s" % (m.group(1), m.group(2), m.group(3), m.group(4), m.group(5))

        Dbg.ret('DecodeKernelVersion._get_version_from_property', retval)
        return retval

    # _find_kernel_version_in_description
    #
    def _find_kernel_version_in_description(self):
        '''
        The kernel version can be in different lines in the description. Try to
        find one of them with the full version.
        '''
        Dbg.enter('KernelBug._find_kernel_version_in_description')
        retval = None
        desc_lines = self.description.split('\n')
        for line in desc_lines:
            m = re.search('Linux version ([0-9]+)\.([0-9]+)\.([0-9]+)\-([0-9]+)\-(.*?) .*', line)
            if m is not None:
                retval = "%s.%s.%s-%s.%s" % (m.group(1), m.group(2), m.group(3), m.group(4), m.group(5))
                Dbg.verbose("Kernel version: %s" % retval)
                break

            m = re.search('(\d+)\.(\d+)\.(\d+)[\-|\.](\d+)-\S+ #(\d+)', line)
            if m is not None:
                retval = "%s.%s.%s-%s.%s" % (m.group(1), m.group(2), m.group(3), m.group(4), m.group(5))
                Dbg.verbose("Kernel version: %s" % retval)
                break

        Dbg.ret('KernelBug._find_kernel_version_in_description', retval)
        return retval

    # booted_kernel_version
    #
    @property
    def booted_kernel_version(self):
        '''
        Look at various data in the bug and determine the kernel version that was booted.
        '''
        Dbg.enter('KernelBug.kernel_version')
        retval = None

        while True:
            # "ProcVersionSignature": "Ubuntu 2.6.35-22.33-generic 2.6.35.4",
            #
            try:
                retval = self._get_version_from_property('ProcVersionSignature')
                break
            except KeyError:
                pass

            #  "Uname": "Linux 2.6.35-22-generic i686"
            #
            try:
                retval = self._get_version_from_property('Uname')
                break
            except KeyError:
                pass

            retval = self._find_kernel_version_in_description()
            break

        Dbg.ret('KernelBug.kernel_version', retval)
        return retval

# vi:set ts=4 sw=4 expandtab:
