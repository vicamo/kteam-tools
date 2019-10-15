<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<style>
a:link {
    color: green; 
    background-color: transparent; 
    text-decoration: none;
}

a:visited {
    color: green; 
    background-color: transparent;
    text-decoration: none;
}
</style>
<% #>

# https://www.viget.com/articles/color-contrast/

__testing_status_colors = {
    'New'           : 'blue',
    'In Progress'   : 'grey', # 'white',
    'Confirmed'     : 'darkorange', # '#1496bb', # 'yellow',
    'Incomplete'    : 'red',
    'Invalid'       : 'grey',
    'Fix Released'  : 'green', # '#1496bb',
    'Fix Committed' : '#1496bb',
    'Task missing'  : 'red',
    'unknown'       : 'magenta',
    'n/a'           : 'grey',
}
%>
<%

def __task_status(bug, task_name):
    try:
        return bug['task'][task_name].get('status','missing %s' % task_name)
    except KeyError:
        pass
    return 'n/a'

%>
<%

def __assignee(bug, task_name):
    try:
        return bug['task'][task_name]['assignee']
    except KeyError:
        return 'unknown'
    return

%>
<%

def __coloured(msg, colour='black'):
    return '<span style="color: %s;font-weight: bold">%s</span>' % (colour, msg)

%>
<%
import textwrap

# bite_format
#
def bite_format(thing_prefix, payload, thing_in):
    bite = '<span style="display: inline-block; min-width: 20px; width=20px;">{}</span>'.format(thing_prefix)
    bite += '<span style="display: inline-block; min-width: 400px; width=400px;">{}</span>'.format(payload)
    if len(thing_in) != 0:
        if payload[-2:] not in ('', '  '):
            bite += '  '
        bite += 'in: ' + ','.join(thing_in)
    return bite

