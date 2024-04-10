#!/usr/bin/env python
#

from .shell                     import sh
from re                         import compile

class GitError(Exception):
    # __init__
    #
    def __init__(self, error):
        self.msg = error

class Git:
    commit_rc  = compile(r'^commit\s+([a-f0-9]+)\s*$')
    author_rc  = compile(r'^Author:\s+(.*)\s+<(.*)>$')
    date_rc    = compile(r'^Date:\s+(.*)$')
    buglink_rc = compile(r'^\s+BugLink:\s+http.*launchpad\.net/.*/([0-9]+)$')
    sob_rc     = compile(r'^\s+Signed-off-by:\s+(.*)\s+<(.*)>$')
    ack_rc     = compile(r'^\s+Acked-by:\s+(.*)\s+<(.*)>$')
    subject_rc = compile(r"^UBUNTU: (Ubuntu-.*)$")
    tag_rc     = compile(r"^Ubuntu-([a-z][^-]*-){0-2}(.*)$")
    log_results = {}

    @classmethod
    def sh(cls, cmd):
        status, tmp = sh(cmd, quiet=True)
        output = [l.replace('\n', '') for l in tmp]
        return status, output

    # is_repo
    #
    # If a "git branch" returns a 0 status and a non-empty result, then we
    # are in a git repository.
    #
    @classmethod
    def is_repo(cls):
        retval = False
        try:
            branches = cls.branches()
            if branches != "":
                retval = True

        except GitError:
            retval = False

        return retval

    # config
    #
    # Return the requested git config value. E.g. config("user.email")
    #
    @classmethod
    def config(cls, key):
        status, result = cls.sh("git config %s" % key)
        if status != 0:
            raise GitError(result)
        return result[0]

    # branches
    #
    # Return a list of all the git branches known to this git repository.
    #
    @classmethod
    def branches(cls):
        retval = []
        status, result = cls.sh("git branch")
        if status == 0:
            for line in result:
                if line[0] == '*':
                    line = line[1:]
                retval.append(line.strip())
        else:
            raise GitError(result)

        return retval

    # tags
    #
    @classmethod
    def tags(cls, contains=''):
        retval = []
        cmd = "git tag"
        if contains != '':
            cmd += ' --contains %s' % (contains)

        status, result = cls.sh(cmd)
        if status == 0:
            for line in result:
                if line != '' and line[0] == '*':
                    line = line[1:]
                retval.append(line.strip())
        else:
            raise GitError(result)

        return retval

    # current_branch
    #
    # Return a string that is the current branch checked out.
    #
    @classmethod
    def current_branch(cls):
        # Note: older versions of git symbolic-ref do not support --short
        status, result = cls.sh("git symbolic-ref HEAD")
        if status != 0:
            raise GitError("no current branch")
        return result[0].replace("refs/heads/", "")

    @classmethod
    def ubuntu_commit(cls, branch):
        """
        Return the SHA1 for the last commit that touched debian.master/ whose
        message matched the pattern 'UBUNTU: Ubuntu-[0-9]', given a branch.
        """
        (status, output) = cls.sh('git log --pretty=%%H -1 --grep="UBUNTU: Ubuntu-[0-9]" %s debian.master/' % (branch))
        if status == 0 and len(output) == 1:
            return output[0]
        return None

    @classmethod
    def subject(cls, commit):
        """
        Return message summary/subject from given commit.
        """
        (status, output) = cls.sh('git show --pretty=%%s -s %s' % (commit))
        if status == 0 and len(output) == 1:
            return output[0]
        return None

    @classmethod
    def tag_from_subject(cls, commit):
        """
        Given an Ubuntu closing commit, extract the matching tag from its subject.
        """
        subject = cls.subject(commit)
        match = cls.subject_rc.match(subject)
        if match:
            return match.group(1).replace("~", "_")
        return None

    @classmethod
    def version_from_subject(cls, commit):
        """
        Given an Ubuntu closing commit, extract the version from its subject.
        """
        tag = cls.tag_from_subject(commit)
        match = cls.tag_rc.match(tag)
        if match:
            tag = match.group(2)
        return tag.replace("_", "~")

    # show
    #
    @classmethod
    def show(cls, obj, branch=''):
        cmd = 'git show '
        if branch != '':
            cmd += branch + ':'
        cmd += obj

        status, result = cls.sh(cmd)
        if status != 0:
            raise GitError(result)

        return result

    @classmethod
    def __process_log_commit(cls, commit_text, sha1):
        results = {}
        results['sha1'] = sha1
        results['text'] = []
        for text in commit_text:

            while True:
                m = cls.author_rc.match(text)          # Author
                if m is not None:
                    id = {}
                    id['name'] = m.group(1)
                    id['email'] = m.group(2)
                    results['author'] = id
                    break

                m = cls.date_rc.match(text)            # Date
                if m is not None:
                    results['date'] = m.group(1)
                    break

                m = cls.buglink_rc.match(text)         # BugLink
                if m is not None:
                    bug = m.group(1)
                    if bug not in cls.log_results['buglink-index']:
                        cls.log_results['buglink-index'][bug] = []

                    if 'buglink' not in results:
                        results['buglink'] = []

                    cls.log_results['buglink-index'][bug].append(results['sha1'])
                    results['buglink'].append(bug)
                    results['text'].append(text)
                    break

                m = cls.sob_rc.match(text)             # Signed-off-by
                if m is not None:
                    if 'sob' not in results:
                        results['sob'] = []

                    id = {}
                    id['name'] = m.group(1)
                    id['email'] = m.group(2)
                    results['sob'].append(id)
                    results['text'].append(text)
                    break

                m = cls.ack_rc.match(text)             # Acked-by
                if m is not None:
                    if 'acks' not in results:
                        results['acks'] = []

                    id = {}
                    id['name'] = m.group(1)
                    id['email'] = m.group(2)
                    results['acks'].append(id)
                    results['text'].append(text)
                    break

                results['text'].append(text)
                break
        return results

    # log
    #
    # The idea here is to take the output from "git log" and turn it into
    # a python dictionary structure which can be used by other scripts
    # to easily get information. One of the most uesful items in this
    # dictionary is a list of commits indexed by the related buglink.
    #
    @classmethod
    def log(cls, num=-1):
        cls.log_results = {}
        cls.log_results['commits']       = []
        cls.log_results['buglink-index'] = {}
        if num != -1:
            status, result = cls.sh("git log -%d" % (num))
        else:
            status, result = cls.sh("git log")
        commit       = {}
        commit_text  = []
        current_sha1 = 'unknown'
        if status != 0:
            raise GitError(result)

        for line in result:
            m = cls.commit_rc.match(line)
            if m is not None:
                sha1 = m.group(1)
                # This is a new commit sha1. We are going to build up a dictionary entry
                # for this one commit and then add it to the dictionary of all commits.
                #
                # When building up this commit's dictionary entry, we go back through the
                # commit text looking for information we want to pull out and make easily
                # available via dictionary keys.
                #
                if len(commit_text) > 0:
                    commit = cls.__process_log_commit(commit_text, current_sha1)
                    cls.log_results['commits'].append(commit)

                    # Reset working variables
                    #
                    commit = {}
                    commit_text = []
                    current_sha1 = sha1

                else:
                    # This is the very first sha1
                    #
                    current_sha1 = m.group(1)
            else:
                # This is text between two SHA1s, just add it to the working
                # buffer for the current commit.
                #
                commit_text.append(line)

        if len(commit_text) > 0:
            commit = cls.__process_log_commit(commit_text, current_sha1)
            cls.log_results['commits'].append(commit)

        return cls.log_results

# vi:set ts=4 sw=4 expandtab:
