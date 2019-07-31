from ktl.kernel_series                          import KernelSeries

from wfl.log                                    import center, cleave, cdebug, cinfo
from .base                                      import TaskHandler


class PreparePackage(TaskHandler):
    '''
    A Task Handler for the prepare-package task.

    States:

        - New
            Just move straight to Confirmed.

        - Confirmed / Triaged / In Progress / Fix Committed
            Keep checking for when all the packages are fully built. When
            they are, move this task to Fix Released

        - Fix Released
            We don't process when in this state. We're done.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(PreparePackage, s).__init__(lp, task, bug)

        # The tracking bug should start this task out as 'Confirmed'
        # for primary packages.  Derivatives should flip to 'Confirmed'
        # as soon as their primary is uploaded.
        #
        s.jumper['New']           = s._new
        s.jumper['Confirmed']     = s._common
        s.jumper['Triaged']       = s._common
        s.jumper['In Progress']   = s._common
        s.jumper['Fix Committed'] = s._common

        cleave(s.__class__.__name__ + '.__init__')

    # evaluate_state
    #
    def evaluate_status(s, state):
        # We ARE aware of invalid bugs ... but need a valid package.
        if not s.bug.has_package:
            return False
        return s.jumper[state]()

    # _kernel_block_source
    #
    def _kernel_block_source(s):
        '''
        If a 'kernel-block-source' tag exist return True.
        '''
        center(s.__class__.__name__ + '._kernel_block_source')
        retval = False

        if 'kernel-block' in s.bug.tags or 'kernel-block-source' in s.bug.tags:
            retval = True

        cleave(s.__class__.__name__ + '._kernel_block_source (%s)' % retval)
        return retval

    # _package_name
    #
    def _package_name(s):
        pkg = s.task.name.replace('prepare-package', '').replace('-', '')
        if pkg == '':
            pkg = 'main'
        return pkg

    # master_prepare_ready
    #
    def master_prepare_ready(s):
        if not s.bug.is_derivative_package:
            return True

        master = s.bug.master_bug
        if master.tasks_by_name['prepare-package'].status == 'Fix Released':
            return True

        return False


    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')

        retval = False
        while True:
            # Since all the Prepare-package* packagestasks use this same method
            # we need to determine which one we are working this time.
            pkg = s._package_name()

            # For derivative bugs we wait until the parent has at least got its
            # primary package uploaded.  Then we must have something we _could_
            # rebase on.
            if not s.master_prepare_ready():
                if pkg == 'main' or not s.bug.valid_package('main'):
                    s.task.reason = 'Holding -- waiting for master bug'
                break

            # Confirm whether this package is actually valid.
            if not s.bug.valid_package(pkg):
                s.task.status = 'Invalid'
                retval = True
                break

            # If we are not the primary-package and there is a primary package
            # hold us until the primary is handled, this keeps the todo list
            # short and sweet.  The very first thing we need to do is to set
            # the kernel version, so hold secondary packages pending that.
            if (pkg != 'main' and s.bug.valid_package('main') and
                not s.bug.is_valid
               ):
                retval = False
                break

            if s._kernel_block_source():
                s.task.reason = 'Stalled -- manual kernel-block/kernel-block-source present'
                break

            s.task.status = 'Confirmed'
            s.task.timestamp('started')
            retval = True
            break

        cleave(s.__class__.__name__ + '._new (%s)' % (retval))
        return retval

    # _common
    #
    def _common(s):
        '''
        Look to see if the packages have been fully built. This is our indication that the
        packages have been prepared and we can close this task.
        '''
        center(s.__class__.__name__ + '._common')
        retval = False

        while not retval:
            if s.task.status not in ('Confirmed'):
                break
            if not s._kernel_block_source() and s.master_prepare_ready():
                break

            if s._kernel_block_source():
                cinfo('            A kernel-block/kernel-block-source tag exists on this tracking bug pulling back from Confirmed', 'yellow')
            if not s.master_prepare_ready():
                cinfo('            Master kernel no longer ready pulling back from Confirmed', 'yellow')

            s.task.status = 'New'

            retval = True
            break

        while not retval:

            # If we do not have a version then whine about that.
            if not s.bug.is_valid:
                s.task.reason = 'Pending -- version not specified'
                break

            # Since all the Prepare-package* packagestasks use this same method
            # we need to determine which one we are working this time.
            #
            pkg = s._package_name()

            # Confirm whether this package is actually valid
            if not s.bug.valid_package(pkg):
                s.task.status = 'Invalid'
                retval = True
                break

            # Confirm that this package is uploaded.
            if not s.bug.debs.uploaded(pkg):
                s.task.reason = 'Pending -- package not yet uploaded'
                break

            # Check the package tag has been published.
            if not s.bug.published_tag(pkg):
                s.task.reason = 'Stalled -- package tag not yet published'
                break

            s.task.status = 'Fix Released'
            s.task.timestamp('finished')
            try:
                s.task.assignee = s.bug.debs.creator(pkg)
            except KeyError:
                # It doesn't matter if we set the assignee, that's just a nice
                # to have.
                #
                pass

            retval = True
            break

        cleave(s.__class__.__name__ + '._common (%s)' % (retval))
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