# status_bites
#
def __status_bites(bug):
    bites = []

    thing_prefix = '?:'
    thing_in = []

    # Report Debs release progress -- run through the prepare-package
    # tasks and find the more retrograde one and report on that.
    prep_status = 'n/a'
    for prep_task in sorted(bug.get('reason', {}).keys()):
        if not prep_task.startswith('prepare-package'):
            continue
        prep_status = __task_status(bug, prep_task)
        if prep_status in ('Invalid', 'Fix Released'):
            continue
        prep_task = 'prepare-package-meta'
        prep_status = __task_status(bug, prep_task)
        break

    if bug['variant'] in ('debs', 'combo'):
        thing_prefix = 'd:'
        security_status = __task_status(bug, 'promote-to-security')
        updates_status  = __task_status(bug, 'promote-to-updates')
        proposed_status = __task_status(bug, 'promote-to-proposed')
        if prep_status in ('Fix Committed', 'Fix Released'):
            thing_in.append('ppa')
        if proposed_status in ('Fix Released'):
            thing_in.append('proposed')
        if updates_status in ('Fix Released'):
            thing_in.append('updates')
        if security_status in ('Fix Released'):
            thing_in.append('security')

    # Report Snap release progress.
    if bug['variant'] == 'snap-debs':
        thing_prefix = 's:'
        for risk in ['edge', 'beta', 'candidate', 'stable']:
            status = __task_status(bug, 'snap-release-to-' + risk)
            if status == 'Fix Released':
                thing_in.append(risk)

    # debs: being prepared?
    retval = ''
    if prep_status == 'New':
        retval = __coloured('Not ready to be cranked', 'grey')
    elif prep_status == 'Confirmed':
        retval = __coloured('Debs ready to be cranked', 'darkorange') #bca136
    elif prep_status == 'In Progress':
        retval = __coloured('Being cranked by: %s' % (__assignee(bug, prep_task)), '#1496bb')
    elif prep_status == 'Fix Committed':
        retval = __coloured('Uploaded by: %s' % (__assignee(bug, prep_task)), '#1496bb')
    if retval != '':
        bites.append(bite_format(thing_prefix, retval, thing_in))
        thing_in = []

    # debs: testing status mashup.
    automated_testing_status = __task_status(bug, 'automated-testing')
    certification_testing_status = __task_status(bug, 'certification-testing')
    regression_testing_status = __task_status(bug, 'regression-testing')
    verification_testing_status = __task_status(bug, 'verification-testing')
    testing_valid = (
            automated_testing_status not in ('n/a', 'New', 'Invalid') or
            certification_testing_status not in ('n/a', 'New', 'Invalid') or
            regression_testing_status not in ('n/a', 'New', 'Invalid') or
            verification_testing_status not in ('n/a', 'New', 'Invalid'))
    testing_complete = (
            automated_testing_status in ('n/a', 'Invalid', 'Fix Released') and
            certification_testing_status in ('n/a', 'Invalid', 'Fix Released') and
            regression_testing_status in ('n/a', 'Invalid', 'Fix Released') and
            verification_testing_status in ('n/a', 'Invalid', 'Fix Released'))
    if testing_valid and not testing_complete:
        retval = ''

        color = __testing_status_colors[automated_testing_status]
        retval += '<span style="display: inline-block; min-width: 100px; width=100px;">at: %-26s</span>' % (__coloured(automated_testing_status, color))

        color = __testing_status_colors[certification_testing_status]
        retval += '<span style="display: inline-block; min-width: 100px; width=100px;">ct: %-26s</span>' % (__coloured(certification_testing_status, color))

        color = __testing_status_colors[regression_testing_status]
        retval += '<span style="display: inline-block; min-width: 100px; width=100px;">rt: %-26s</span>' % (__coloured(regression_testing_status, color))

        color = __testing_status_colors[verification_testing_status]
        retval += '<span style="display: inline-block; min-width: 100px; width=100px;">vt: %-26s</span>' % (__coloured(verification_testing_status, color))

        bites.append(bite_format(thing_prefix, retval, thing_in))
        thing_in = []

    # snaps: being prepared?
    retval = ''
    prep_status = __task_status(bug, 'snap-release-to-edge')
    if prep_status == 'New':
        retval = __coloured('Not ready to be cranked', 'grey')
    elif prep_status == 'Confirmed':
        retval = __coloured('Snap ready to be cranked', 'darkorange')
    elif prep_status == 'In Progress':
        retval = __coloured('Being cranked by: %s' % (__assignee(bug, 'prepare-package')), '#1496bb')
    elif prep_status == 'Fix Committed':
        retval = __coloured('Uploaded by: %s' % (__assignee(bug, 'prepare-package')), '#1496bb')
    if retval != '':
        bites.append(bite_format(thing_prefix, retval, thing_in))
        thing_in = []
    promote_to = []
    for risk in ('beta', 'candidate', 'stable'):
        promote_status = __task_status(bug, 'snap-release-to-' + risk)
        if promote_status == 'Confirmed':
            promote_to.append(risk)
    if len(promote_to) > 0:
        retval = __coloured("Snap ready to promote to: " + ', '.join(promote_to), 'darkorange')
        bites.append(bite_format(thing_prefix, retval, thing_in))
        thing_in = []

    # snaps: testing status mashup.
    certification_testing_status = __task_status(bug, 'snap-certification-testing')
    qa_testing_status = __task_status(bug, 'snap-qa-testing')
    testing_valid = (
            certification_testing_status not in ('n/a', 'New', 'Invalid') or
            qa_testing_status not in ('n/a', 'New', 'Invalid'))
    testing_complete = (
            certification_testing_status in ('n/a', 'Invalid', 'Fix Released') and
            qa_testing_status in ('n/a', 'Invalid', 'Fix Released'))
    if testing_valid and not testing_complete:
        retval = ''

        color = __testing_status_colors[certification_testing_status]
        retval += '<span style="display: inline-block; min-width: 100px; width=100px;">ct: %-26s</span>' % (__coloured(certification_testing_status, color))

        color = __testing_status_colors[qa_testing_status]
        retval += '<span style="display: inline-block; min-width: 100px; width=100px;">qa: %-26s</span>' % (__coloured(qa_testing_status, color))

        bites.append(bite_format(thing_prefix, retval, thing_in))
        thing_in = []

    # Run the list of reasons swm is reporting and emit those that do not overlap with testing.
    status_colour = {
            'Pending': 'darkorange', #'#bca136',
            'Ongoing': '#1496bb',
            'Holding': 'grey',
            'Stalled': 'crimson',
            'Alert':   'red',
        }
    for task in sorted(bug.get('reason', {}).keys()):
        reason = bug['reason'][task]
        if ((task.startswith('prepare-package') or
                task.startswith('snap-release-to-')) and
                not reason.startswith('Stalled -- ')):
            continue
        if task.endswith('-testing'):
            continue
        if bug.get('master-bug') is not None:
            if task == 'security-signoff':
                continue
        (state, _, reason) = reason.split(' ', 2)
        colour = status_colour.get(state, 'blue')
        retval = '{}: {}'.format(task, reason)
        thing_prefix_wrap = thing_prefix
        for line in textwrap.wrap(retval, width=80):
            if len(line) > 83:
                 line= line[:80] + '...'
            line = __coloured(line, colour)
            bites.append(bite_format(thing_prefix_wrap, line, thing_in))
            thing_in = []
            thing_prefix_wrap = ''

    # We have nothing to say ... so use the phase as a hint.
    if len(bites) == 0:
        retval = bug.get('phase', 'Holding not ready')
        state = retval.split(' ', 1)[0]
        colour = status_colour.get(state, 'blue')
        retval = __coloured(retval, colour)

        bites.append(bite_format(thing_prefix, retval, thing_in))
        thing_in = []

    return bites

%>
<%
import re

cycles = {}
cadence = {}
for bid in sorted(data['swm']):
    b = data['swm'][bid]

    try:
        cycle = 'unknown'
        spin = '?'
        if 'cycle' in b:
            (cycle, spin) = (b['cycle'].split('-') + ['?'])[0:2]

        package = b.get('source', 'unknown')
        version = b.get('version', '-')

        if 'snap-name' in b:
            package = package + ' / ' + b['snap-name']
    except:
        cycle = 'unknown'
        package = 'unknown'
        version = 'unknown'

    cycles[cycle] = True

    phase = b.get('phase', 'unknown (no phase set)')

    sn = b.get('series', 'unknown')

    if cycle not in cadence:
        cadence[cycle] = {}
    if sn not in cadence[cycle]:
        cadence[cycle][sn] = {}
    if package not in cadence[cycle][sn]:
        cadence[cycle][sn][package] = []

    status_list = __status_bites(b)
    first = True
    for status in status_list:
        # Fixup the link to the regression testing if this is 'testing' status.
        #
        if 'rt:' in status:
            try:
                status = re.sub(r'(rt: *<span.*?</span>)', r'<a href="%s">\1</a>' % data['testing']['regression'][package], status)
            except KeyError:
                pass

        # Fixup the link to the automated testing results
        #
        if 'at:' in status:
            status = re.sub(r'(at: *<span.*?</span>)', r'<a href="%s">\1</a>' % 'http://people.canonical.com/~kernel/status/adt-matrix/%s-%s.html' % (sn, package.replace('linux', 'linux-meta')), status)

        # Fixup the link to the sru-report with verification status
        #
        if 'vt:' in status:
            status = re.sub(r'(vt: *<span.*?</span>)', r'<a href="%s">\1</a>' % 'http://kernel.ubuntu.com/reports/sru-report.html', status)

        if first:
            cadence[cycle][sn][package].append({ 'bug': bid, 'version': version, 'phase': status, 'spin': spin })
            first = False
        else:
            cadence[cycle][sn][package].append({ 'bug': None, 'version': None, 'phase': status, 'spin': spin })

%>
<html xmlns="http://www.w3.org/1999/xhtml" dir="ltr" lang="en-US">
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
        <!-- <meta http-equiv="refresh" content="60" /> -->
        <title>${config['title']}</title>
        <link rel="stylesheet" href="http://kernel.ubuntu.com/sru/dashboards/web/media/dashboard.css" type="text/css" media="screen" />
    </head>


    <body class="dash-body">
        <div class="dash-center-wrap">
            <div class="dash-center">
                <div class="dash-center-content">

                    <div id="dash-header">
                        <div id="dash-timestamp">
                            <p>Generated on ${timestamp}</p>
                        </div>
                        <h1>Kernel Team Dashboard</h1>
                    </div> <!-- header -->

                    <div class="dash-section">
                        <table width="100%"> <!-- The section is one big table -->
                            <tr>
                                <td width="100%" valign="top"> <!-- LEFT -->
                                    <!--
                                    <table width="100%"> <tr><td><h3><a href="http://people.canonical.com/~kernel/reports/sru-report.html">SRUs</a></h3></td></tr> <tr><td><hr /></td></tr> </table>
                                    -->
                                    <table width="100%" style="font-size: 0.8em"> <!-- SRU Data -->
                                    <%
                                        releases = data['releases']
                                        releases['00.00'] = 'unknown'
                                        cycle_first = True
                                    %>
                                    % for cycle in sorted(cycles):
                                        % if cycle_first is False:
                                            <tr>
                                                <td colspan="5">&nbsp;</td>
                                            </tr>
                                        % endif
                                        <tr>
                                            <td colspan="5" style="background: #ffffc0; font-size: 140%; ">${cycle}</td>
                                        </tr>
                                        <%
                                            cycle_first = False
                                        %>
                                        % for rls in sorted(releases, reverse=True):
                                            <%
                                                codename = releases[rls].capitalize()
                                            %>
                                            % if releases[rls] in cadence[cycle]:
                                            <tr>
                                                <td colspan="5" style="background: #e9e7e5;">${rls} &nbsp;&nbsp; ${codename}</td>
                                            </tr>
                                                % for pkg in sorted(cadence[cycle][releases[rls]]):
                                                    % for bug in cadence[cycle][releases[rls]][pkg]:
                                                        <tr style="line-height: 100%">
                                                            <td>&nbsp;</td>
                                                            <%
                                                                cell_version = '&nbsp;'
                                                                cell_package = '&nbsp;'
                                                                cell_spin = '&nbsp;'
                                                                if bug['bug'] is not None:
                                                                    url = "https://bugs.launchpad.net/ubuntu/+source/linux/+bug/%s" % bug['bug']
                                                                    cell_version = '<a href="{}">{}</a>'.format(url, bug['version'])
                                                                    cell_package = '<a href="{}">{}</a>'.format(url, pkg)
                                                                    cell_spin = '#{}'.format(bug['spin'])
                                                            %>
                                                            <td width="120" align="right" style="color: green">${cell_version}</td>
                                                            <td style="color: green">${cell_package}</a></td>
                                                            <td style="color: grey">${cell_spin}</td>
                                                            <td>${bug['phase']}</td>
                                                        </tr>
                                                    % endfor
                                                % endfor
                                            % endif
                                        % endfor
                                    % endfor
                                    </table>
                                </td>
                                <!--
                                <td width="10%">&nbsp;</td>
                                <td width="45%" valign="top">
                                </td>
                                -->
                            </tr>
                        </table>
                    </div> <!-- dash-section -->
                </div>
            </div>
        -</div>
    </body>

</html>
<!-- vi:set ts=4 sw=4 expandtab: -->
