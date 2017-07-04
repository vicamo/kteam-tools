
from wfl.log                                    import center, cleave, cdebug
from .base                                      import TaskHandler

class PreparePackageBase(TaskHandler):
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
        super(PreparePackageBase, s).__init__(lp, task, bug)

        # The tracking bug should start this task out as 'Confirmed'
        # for primary packages.  Derivatives should flip to 'Confirmed'
        # as soon as their primary is uploaded.
        #
        s.jumper['Confirmed']     = s._common
        s.jumper['Triaged']       = s._common
        s.jumper['In Progress']   = s._common
        s.jumper['Fix Committed'] = s._common

        cleave(s.__class__.__name__ + '.__init__')

    # evaluate_state
    #
    def evaluate_status(s, state):
        # We ARE aware of invalid bugs ...
        return s.jumper[state]()

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')

        retval = False
        while True:
            # For derivative bugs we wait until the parent has at least got its
            # primary package uploaded.  Then we must have something we _could_
            # rebase on.
            if s.bug.is_derivative_package:
                master = s.bug.master_bug
                if master.tasks_by_name['prepare-package'].status != 'Fix Released':
                    retval = False
                    break

            s.task.status = 'Confirmed'
            s.task.timestamp('started')
            s.bug.phase = 'Packaging'
            retval = True
            break

        cleave(s.__class__.__name__ + '._new (%s)' % (retval))
        return retval

    # _new_
    #
    def _new_dependent(s):
        center(s.__class__.__name__ + '._new_dependent')

        retval = False
        while True:
            # If our primary prepare-package has moved past Confirmed
            # we can move this one on as well.
            if s.bug.tasks_by_name['prepare-package'].status in ('New', 'Confirmed'):
                retval = False
                break

            s.task.status = 'Confirmed'
            s.task.timestamp('started')
            retval = True
            break

        cleave(s.__class__.__name__ + '._new_dependent (%s)' % (retval))
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

        while True:
            if not s.bug.is_valid:
                break

            # Since all the Prepare-package* packagestasks use this same method
            # we need to determine which one we are working this time. That gives
            # us the package to check if it's fully built.
            #
            pkg = s.task.name.replace('prepare-package', '').replace('-', '')
            if pkg == '':
                pkg = 'main'
            if not s.bug.uploaded(pkg):
                break

            s.bug.phase = 'Uploaded'
            s.task.status = 'Fix Released'
            s.task.timestamp('finished')
            try:
                s.task.assignee = s.bug.creator(pkg)
            except KeyError:
                # It doesn't matter if we set the assignee, that's just a nice
                # to have.
                #
                pass

            retval = True
            break

        cleave(s.__class__.__name__ + '._common (%s)' % (retval))
        return retval


class PreparePackage(PreparePackageBase):
    '''
    A Task Handler for the prepare-package task.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(PreparePackage, s).__init__(lp, task, bug)
        s.jumper['New']           = s._new
        cleave(s.__class__.__name__ + '.__init__')


class PreparePackageMeta(PreparePackageBase):
    '''
    A Task Handler for the prepare-package-meta task.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(PreparePackageMeta, s).__init__(lp, task, bug)
        s.jumper['New']           = s._new_dependent
        cleave(s.__class__.__name__ + '.__init__')


class PreparePackageSigned(PreparePackageBase):
    '''
    A Task Handler for the prepare-package-signed task.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(PreparePackageSigned, s).__init__(lp, task, bug)
        s.jumper['New']           = s._new_dependent
        cleave(s.__class__.__name__ + '.__init__')

class PreparePackageLBM(PreparePackageBase):
    '''
    A Task Handler for the prepare-package-lbm task.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(PreparePackageLBM, s).__init__(lp, task, bug)
        s.jumper['New']           = s._new_dependent
        cleave(s.__class__.__name__ + '.__init__')


class PreparePackagePortsMeta(PreparePackageBase):
    '''
    A Task Handler for the prepare-package-ports-meta task.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(PreparePackagePortsMeta, s).__init__(lp, task, bug)
        s.jumper['New']           = s._new_dependent
        cleave(s.__class__.__name__ + '.__init__')


# vi: set ts=4 sw=4 expandtab syntax=python
