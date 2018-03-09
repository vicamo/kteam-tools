<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<% #>

# https://www.viget.com/articles/color-contrast/

__testing_status_colors = {
    'New'           : 'blue',
    'In Progress'   : 'grey', # 'white',
    'Confirmed'     : '#1496bb', # 'yellow',
    'Incomplete'    : 'red',
    'Invalid'       : 'grey',
    'Fix Released'  : 'green',
    'Fix Committed' : 'green',
    'Task missing'  : 'red',
    'unknown'       : 'magenta',
}

def __task_status(bug, task_name):
    try:
        for t in bug['tasks']:
            if t['target-name'] == '%s/%s' % ('kernel-sru-workflow', task_name):
                return t['status']
    except KeyError:
        return 'missing %s' % task_name
    return 'unknown'

def __assignee(bug, task_name):
    try:
        for t in bug['tasks']:
            if t['target-name'] == '%s/%s' % ('kernel-sru-workflow', task_name):
                return t['assignee']
    except KeyError:
        return 'unknown'
    return

def __coloured(msg, colour='black'):
    return '<span style="color: %s;font-weight: bold">%s</span>' % (colour, msg)

def __status_bite(bug):
    retval = ''

    while True:
        # Is it ready for promotion to -updates/-security?
        #
        security_status = __task_status(bug, 'promote-to-security')
        updates_status  = __task_status(bug, 'promote-to-updates')
        proposed_status = __task_status(bug, 'promote-to-proposed')
        if updates_status == 'Confirmed':
            if security_status == 'Confirmed':
                retval = __coloured('Ready for updates and security', 'green')
            elif security_status == 'Invalid':
                retval = __coloured('Ready for updates', 'green')
            else:
                retval = __coloured('Waiting for security review', '#bca136')
            break
        elif updates_status == 'Fix Committed':
            if security_status == 'Fix Committed':
                retval = __coloured('Releasing to updates and security', 'green')
            elif security_status == 'Invalid':
                retval = __coloured('Releasing to updates', 'green')
            else:
                retval = __coloured('Unknown release state', '#bca136')
            break
        elif updates_status == 'Fix Released':
            if security_status == 'Fix Committed':
                retval = __coloured('Releasing to updates and security', 'green')
            elif security_status == 'Invalid':
                retval = __coloured('Released to updates', 'green')
            elif security_status == 'Fix Released':
                retval = __coloured('Released to updates and security', 'green')
            break
        elif proposed_status == 'Confirmed':
            retval = __coloured('**  Waiting to be copied to -poposed **', 'red')
            break
        elif proposed_status == 'In Progress':
            retval = __coloured('Being copied to -proposed', '#bca136')
            break
        elif proposed_status == 'Fix Committed':
            retval = __coloured('Publishing to -proposed', '#bca136')
            break

        prep_status = __task_status(bug, 'prepare-package')
        if prep_status == 'New':
            retval = __coloured('Not ready to be cranked', 'blue')
            break
        elif prep_status == 'Confirmed':
            retval = __coloured('Ready to be cranked', '#bca136')
            break
        elif prep_status == 'In Progress':
            retval = __coloured('Being cranked by: %s' % (__assignee(bug, 'prepare-package')), 'green')
            break
        elif prep_status == 'Fix Committed':
            retval = __coloured('Uploaded by: %s' % (__assignee(bug, 'prepare-package')), 'magenta')
            break
        elif prep_status == 'Fix Released' and proposed_status == 'New':
            retval = __coloured('Building', 'magenta')
            break

        # Not ready for promotion, where are we with testing?
        #
        retval = '<table width="100%"><tr>'

        # automated-testing
        #
        automated_testing_status = __task_status(bug, 'automated-testing')
        color = __testing_status_colors[automated_testing_status]
        retval += '<td width="25%%" style="padding: 0 0">automated: %-26s</td>' % (__coloured(automated_testing_status, color))

        # certification-testing
        #
        certification_testing_status = __task_status(bug, 'certification-testing')
        color = __testing_status_colors[certification_testing_status]
        retval += '<td width="25%%" style="padding: 0 0">vertification: %-26s</td>' % (__coloured(certification_testing_status, color))

        # regression-testing
        #
        certification_testing_status = __task_status(bug, 'regression-testing')
        color = __testing_status_colors[certification_testing_status]
        retval += '<td width="25%%" style="padding: 0 0">regression: %-26s</td>' % (__coloured(certification_testing_status, color))

        # verification-testing
        #
        verification_testing_status = __task_status(bug, 'verification-testing')
        color = __testing_status_colors[verification_testing_status]
        retval += '<td width="25%%" style="padding: 0 0">verification: %-26s</td>' % (__coloured(verification_testing_status, color))

        retval += '</tr></table>'

        break

    return retval

