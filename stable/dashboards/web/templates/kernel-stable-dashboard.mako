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
    'Confirmed'     : '#1496bb', # 'yellow',
    'Incomplete'    : 'red',
    'Invalid'       : 'grey',
    'Fix Released'  : '#1496bb',
    'Fix Committed' : '#1496bb',
    'Task missing'  : 'red',
    'unknown'       : 'magenta',
    'n/a'           : 'grey',
}
%>
<%

def __task_status(bug, task_name):
    try:
        for t in bug['tasks']:
            if t['target-name'] == '%s/%s' % ('kernel-sru-workflow', task_name):
                return t['status']
            if 'kernel-development-workflow' in t['target-name']:
                if t['target-name'] == '%s/%s' % ('kernel-development-workflow', task_name):
                    return t['status']
    except KeyError:
        return 'missing %s' % task_name
    return 'n/a'

%>
<%

def __assignee(bug, task_name):
    try:
        for t in bug['tasks']:
            if t['target-name'] == '%s/%s' % ('kernel-sru-workflow', task_name):
                return t['assignee']
    except KeyError:
        return 'unknown'
    return

%>
<%

def __coloured(msg, colour='black'):
    return '<span style="color: %s;font-weight: bold">%s</span>' % (colour, msg)

%>
<%

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
                retval = __coloured('Ready for updates and security', '#1496bb')
            elif security_status == 'Invalid':
                retval = __coloured('Ready for updates', '#1496bb')
            else:
                retval = __coloured('Waiting for security review', '#bca136')
            break
        elif updates_status == 'Fix Committed':
            if security_status == 'Fix Committed':
                retval = __coloured('Releasing to updates and security', '#1496bb')
            elif security_status == 'Invalid':
                retval = __coloured('Releasing to updates', '#1496bb')
            else:
                retval = __coloured('Unknown release state', '#bca136')
            break
        elif updates_status == 'Fix Released':
            if security_status == 'Fix Committed':
                retval = __coloured('Releasing to updates and security', '#1496bb')
            elif security_status == 'Invalid':
                retval = __coloured('Released to updates', '#1496bb')
            elif security_status == 'Fix Released':
                retval = __coloured('Released to updates and security', '#1496bb')
            break
        elif proposed_status == 'Confirmed':
            retval = __coloured('Waiting to be copied to -proposed', 'red')
            break
        elif proposed_status == 'In Progress':
            retval = __coloured('Being copied to -proposed', '#bca136')
            break
        elif proposed_status == 'Fix Committed':
            retval = __coloured('Publishing to -proposed', '#3455db')
            break

        prep_status = __task_status(bug, 'prepare-package')

        if prep_status == 'Invalid':
            # For -meta only packages, consider prepare-package-meta status
            prep_status = __task_status(bug, 'prepare-package-meta')

        if prep_status == 'New':
            retval = __coloured('Not ready to be cranked', 'grey')
            break
        elif prep_status == 'Confirmed':
            retval = __coloured('Ready to be cranked', '#bca136')
            break
        elif prep_status == 'In Progress':
            retval = __coloured('Cranker: %s' % (__assignee(bug, 'prepare-package')), '#1496bb')
            break
        elif prep_status == 'Fix Committed':
            retval = __coloured('Uploaded by: %s' % (__assignee(bug, 'prepare-package')), 'magenta')
            break
        elif prep_status == 'Fix Released' and proposed_status == 'New':
            retval = __coloured('Building', '#3455db')
            break

        # Not ready for promotion, where are we with testing?
        #
        retval = '<table width="100%" border="0"><tr>'
        retval += '<td style="padding: 0 0">%s</td>' % __coloured('Testing', '#1496bb')

        # automated-testing
        #
        automated_testing_status = __task_status(bug, 'automated-testing')
        if automated_testing_status == 'n/a':
            retval += '<td width="18%%" style="padding: 0 0"> </td>'
        else:
            color = __testing_status_colors[automated_testing_status]
            retval += '<td width="18%%" style="padding: 0 0">automated: %-26s</td>' % (__coloured(automated_testing_status, color))

        # certification-testing
        #
        certification_testing_status = __task_status(bug, 'certification-testing')
        if certification_testing_status == 'n/a':
            retval += '<td width="18%%" style="padding: 0 0"> </td>'
        else:
            color = __testing_status_colors[certification_testing_status]
            retval += '<td width="18%%" style="padding: 0 0">certification: %-26s</td>' % (__coloured(certification_testing_status, color))

        # regression-testing
        #
        regression_testing_status = __task_status(bug, 'regression-testing')
        if regression_testing_status == 'n/a':
            retval += '<td width="18%%" style="padding: 0 0"> </td>'
        else:
            color = __testing_status_colors[regression_testing_status]
            retval += '<td width="18%%" style="padding: 0 0">regression: %-26s</td>' % (__coloured(regression_testing_status, color))

        # verification-testing
        #
        verification_testing_status = __task_status(bug, 'verification-testing')
        if verification_testing_status == 'n/a':
            retval += '<td width="18%%" style="padding: 0 0"> </td>'
        else:
            color = __testing_status_colors[verification_testing_status]
            retval += '<td width="18%%" style="padding: 0 0">verification: %-26s</td>' % (__coloured(verification_testing_status, color))

        retval += '</tr></table>'

        break

    return retval
%>
<%

cadence = {}
for bid in data['workflow']['bug-collections']['kernel-sru-workflow']['bugs']:
    b = data['workflow']['bug-collections']['kernel-sru-workflow']['bugs'][bid]

    try:
        title = b['title']
        package, other = title.split(':')
        other = other.strip()
        version, other = other.split(' ', 1)
    except:
        package = 'unknown'
        version = 'unknown'

    if 'kernel-stable-phase' not in b['properties']:
        phase = "Unknown (kernel-stable-phase properites missing)"
    else:
        phase = b['properties']['kernel-stable-phase']

    if b['series name'] == "":
        sn = 'unknown'
    else:
        sn = b['series name']
    if sn not in cadence:
        cadence[sn] = {}
    if package not in cadence[sn]:
        cadence[sn][package] = []
    status = __status_bite(b)

    # Fixup the link to the regression testing if this is 'testing' status.
    #
    if 'regression' in status:
        try:
            status = status.replace('regression', '<a href="%s">regression</a>' % data['testing']['regression'][package])
        except KeyError:
            pass

    # Fixup the link to the automated testing results
    #
    if 'automated' in status:
        status = status.replace('automated', '<a href="%s">automated</a>' % 'http://people.canonical.com/~kernel/status/adt-matrix/%s-%s.html' % (sn, package.replace('linux', 'linux-meta')))

    # Fixup the link to the sru-report with verification status
    #
    if 'verification' in status:
        status = status.replace('verification', '<a href="%s">verification</a>' % 'http://kernel.ubuntu.com/reports/sru-report.html')

    cadence[sn][package].append({ 'bug': bid, 'version': version, 'phase': status })
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
                                    %>
                                    % for rls in sorted(releases, reverse=True):
                                        <%
                                            codename = releases[rls].capitalize()
                                        %>
                                        % if releases[rls] in cadence:
                                        <tr>
                                            <td colspan="5" style="background: #e9e7e5;">${rls} &nbsp;&nbsp; ${codename}</td>
                                        </tr>
                                            % for pkg in sorted(cadence[releases[rls]]):
                                                % for bug in cadence[releases[rls]][pkg]:
                                                    <tr style="line-height: 100%">
                                                        <td>&nbsp;</td>
                                                        <%
                                                            url = "https://bugs.launchpad.net/ubuntu/+source/linux/+bug/%s" % bug['bug']
                                                        %>
                                                        <td width="120" align="right" style="color: green"><a href="${url}">${bug['version']}</a></td>
                                                        <td style="color: green"><a href="${url}">${pkg}</a></td>
                                                        <td>${bug['phase']}</td>
                                                    </tr>
                                                % endfor
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
