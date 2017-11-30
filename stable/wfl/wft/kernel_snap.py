
from wfl.log                                    import center, cleave, cinfo, cerror
from wfl.snap                                   import SnapStore, SnapStoreError
from .base                                      import TaskHandler

from ktl.kernel_series                          import KernelSeries


class KernelSnapBase(TaskHandler):
    '''
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(KernelSnapBase, s).__init__(lp, task, bug)

        s._snap_info = False
        s._snap_store = None

        cleave(s.__class__.__name__ + '.__init__')

    @property
    def snap_info(s):
        '''
        Return a KernelSeriesSnapEntry for the snap.  If not found, None
        is returned.
        '''
        if s._snap_info == False:
            # XXX: we so should keep this package object as an attr on the bug.
            kernel_series = KernelSeries()
            series = kernel_series.lookup_series(codename=s.bug.series)
            package = series.lookup_source(s.bug.pkg_name)

            # XXX: the bugs we create need to record the snap name.
            snaps = package.snaps
            s._snap_info = None
            for snap in snaps:
                if snap.primary:
                    s._snap_info = snap
                    break

        return s._snap_info

    @property
    def snap_store(s):
        if s._snap_store is None:
            s._snap_store = SnapStore(s.bug, s.snap_info)
        return s._snap_store


class SnapReleaseToEdge(KernelSnapBase):
    '''
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(SnapReleaseToEdge, s).__init__(lp, task, bug)

        s.jumper['New']           = s._new
        s.jumper['Confirmed']     = s._verify_release
        s.jumper['Triaged']       = s._verify_release
        s.jumper['In Progress']   = s._verify_release
        s.jumper['Fix Committed'] = s._verify_release

        cleave(s.__class__.__name__ + '.__init__')

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        # The snap should be released to edge and beta channels after
        # the package hits -proposed.
        if s.bug.tasks_by_name['promote-to-proposed'].status == 'Fix Released':
            s.task.status = 'Confirmed'
            s.task.timestamp('started')
            retval = True
        else:
            cinfo('    task promote-to-proposed is not \'Fix Released\'', 'yellow')

        cleave(s.__class__.__name__ + '._new (%s)' % (retval))
        return retval

    # _verify_release
    #
    def _verify_release(s):
        center(s.__class__.__name__ + '._verify_release')
        retval = False

        try:
            if s.snap_store.match_version('edge'):
                s.task.status = 'Fix Released'
                s.task.timestamp('finished')
                retval = True
            else:
                cinfo('    snap not in edge channel', 'yellow')
        except SnapStoreError as e:
            cerror('    failed to query snap store (%s)' % str(e))

        cleave(s.__class__.__name__ + '._verify_release (%s)' % (retval))
        return retval


class SnapReleaseToBeta(KernelSnapBase):
    '''
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(SnapReleaseToBeta, s).__init__(lp, task, bug)

        s.jumper['New']           = s._new
        s.jumper['Confirmed']     = s._verify_release
        s.jumper['Triaged']       = s._verify_release
        s.jumper['In Progress']   = s._verify_release
        s.jumper['Fix Committed'] = s._verify_release

        cleave(s.__class__.__name__ + '.__init__')

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        # The snap should be released to edge and beta channels after
        # the package hits -proposed.
        if s.bug.tasks_by_name['promote-to-proposed'].status == 'Fix Released':
            s.task.status = 'Confirmed'
            s.task.timestamp('started')
            retval = True
        else:
            cinfo('    task promote-to-proposed is not \'Fix Released\'', 'yellow')

        cleave(s.__class__.__name__ + '._new (%s)' % (retval))
        return retval

    # _verify_release
    #
    def _verify_release(s):
        center(s.__class__.__name__ + '._verify_release')
        retval = False

        try:
            if s.snap_store.match_version('beta'):
                s.task.status = 'Fix Released'
                s.task.timestamp('finished')
                retval = True
            else:
                cinfo('    snap not in beta channel', 'yellow')
        except SnapStoreError as e:
            cerror('    failed to query snap store (%s)' % str(e))

        cleave(s.__class__.__name__ + '._verify_release (%s)' % (retval))
        return retval


class SnapReleaseToCandidate(KernelSnapBase):
    '''
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(SnapReleaseToCandidate, s).__init__(lp, task, bug)

        s.jumper['New']           = s._new
        s.jumper['Confirmed']     = s._verify_release
        s.jumper['Triaged']       = s._verify_release
        s.jumper['In Progress']   = s._verify_release
        s.jumper['Fix Committed'] = s._verify_release

        cleave(s.__class__.__name__ + '.__init__')

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        # The snap is released to candidate channel after it's on beta channel
        # and passes HW certification tests (or the task is set to invalid).
        while not retval:
            if s.bug.tasks_by_name['snap-release-to-beta'].status != 'Fix Released':
                cinfo('    task snap-release-to-beta is not \'Fix Released\'', 'yellow')
                break

            if (s.bug.tasks_by_name.get('snap-certification-testing', None) is not None
                    and s.bug.tasks_by_name['snap-certification-testing'].status not in ['Fix Released', 'Invalid']):
                cinfo('    task snap-certification-testing is neither \'Fix Released\' nor \'Invalid\'', 'yellow')
                break

            s.task.status = 'Confirmed'
            s.task.timestamp('started')

            retval = True
            break

        cleave(s.__class__.__name__ + '._new (%s)' % (retval))
        return retval

    # _verify_release
    #
    def _verify_release(s):
        center(s.__class__.__name__ + '._verify_release')
        retval = False

        try:
            if s.snap_store.match_version('candidate'):
                s.task.status = 'Fix Released'
                s.task.timestamp('finished')
                retval = True
            else:
                cinfo('    snap not in candidate channel', 'yellow')
        except SnapStoreError as e:
            cerror('    failed to query snap store (%s)' % str(e))

        cleave(s.__class__.__name__ + '._verify_release (%s)' % (retval))
        return retval