cadence = {}
for bid in data['workflow']['bug-collections']['kernel-sru-workflow']['bugs']:
    b = data['workflow']['bug-collections']['kernel-sru-workflow']['bugs'][bid]

    title = b['title']
    package, other = title.split(':')
    other = other.strip()
    version, other = other.split(' ', 1)

    if 'kernel-stable-phase' not in b['properties']:
        phase = "Unknown (kernel-stable-phase properites missing)"
    else:
        phase = b['properties']['kernel-stable-phase']

    if b['series name'] not in cadence:
        cadence[b['series name']] = {}
    cadence[b['series name']][package] = {}
    cadence[b['series name']][package]['bug'] = bid
    cadence[b['series name']][package]['version'] = version
    cadence[b['series name']][package]['phase'] = __status_bite(b)

if 'kernel-development-workflow' in data['workflow']['bug-collections']:
    for bid in data['workflow']['bug-collections']['kernel-development-workflow']['bugs']:
        b = data['workflow']['bug-collections']['kernel-development-workflow']['bugs'][bid]

        title = b['title']
        package, other = title.split(':')
        other = other.strip()
        version, other = other.split(' ', 1)
        if ('properties' in b) and ('kernel-phase' in b['properties']):
            phase = b['properties']['kernel-phase']
        else:
            phase = 'damaged'

        if b['series name'] not in cadence:
            cadence[b['series name']] = {}
        cadence[b['series name']][package] = {}
        cadence[b['series name']][package]['bug'] = bid
        cadence[b['series name']][package]['version'] = version
        cadence[b['series name']][package]['phase'] = __status_bite(b)

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
                        <h1>Kernel Stable Team</h1>
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
                                        sru = data['sru']
                                        releases = sru['releases'].keys()
                                    %>
                                    % for rls in sorted(releases):
                                        <tr>
                                            <td colspan="5" style="background: #e9e7e5;">${rls}</td>
                                        </tr>
                                        % if rls in cadence:

                                            % for pkg in sorted(cadence[rls]):
                                            <%
                                                bug_count = 0
                                                missing  = 0
                                                verified = 0
                                                tracker  = 0
                                                needing_verification = 0
                                                if rls != dev_series:
                                                    try:
                                                        if 'bugs' in sru['releases'][rls][pkg]:
                                                            if rls in sru['releases']:
                                                                bug_count = len(sru['releases'][rls][pkg]['bugs'])

                                                                for bid in sru['releases'][rls][pkg]['bugs']:
                                                                    b = sru['releases'][rls][pkg]['bugs'][bid]
                                                                    if b['state'] == 'missing':
                                                                        missing += 1
                                                                    elif b['state'] == 'verified':
                                                                        verified += 1
                                                                    elif 'tracker' in b['state']:
                                                                        tracker += 1
                                                                needing_verification = bug_count - tracker
                                                    except KeyError:
                                                        pass

                                            %>
                                                <tr style="line-height: 100%">
                                                    <td>&nbsp;</td>

                                                    <%
                                                        # % if needing_verification == verified:
                                                        # <td width="120" align="right" style="color: green">
                                                        # % elif missing > 0:
                                                        # <td width="120" align="right" style="color: red">
                                                        # % else:
                                                        # <td width="120" align="right">
                                                        # % endif
                                                    %>
                                                    <td width="120" align="right" style="color: green">${cadence[rls][pkg]['version']}</td>

                                                    <%
                                                        # % if needing_verification == verified:
                                                        # <td style="color: green">
                                                        # % elif missing > 0:
                                                        # <td style="color: red">
                                                        # % else:
                                                        # <td>
                                                        # % endif
                                                    %>
                                                    <td style="color: green">${pkg}</td>

                                                    <td>${cadence[rls][pkg]['phase']}</td>
                                                </tr>
                                            % endfor
                                        % endif
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
