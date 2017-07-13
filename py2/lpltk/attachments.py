#!/usr/bin/python

import gzip
import os
import shutil
import tarfile

from copy                       import copy
from locale                     import getpreferredencoding
from zipfile                    import ZipFile

from attachment                 import Attachment
from fnmatch                    import fnmatch

# Attachments
#
# A collection class for files added into launchpad, also known
# as an attachment.
#

class LocalAttachment(object):
    class Data:
        class Fd(file):
            @property
            def content_type(self):
                return None

            @property
            def len(self):
                stat = os.stat(self.name)
                return stat.st_size

        def set_path(self, path):
            self.__path = path
        def open(self):
            if self.__path:
                return LocalAttachment.Data.Fd(self.__path)

    def __init__(self):
        self.data = LocalAttachment.Data()

class Attachments(object):
    # __init__
    #
    # Initialize the instance from a Launchpad bug.
    #
    def __init__(self, tkbug):
        self.__tkbug                = tkbug
        self.__commit_changes       = tkbug.commit_changes
        self.__attachments          = None
        self.__filters              = []

        self.__download             = False
        self.__download_dir         = None

        self.__extract              = False
        self.__extract_dir          = None
        self.__extract_limit        = None

        self.__gzip                 = False
        self.__gzip_dir             = None

        self.__force_mimetype       = False

    # __len__
    #
    def __len__(self):
        return len(list(self.__iter__()))

    # __getitem__
    #
    def __getitem__(self, key):
        return list(self.__iter__())[key]

    # __iter__
    #
    def __iter__(self):
        self.__fetch_if_needed()
        for attachment in self.__attachments:
            if self.__gzip:
                attachment = self.__gzip_if_needed(attachment)

            included = True
            a = Attachment(self.__tkbug, attachment, self.__force_mimetype)
            for f, params in self.__filters:
                if not f(a, params):
                    included = False
            if included:
                if self.__extract and \
                            a.is_archive_type('tar') and \
                            not self.__exceeds_tar_limit(a.remotefd):
                    for member in self.__get_tar_members(a):
                        yield member
                elif self.__extract and \
                            a.is_archive_type('zip') and \
                            not self.__exceeds_zip_limit(a.remotefd):
                    for member in self.__get_zip_members(a):
                        yield member
                else:
                    if self.__download and \
                            not isinstance(attachment, LocalAttachment):
                        tmpfile = os.path.join(self.__download_dir, a.title)
                        with open(tmpfile, 'w+b') as localfd:
                            localfd.write(a.content)
                    yield a

    # __contains__
    #
    def __contains__(self, item):
        return item in self.__iter__()

    # __fetch_if_needed
    #
    def __fetch_if_needed(self):
        if self.__attachments == None:
            self.__attachments = self.__tkbug.lpbug.attachments_collection

    def __gzip_if_needed(self, attachment):
        filters = dict(self.__filters)
        if not filters.has_key(filter_size_between):
            return attachment

        minsize, maxsize = filters[filter_size_between]
        remotefd = attachment.data.open()

        if remotefd.len > maxsize:
            gzip_attachment = LocalAttachment()
            gzip_attachment.title = attachment.title + '.gz'
            gzip_attachment.type = attachment.type

            tmpfile = os.path.join(self.__gzip_dir, gzip_attachment.title)
            gzipfd = gzip.open(tmpfile, 'w+b')
            gzipfd.write(remotefd.read())
            gzipfd.close()

            gzip_attachment.data.set_path(tmpfile)
            attachment = gzip_attachment

        remotefd.close()
        return attachment

    def __find_mime_type(self, attachment):
        for pattern, mimetype in self.MIMETYPES.iteritems():
            if fnmatch(attachment.title, pattern):
                return mimetype

    def __get_tar_members(self, tarattachment):
        tar = tarfile.open(fileobj=tarattachment.remotefd)

        attachments = []
        for member in tar:
            if member.isfile():
                attachment = LocalAttachment()
                attachment.title = os.path.basename(member.name)
                if (fnmatch(attachment.title, '*.diff') or
                    fnmatch(attachment.title, '*.patch')):
                    attachment.type = 'Patch'
                else:
                    attachment.type = None

                tar.extract(member, self.__extract_dir)
                oldpath = os.path.join(self.__extract_dir,
                                       member.name)
                newpath = os.path.join(self.__extract_dir,
                                       os.path.basename(member.name))
                shutil.move(oldpath, newpath)
                attachment.data.set_path(newpath)

                attachments.append(Attachment(self.__tkbug,
                                              attachment,
                                              self.__force_mimetype))

        return attachments

    def __exceeds_tar_limit(self, fd):
        if not self.__extract_limit:
            return False

        tar = tarfile.open(fileobj=fd)
        result = len(tar.getnames()) > self.__extract_limit
        fd.seek(0)

        return result

    def __get_zip_members(self, zipattachment):
        zip = ZipFile(file=zipattachment.remotefd)

        attachments = []
        for member in [zip.open(name) for name in zip.namelist()]:
            if member.name[-1] == '/':
                continue

            attachment = LocalAttachment()
            attachment.title = os.path.basename(member.name)
            if (fnmatch(attachment.title, '*.diff') or
                fnmatch(attachment.title, '*.patch')):
                attachment.type = 'Patch'
            else:
                attachment.type = None

            zip.extract(member.name, self.__extract_dir)
            oldpath = os.path.join(self.__extract_dir, member.name)
            newpath = os.path.join(self.__extract_dir,
                                   os.path.basename(member.name))
            shutil.move(oldpath, newpath)
            attachment.data.set_path(newpath)

            attachments.append(Attachment(self.__tkbug,
                                          attachment,
                                          self.__force_mimetype))

        return attachments

    def __exceeds_zip_limit(self, fd):
        if not self.__extract_limit:
            return False

        zip = ZipFile(file=fd)
        result = len(zip.namelist()) > self.__extract_limit
        fd.seek(0)

        return result

    def download_in_dir(self, download_dir):
        self.__download = True
        self.__download_dir = download_dir

    def extract_archives(self, extract_dir, extract_limit=None):
        self.__extract = True
        self.__extract_dir = extract_dir
        self.__extract_limit = extract_limit

    def try_gzip(self, gzip_dir):
        self.__gzip = True
        self.__gzip_dir = gzip_dir

    def force_mimetype(self):
        self.__force_mimetype = True

    def add_filter(self, f, params):
        """ Add filter f to constrain the list of attachments.

        f is a function which takes as arguments an Attachment
        object, and a list of parameters specific to the given
        filter.
        """
        self.__filters.append( (f, params) )

    def check_required_files(self, glob_patterns):
        """ Check that collection includes required filenames

        Given a list of glob filename patterns, looks through the
        attachments to verify at least one attachment fulfils the
        required file pattern.  Returns a list of globs that were
        not matched.  Returns an empty list if all requirements
        were met.
        """
        missing = []
        for glob_pattern in glob_patterns:
            found = False

            for a in self.__iter__():
                if fnmatch(a.filename, glob_pattern):
                    found = True
                    break

            if not found:
                missing.append(glob_pattern)
        return missing

# Filters
def filter_owned_by_person(attachment, persons):
    """ File owned by specific person(s) (e.g. original bug reporter) """
    return bool(attachment.owner and
                attachment.owner in persons)

def filter_filename_matches_globs(attachment, glob_patterns):
    """ Filename matches one of a set of glob patterns (e.g. Xorg.*.log) """
    filename = attachment.title
    for glob_pattern in glob_patterns:
        if fnmatch(filename, glob_pattern):
            return False
    return True

def filter_size_between(attachment, sizes):
    """ File size is within [min, max] bounds """
    assert(len(sizes) == 2)
    min_size = sizes[0]
    max_size = sizes[1]
    return bool(min_size <= len(attachment) and len(attachment) <= max_size)

def filter_age_between(attachment, ages_in_days):
    """ File was attached to bug between [min, max] days """
    assert(len(ages_in_days) == 2)
    min_age = ages_in_days[0]
    max_age = ages_in_days[1]
    return bool(min_age <= attachment.age and attachment.age <= max_age)

def filter_is_patch(attachment, is_patch):
    return attachment.is_patch() == is_patch

# vi:set ts=4 sw=4 expandtab:
