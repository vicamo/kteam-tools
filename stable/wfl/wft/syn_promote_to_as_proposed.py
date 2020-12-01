from datetime                                   import datetime, timedelta, timezone

from wfl.log                                    import center, cleave, cdebug, cinfo
from .base                                      import TaskHandler


class SynPromoteToAsProposed(TaskHandler):
    '''
    A Task Handler for the promote-to-as-proposed pseudo task.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(SynPromoteToAsProposed, s).__init__(lp, task, bug)

        # The tracking bug should start this task out as 'Confirmed'
        # for primary packages.  Derivatives should flip to 'Confirmed'
        # as soon as their primary is uploaded.
        #
        s.jumper['New']           = s._common
        s.jumper['Opinion']       = s._common
        s.jumper['Confirmed']     = s._common
        s.jumper['Triaged']       = s._common
        s.jumper['In Progress']   = s._common
        s.jumper['Fix Committed'] = s._common

        cleave(s.__class__.__name__ + '.__init__')

    # evaluate_state
    #
    #def evaluate_status(s, state):
    #    # We ARE aware of invalid bugs ... but need a valid package.
    #    if not s.bug.has_package:
    #        return False
    #    return s.jumper[state]()

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
            status_ptp = s.bug.task_status('promote-to-proposed')
            if (status_ptp == 'Invalid' or
                    s.bug.debs.routing('as-proposed') is None or
                    s.bug.source.private):
                if status_ptp == 'Invalid':
                    cinfo("promote-to-proposed: invalid, marking invalid")
                elif s.bug.debs.routing('as-proposed') is None:
                    cinfo("no as-proposed route, marking invalid")
                elif s.bug.source.private:
                    cinfo("source marked private, marking invalid")

                if s.task.status != 'Invalid':
                    s.task.status = 'Invalid'
                    retval = True
                break

            if status_ptp not in ('Fix Committed', 'Fix Released'):
                cinfo("promote-to-proposed: {}, waiting for likely completion".format(status_ptp))
                break

            if not s.bug.debs.all_built_and_in_pocket('Proposed'):
                cinfo("packages are not all in Proposed")
                break

            s.task.reason = 'Ongoing -- packages not yet published'

            if s.task.status not in ('Fix Committed', 'Fix Released'):
                cinfo("packages ready for copy, requesting")
                (dst_archive, dst_pocket) = s.bug.debs.routing('as-proposed')[0]
                for dep, package in s.bug.debs.pkgs.items():
                    (src_archive, src_pocket) = s.bug.debs.build_info[dep]['Proposed']['route']
                    cinfo("copying from {}:{}:{} to {}:{}:{} package {}:{}".format(src_archive, src_pocket, s.bug.series, dst_archive, dst_pocket, s.bug.series, dep, package))
                    dst_archive.copyPackage(
                        from_archive=src_archive, from_series=s.bug.series, from_pocket=src_pocket,
                        to_series=s.bug.series, to_pocket=dst_pocket,
                        source_name=package, version=s.bug.debs.build_info[dep]['Proposed']['version'],
                        include_binaries=True)
                if s.task.status != 'Fix Committed':
                    s.task.status = 'Fix Committed'
                    retval = True
                break

            if not s.bug.debs.all_built_and_in_pocket('as-proposed'):
                cinfo("packages are not all in as-proposed")
                break

            if s.task.status != 'Fix Released':
                s.task.status = 'Fix Released'
                retval = True
            break

        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