class SnapReleaseToStable(KernelSnapBase):
    '''
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(SnapReleaseToStable, s).__init__(lp, task, bug)

        s.jumper['New']           = s._new
        s.jumper['Confirmed']     = s._verify_release
        s.jumper['Triaged']       = s._verify_release
        s.jumper['In Progress']   = s._verify_release
        s.jumper['Fix Committed'] = s._verify_release

        cleave(s.__class__.__name__ + '.__init__')

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        # Set the task to invalid if 'stable' is not set on kernel-series-info.yaml
        if not s.snap_info.stable:
            cinfo('    not a stable snap', 'yellow')
            s.task.status = 'Invalid'
            retval = True

        # The snap is released to stable channel after it's on candidate channel,
        # passes QA tests (or the task is set to invalid) and the deb is promoted
        # to -updates or -security.
        while not retval:
            if s.bug.tasks_by_name['snap-release-to-candidate'].status != 'Fix Released':
                cinfo('    task snap-release-to-candidate is not \'Fix Released\'', 'yellow')
                break

            if (s.bug.tasks_by_name.get('snap-qa-testing', None) is not None
                    and s.bug.tasks_by_name['snap-qa-testing'].status not in ['Fix Released', 'Invalid']):
                cinfo('    task snap-qa-testing is neither \'Fix Released\' nor \'Invalid\'', 'yellow')
                break

            if s.bug.tasks_by_name['promote-to-updates'].status not in ['Fix Released', 'Invalid']:
                cinfo('    task promote-to-updates is neither \'Fix Released\' nor \'Invalid\'', 'yellow')
                break

            if (s.bug.tasks_by_name['promote-to-updates'].status == 'Invalid'
                    and s.bug.tasks_by_name['promote-to-security'].status not in ['Fix Released', 'Invalid']):
                cinfo('    task promote-to-updates is \'Invalid\' and promote-to-security is neither \'Fix Released\''
                      ' nor \'Invalid\'', 'yellow')
                break

            s.task.status = 'Confirmed'
            s.task.timestamp('started')

            retval = True
            break

        cleave(s.__class__.__name__ + '._new (%s)' % (retval))
        return retval

    # _verify_release
    #
    def _verify_release(s):
        center(s.__class__.__name__ + '._verify_release')
        retval = False

        try:
            if s.snap_store.match_version('stable'):
                s.task.status = 'Fix Released'
                s.task.timestamp('finished')
                retval = True
            else:
                cinfo('    snap not in stable channel', 'yellow')
        except SnapStoreError as e:
            cerror('    failed to query snap store (%s)' % str(e))

        cleave(s.__class__.__name__ + '._verify_release (%s)' % (retval))
        return retval


class SnapQaTesting(KernelSnapBase):
    '''
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(SnapQaTesting, s).__init__(lp, task, bug)

        s.jumper['New'] = s._new

        cleave(s.__class__.__name__ + '.__init__')

    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        # We only care about setting the task to 'Confirmed' when the
        # snap is published to the candidate channel.
        if s.bug.tasks_by_name['snap-release-to-candidate'].status == 'Fix Released':
            s.task.status = 'Confirmed'
            s.task.timestamp('started')
            retval = True
        else:
            cinfo('    task snap-release-to-candidate is not \'Fix Released\'', 'yellow')

        cleave(s.__class__.__name__ + '._new (%s)' % (retval))
        return retval


class SnapCertificationTesting(KernelSnapBase):
    '''
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(SnapCertificationTesting, s).__init__(lp, task, bug)

        s.jumper['New'] = s._new

        cleave(s.__class__.__name__ + '.__init__')

    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        # We only care about setting the task to 'Confirmed' when the
        # snap is published to the beta channel.
        if s.bug.tasks_by_name['snap-release-to-beta'].status == 'Fix Released':
            s.task.status = 'Confirmed'
            s.task.timestamp('started')
            retval = True
        else:
            cinfo('    task snap-release-to-beta is not \'Fix Released\'', 'yellow')

        cleave(s.__class__.__name__ + '._new (%s)' % (retval))
        return retval


class SnapPublish(KernelSnapBase):
        '''
        '''

        # __init__
        #
        def __init__(s, lp, task, bug):
            center(s.__class__.__name__ + '.__init__')
            super(SnapPublish, s).__init__(lp, task, bug)

            s.jumper['New']           = s._new
            s.jumper['Confirmed']     = s._verify_release
            s.jumper['Triaged']       = s._verify_release
            s.jumper['In Progress']   = s._verify_release
            s.jumper['Fix Committed'] = s._verify_release

            cleave(s.__class__.__name__ + '.__init__')

        # _new
        #
        def _new(s):
            center(s.__class__.__name__ + '._new')
            retval = False

            # If the snap has update control set up, the original publisher of the snap
            # needs to validate the new snap after it hits the stable channel.
            if s.bug.tasks_by_name['snap-release-to-stable'].status == 'Fix Released':
                s.task.status = 'Confirmed'
                s.task.timestamp('started')
                retval = True
            else:
                cinfo('    task snap-release-to-stable is not \'Fix Released\'', 'yellow')

            cleave(s.__class__.__name__ + '._new (%s)' % (retval))
            return retval

        # _verify_release
        #
        def _verify_release(s):
            center(s.__class__.__name__ + '._verify_release')
            retval = False
            # TODO: check if the snap has been un-gated
            cleave(s.__class__.__name__ + '._verify_release (%s)' % (retval))
            return retval

# vi: set ts=4 sw=4 expandtab syntax=python
