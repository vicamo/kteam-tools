#!/usr/bin/python

from message                    import Message
from fnmatch                    import fnmatch
from utils                      import (
    o2str,
    typecheck_Entry
    )

# Attachment
#
class Attachment(object):
    TAR_ARCHIVE_TYPES = [
        'application/x-tar',
        ]
    TAR_ARCHIVE_EXTS = [
        '*.tar.gz',
        '*.tgz',
        '*.tar.bz2',
        ]
    ZIP_ARCHIVE_TYPES = [
        'application/zip'
        ]
    ZIP_ARCHIVE_EXTS = [
        '*.zip'
        ]
    MIMETYPES = {
            '*.txt' : 'text/plain',
            '*.log' : 'text/plain',
            }

    # __init__
    #
    def __init__(self, tkbug, lpattachment, force_mimetype=False):
        self.__tkbug          = tkbug
        self.__commit_changes = tkbug.commit_changes
        self.__attachment     = typecheck_Entry(lpattachment)
        self.__force_mimetype = force_mimetype
        self.__title          = None
        self.__type           = None
        self.__message        = None
        self.__data           = None
        self.__remotefd       = None
        self.__content        = None
        self.__filename       = None
        self.__url            = None

    # __del__
    #
    def __del__(self):
        if self.__remotefd:
            self.__remotefd.close()

    # __len__
    #
    def __len__(self):
        return self.remotefd.len

    def __eq__(self, other):
        return self.__attachment == other.__attachment

    def __ne__(self, other):
        return self.__attachment != other.__attachment

    def __find_mimetype(self):
        for pattern, mimetype in self.MIMETYPES.iteritems():
            if fnmatch(self.title, pattern):
                return mimetype

    # title
    #
    @property
    def title(self):
        if self.__title == None:
            self.__title = o2str(self.__attachment.title)
        return self.__title

    # kind
    #
    @property
    def kind(self):
        if self.__type == None:
            self.__type = self.__attachment.type
        return self.__type

    # url
    #
    @property
    def url(self):
        if self.__url == None:
            self.__url = "%s/+files/%s" %(
                self.__attachment.web_link,
                self.filename)
        return self.__url

    # content_type
    #
    @property
    def content_type(self):
        if self.__force_mimetype:
            return self.__find_mimetype()
        else:
            return self.remotefd.content_type

    # message
    #
    @property
    def message(self):
        if self.__message == None:
            self.__message = Message(self.__tkbug, self.__attachment.message)
        return self.__message

    # owner
    #
    @property
    def owner(self):
        if not self.message:
            return None
        return self.message.owner

    # age (in days)
    #
    @property
    def age(self):
        if not self.message:
            return None
        t = self.message.date_created
        now = t.now(t.tzinfo)
        return 0 + (now - t).days

    # data
    #
    @property
    def data(self):
        if self.__data == None:
            self.__data = self.__attachment.data
        return self.__data

    # remotefd
    #
    @property
    def remotefd(self):
        if self.__remotefd == None:
            self.__remotefd = self.data.open()
        return self.__remotefd

    # filename
    #
    @property
    def filename(self):
        if self.__filename == None:
            self.__filename = self.remotefd.filename
        return self.__filename

    # content
    #
    @property
    def content(self):
        if self.__content == None:
            self.__content = self.remotefd.read()
        return self.__content

    def is_patch(self):
        return bool(self.kind == 'Patch')

    def is_archive_type(self, type):
        type = type.upper()
        if not hasattr(self, '%s_ARCHIVE_TYPES' % type):
            return False
        archive_types = getattr(self, '%s_ARCHIVE_TYPES' % type)
        archive_exts = getattr(self, '%s_ARCHIVE_EXTS' % type)

        if self.remotefd.content_type in archive_types:
            return True

        for ext in archive_exts:
            if fnmatch(self.title, ext):
                return True

        return False

    def is_archive(self):
        return self.is_archive_type('tar') or self.is_archive_type('zip')

# vi:set ts=4 sw=4 expandtab:
