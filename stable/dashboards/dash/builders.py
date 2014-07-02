#!/usr/bin/env python
#

from dash.dbg                            import Dbg

# Builders
#
class Builders(dict):
    """
    A dictionary of LP build farm builders.
    """

    # __init__
    #
    def __init__(self, lp, *args):
        Dbg.enter("Builders.__init__")

        dict.__init__(self, args)

        self.lp = lp
        builders = self.lp.builders
        farm = {}
        for builder in builders:
            b = {}
            b['active']        = builder.active
            b['builderok']     = builder.builderok
            try:
                b['description']   = builder.description
            except:
                b['description']   = ''
            b['failnotes']     = builder.failnotes
            b['failure_count'] = builder.failure_count
            b['manual']        = builder.manual
            b['name']          = builder.name
            #b['owner']          = builder.owner
            b['processor']     = builder.processor.name
            b['title']         = builder.title
            b['virtualized']   = builder.virtualized
            b['vm_host']       = builder.vm_host
            b['web_link']      = builder.web_link
            #b['resource']      = builder.resource_type

            self[builder.name] = b

        Dbg.leave("Builders.__init__")

    # queues
    #
    def queues(self):
        Dbg.enter("Builders.queues")
        retval = self.lp.builders.getBuildQueueSizes()
        Dbg.leave("Builders.queues")
        return retval

    # stats
    #
    def stats(self):
        Dbg.enter("Builders.stats")
        available = 0
        disabled  = 0
        manual    = 0
        ppa = {}
        distro_builder = {}
        virt = {}
        nonvirt = {}
        for builder in self:
            b = self[builder]
            if b['builderok']:
                available   += 1

                if b['virtualized']:
                    ppa[builder] = b
                    try:
                        virt[b['processor']]['available'] += 1
                    except KeyError:
                        virt[b['processor']] = {}
                        virt[b['processor']]['available'] = 1
                        virt[b['processor']]['disabled'] = 0

                else:
                    distro_builder[builder] = b
                    try:
                        nonvirt[b['processor']]['available'] += 1
                    except KeyError:
                        nonvirt[b['processor']] = {}
                        nonvirt[b['processor']]['available'] = 1
                        nonvirt[b['processor']]['disabled'] = 0

            else:
                disabled += 1

                if b['virtualized']:
                    ppa[builder] = b
                    try:
                        virt[b['processor']]['disabled'] += 1
                    except KeyError:
                        virt[b['processor']] = {}
                        virt[b['processor']]['disabled'] = 1
                        virt[b['processor']]['available'] = 0

                else:
                    distro_builder[builder] = b
                    try:
                        p = nonvirt[b['processor']]
                        nonvirt[b['processor']]['disabled'] += 1
                    except KeyError:
                        nonvirt[b['processor']] = {}
                        nonvirt[b['processor']]['disabled'] = 1
                        nonvirt[b['processor']]['available'] = 0

            if b['manual']:
                manual += 1

        queues = self.queues()

        stats = {
            'totals' : {
                'registered' : len(self),
                'available'  : available,
                'disabled'   : disabled,
                'manual'     : manual,
                'auto'       : available - manual
            }
        }
        stats['nonvirt'] = {}
        for proc in sorted(nonvirt):
            stats['nonvirt'][proc] = {}
            try:
                (jobs, estimate) = queues['nonvirt'][proc]
                queue = "%d jobs" % (jobs)
            except KeyError:
                queue = 'empty'

            stats['nonvirt'][proc]['available'] = nonvirt[proc]['available']
            stats['nonvirt'][proc]['disabled'] = nonvirt[proc]['disabled']
            stats['nonvirt'][proc]['queue'] = queue

        stats['virt'] = {}
        for proc in sorted(virt):
            stats['virt'][proc] = {}
            try:
                (jobs, estimate) = queues['virt'][proc]
                queue = "%d jobs" % (jobs)
            except KeyError:
                queue = 'empty'

            stats['virt'][proc]['available'] = virt[proc]['available']
            stats['virt'][proc]['disabled'] = virt[proc]['disabled']
            stats['virt'][proc]['queue'] = queue

        Dbg.leave("Builders.stats")
        return stats

# vi:set ts=4 sw=4 expandtab:
