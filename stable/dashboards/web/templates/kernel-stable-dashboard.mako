<% #>

# https://www.viget.com/articles/color-contrast/

__testing_status_colors = {
    'New'           : 'grey',
    'In Progress'   : 'grey', # 'white',
    'Confirmed'     : 'darkorange', # '#1496bb', # 'yellow',
    'Triaged'       : 'orange',
    'Incomplete'    : 'red',
    'Invalid'       : 'grey',
    'Fix Released'  : 'green', # '#1496bb',
    'Fix Committed' : '#1496bb',
    'Task missing'  : 'red',
    'unknown'       : 'magenta',
    'n/a'           : 'grey',
    "Won't Fix"     : 'red',
    'Opinion'       : 'red',
}
__testing_status_text = {
    'New'           : 'Not Ready',
    'In Progress'   : 'In Progress',
    'Confirmed'     : 'Ready',
    'Triaged'       : 'No Results',
    'Incomplete'    : 'Failed',
    'Fix Released'  : 'Passed',
    'Opinion'       : 'Aborted',
}
__review_status_colors = __testing_status_colors
__review_status_text = {
    'New'           : 'Not Ready',
    'In Progress'   : 'In Progress',
    'Confirmed'     : 'Ready',
    'Incomplete'    : 'Rejected',
    'Fix Released'  : 'Approved',
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
    return '<span style="color: %s">%s</span>' % (colour, msg)

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
        bite += 'in: ' + __coloured('/', 'silver').join(thing_in)
        # We have consumed the thing_in specifier, clear it out.
        thing_in[:] = []
    return bite

# tagged_block
#
def tagged_block(key, value):
    retval = '<span style="display: inline-block; min-width: 20px; width=20px;">{}</span>'.format(key)
    retval += '<span style="display: inline-block; min-width: 80px; width=80px;">{}</span>'.format(value)
    return retval

# tagged_block_valid
#
def tagged_block_valid(key, value, colour):
    key_title = key
    if 'tooltip-' + key in attrs:
        key_title = '<span title="{}">{}</span>'.format(attrs['tooltip-' + key], key)
    if value in ('n/a', 'Invalid'):
        return tagged_block(__coloured(key_title, 'silver'), __coloured('n/a', 'silver'))
    elif value == "Won't Fix":
        return tagged_block(__coloured(key_title, 'silver'), __coloured('Skipped', 'silver'))
    else:
        block = tagged_block(key_title, __coloured(value, colour))
        if key in attrs:
            block = '<a href="{}">{}</a>'.format(attrs[key], block)
        return block

def add_in(thing_in, where, state):
    in_colours = {
        'New'           : 'silver',
        'Confirmed'     : 'silver',
        'In Progress'   : 'orange',
        'Fix Committed' : 'orange',
        'Fix Released'  : 'default',
        'Incomplete'    : 'red',
    }
    colour = in_colours.get(state)
    if colour is not None:
        if colour != 'default':
            where = __coloured(where, colour)
        thing_in.append(where)

# status_bites
#
def __status_bites(bug, attrs):
    bites = []

    thing_prefix = '?:'
    thing_in = []

    # Report Debs release progress -- run through the prepare-package
    # tasks and find the more retrograde one and report on that.
    prep_states = {}
    for task, task_data in bug.get('task', {}).items():
        if task.startswith('prepare-package'):
            prep_states[task_data['status']] = task
    for prep_status in ['In Progress', 'Fix Committed', 'Confirmed', 'New', 'Fix Released']:
        if prep_status in prep_states:
            prep_task = prep_states[prep_status]
            break

    if bug.get('variant') in ('debs', 'combo'):
        thing_prefix = 'd:'
        security_status = __task_status(bug, 'promote-to-security')
        updates_status  = __task_status(bug, 'promote-to-updates')
        proposed_status = __task_status(bug, 'promote-to-proposed')
        release_status = __task_status(bug, 'promote-to-release')
        if proposed_status in ('n/a', 'Invalid'):
            add_in(thing_in, 'source-only', prep_status)
        else:
            add_in(thing_in, 'ppa', prep_status)
            add_in(thing_in, 'proposed', proposed_status)
            add_in(thing_in, 'updates', updates_status)
            add_in(thing_in, 'security', security_status)
            add_in(thing_in, 'release', release_status)

    # Report Snap release progress.
    if bug.get('variant') == 'snap-debs':
        thing_prefix = 's:'
        for risk in ['edge', 'beta', 'candidate', 'stable']:
            status = __task_status(bug, 'snap-release-to-' + risk)
            add_in(thing_in, risk, status)

    # State sets.
    test_set_invalid = ('n/a', 'New', 'Invalid')
    test_set_complete = ('n/a', 'Invalid', 'Fix Released', "Won't Fix")

    # debs: testing status mashup (early phase Touch Testing)
    boot_testing_status = __task_status(bug, 'boot-testing')
    sru_review_status = __task_status(bug, 'sru-review')
    testing_valid = (
            boot_testing_status not in test_set_invalid or
            sru_review_status not in test_set_invalid)
    testing_complete = (
            boot_testing_status in test_set_complete and
            sru_review_status in test_set_complete)
    if testing_valid and not testing_complete:
        retval = ''

        color = __testing_status_colors[boot_testing_status]
        boot_testing_status = __testing_status_text.get(boot_testing_status, boot_testing_status)
        retval += tagged_block_valid('bt:', boot_testing_status, color)
        retval += tagged_block('', '')
        retval += tagged_block('', '')
        color = __review_status_colors[sru_review_status]
        sru_review_status = __review_status_text.get(sru_review_status, sru_review_status)
        retval += tagged_block_valid('sr:', sru_review_status, color)

        bites.append(bite_format(thing_prefix, retval, thing_in))

    # debs: testing status mashup (main phase Testing)
    automated_testing_status = __task_status(bug, 'automated-testing')
    certification_testing_status = __task_status(bug, 'certification-testing')
    regression_testing_status = __task_status(bug, 'regression-testing')
    verification_testing_status = __task_status(bug, 'verification-testing')
    testing_valid = (
            automated_testing_status not in test_set_invalid or
            certification_testing_status not in test_set_invalid or
            regression_testing_status not in test_set_invalid or
            verification_testing_status not in test_set_invalid)
    testing_complete = (
            automated_testing_status in test_set_complete and
            certification_testing_status in test_set_complete and
            regression_testing_status in test_set_complete and
            verification_testing_status in test_set_complete)
    if testing_valid and not testing_complete:
        retval = ''

        color = __testing_status_colors[automated_testing_status]
        automated_testing_status = __testing_status_text.get(automated_testing_status, automated_testing_status)
        retval += tagged_block_valid('at:', automated_testing_status, color)

        color = __testing_status_colors[certification_testing_status]
        certification_testing_status = __testing_status_text.get(certification_testing_status, certification_testing_status)
        retval += tagged_block_valid('ct:', certification_testing_status, color)

        color = __testing_status_colors[regression_testing_status]
        regression_testing_status = __testing_status_text.get(regression_testing_status, regression_testing_status)
        retval += tagged_block_valid('rt:', regression_testing_status, color)

        color = __testing_status_colors[verification_testing_status]
        verification_testing_status = __testing_status_text.get(verification_testing_status, verification_testing_status)
        retval += tagged_block_valid('vt:', verification_testing_status, color)

        bites.append(bite_format(thing_prefix, retval, thing_in))

    # snaps: being prepared?
    retval = ''
    promote_to = []
    for risk in ('beta', 'candidate', 'stable'):
        promote_status = __task_status(bug, 'snap-release-to-' + risk)
        if promote_status == 'Confirmed':
            promote_to.append(risk)
    if len(promote_to) > 0:
        retval = __coloured("Snap ready to promote to: " + ', '.join(promote_to), 'darkorange')
        bites.append(bite_format(thing_prefix, retval, thing_in))

    # snaps: testing status mashup.
    certification_testing_status = __task_status(bug, 'snap-certification-testing')
    qa_testing_status = __task_status(bug, 'snap-qa-testing')
    testing_valid = (
            certification_testing_status not in test_set_invalid or
            qa_testing_status not in test_set_invalid)
    testing_complete = (
            certification_testing_status in test_set_complete and
            qa_testing_status in test_set_complete)
    if testing_valid and not testing_complete:
        retval = ''

        color = __testing_status_colors[certification_testing_status]
        certification_testing_status = __testing_status_text.get(certification_testing_status, certification_testing_status)
        retval += tagged_block_valid('ct:', certification_testing_status, color)

        color = __testing_status_colors[qa_testing_status]
        qa_testing_status = __testing_status_text.get(qa_testing_status, qa_testing_status)
        retval += tagged_block_valid('qa:', qa_testing_status, color)

        bites.append(bite_format(thing_prefix, retval, thing_in))

    # signoffs: report signoffs together..
    security_signoff_status = __task_status(bug, 'security-signoff')
    kernel_signoff_status = __task_status(bug, 'kernel-signoff')
    stakeholder_signoff_status = __task_status(bug, 'stakeholder-signoff')
    signoff_valid = (
            security_signoff_status not in ('n/a', 'New', 'Invalid') or
            kernel_signoff_status not in ('n/a', 'New', 'Invalid') or
            stakeholder_signoff_status not in ('n/a', 'New', 'Invalid'))
    signoff_complete = (
            security_signoff_status in ('n/a', 'Invalid', 'Fix Released') and
            kernel_signoff_status in ('n/a', 'Invalid', 'Fix Released') and
            stakeholder_signoff_status in ('n/a', 'Invalid', 'Fix Released'))
    if signoff_valid and not signoff_complete:
        retval = ''

        color = __testing_status_colors[security_signoff_status]
        retval += tagged_block_valid('ss:', security_signoff_status, color)

        color = __testing_status_colors[stakeholder_signoff_status]
        retval += tagged_block_valid('Ss:', stakeholder_signoff_status, color)

        color = __testing_status_colors[kernel_signoff_status]
        retval += tagged_block_valid('ks:', kernel_signoff_status, color)

        bites.append(bite_format(thing_prefix, retval, thing_in))

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
        if (task.startswith('prepare-package') and
                not reason.startswith('Stalled -- ')):
            continue
        # Elide things which are on one of the three "status box" rows.
        if task.endswith('-testing') or task.endswith('-signoff') or task == 'sru-review':
            continue
        (state, flags, reason) = reason.split(' ', 2)
        colour = status_colour.get(state, 'blue')
        # Initial tasks are emitted without their task name.
        if 'b' in flags:
            retval = reason
        else:
            human_task = task[1:] if task[0] == ':' else task
            retval = '{}: {}'.format(human_task, reason)
        thing_prefix_wrap = thing_prefix
        for line in textwrap.wrap(retval, width=80):
            if len(line) > 83:
                 line= line[:80] + '...'
            line = __coloured(line, colour)
            bites.append(bite_format(thing_prefix_wrap, line, thing_in))
            thing_prefix_wrap = ''

    # We have nothing to say ... so use the phase as a hint.
    if len(bites) == 0:
        retval = bug.get('phase', 'Holding not ready')
        state = retval.split(' ', 1)[0]
        if state == 'Complete':
            colour = 'blue'
        else:
            colour = 'red'
        #colour = status_colour.get(state, 'blue')
        retval = __coloured(retval, colour)

        bites.append(bite_format(thing_prefix, retval, thing_in))

    return bites

%>
<%
import re
import urllib.parse

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

    # Pull together any suplemental links etc we need.
    attrs = {}
    attrs['at:'] = 'http://people.canonical.com/~kernel/status/adt-matrix/{}-{}.html'.format(sn, package.replace('linux', 'linux-meta'))
    attrs['vt:'] = 'http://kernel.ubuntu.com/reports/sru-report.html#{}--{}'.format(sn, package)
    attrs['rt:'] = 'http://10.246.75.167/{}/rtr-lvl1.html#{}:{}:{}:sru'.format(cycle, sn, package, urllib.parse.quote_plus(version))
    attrs['bt:'] = 'http://10.246.75.167/{}/rtr-lvl1.html#{}:{}:{}:boot'.format(cycle, sn, package, urllib.parse.quote_plus(version))

    attrs['tooltip-at:'] = 'Automated Testing'
    attrs['tooltip-ct:'] = 'Certification Testing'
    attrs['tooltip-rt:'] = 'Regression Testing'
    attrs['tooltip-vt:'] = 'Verification Testing'
    attrs['tooltip-bt:'] = 'Boot Testing'
    attrs['tooltip-ss:'] = 'Security Signoff'
    attrs['tooltip-Ss:'] = 'Stakeholder Signoff'
    attrs['tooltip-ks:'] = 'Kernel Signoff'
    attrs['tooltip-sr:'] = 'SRU Review'

    status_list = __status_bites(b, attrs)
    first = True
    #row_style = ' background: #f0f0f0;' if row_number % 2 == 0 else ''
    row_class = ['entry-any']
    master_class = 'master' if 'master-bug' not in b else 'derivative'

    for status in status_list:
        status_row = {'bug': None, 'version': None, 'phase': status, 'spin': spin, 'master-class': master_class, 'row-class': ' '.join(row_class)}
        if first:
            status_row['bug'] = bid
            status_row['version'] = version
            first = False
        cadence[cycle][sn][package].append(status_row)

%>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" dir="ltr" lang="en-US">
    <head>
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
        .master a:link {
            color: darkblue;
            background-color: transparent;
            text-decoration: none;
        }

        .master a:visited {
            color: darkblue;
            background-color: transparent;
            text-decoration: none;
        }
        </style>
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
                                    <tr><td>
                                    </td></tr>

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
                                                row_number = 0
                                            %>
                                            % if releases[rls] in cadence[cycle]:
                                            <tr>
                                                <td colspan="5" style="background: #e9e7e5;">${rls} &nbsp;&nbsp; ${codename}</td>
                                            </tr>
                                                % for pkg in sorted(cadence[cycle][releases[rls]]):
                                                    % for bug in cadence[cycle][releases[rls]][pkg]:
                                                        <%
                                                            cell_version = '&nbsp;'
                                                            cell_package = '&nbsp;'
                                                            cell_spin = '&nbsp;'
                                                            if bug['bug'] is not None:
                                                                url = "https://bugs.launchpad.net/ubuntu/+source/linux/+bug/%s" % bug['bug']
                                                                cell_version = '<a href="{}">{}</a>'.format(url, bug['version'])
                                                                cell_package = '<a href="{}">{}</a>'.format(url, pkg)
                                                                cell_spin = '#{}'.format(bug['spin'])
                                                                row_number += 1
                                                            row_style = ' background: #f6f6f6;' if row_number % 2 == 0 else ''
                                                        %>
                                                        <tr class="${bug['row-class']}" style="line-height: 100%;${row_style}">
                                                            <td>&nbsp;</td>
                                                            <td width="120" align="right" class="${bug['master-class']}">${cell_version}</td>
                                                            <td class="${bug['master-class']}">${cell_package}</a></td>
                                                            <td style="color: grey">${cell_spin}</td>
                                                            <td>${bug['phase']}</td>
                                                        </tr>
                                                    % endfor
                                                % endfor
                                            % endif
                                        % endfor
                                    % endfor
                                    % if cycle_first is True:
                                        <tr>
                                            <td colspan="5">No active SRU cycle at this time (see <a href="https://kernel.ubuntu.com/">kernel.ubuntu.com</a> for any announcements).</td>
                                        </tr>
                                    % endif
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
