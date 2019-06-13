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
# status_bites
#
def __status_bites(bug):
    bites = []

    # debs -- look at the bug with respect to any Debian Packages we are tracking.
    retval = ''
    while True:
        # Is it ready for promotion to -proposed.
        proposed_status = __task_status(bug, 'promote-to-proposed')
        if proposed_status == 'Confirmed':
            retval = __coloured('Waiting to be copied to -proposed', 'red')
            break
        elif proposed_status in ('In Progress', 'Fix Committed'):
            retval = __coloured('Publishing to -proposed', '#3455db')
            break

        # Is it ready for promotion to -updates/-security?
        security_status = __task_status(bug, 'promote-to-security')
        updates_status  = __task_status(bug, 'promote-to-updates')
        retval_release = []
        if updates_status == 'Confirmed':
            retval_release.append('Ready for updates')
        elif updates_status in ('In Progress', 'Fix Committed'):
            retval_release.append('Releasing to updates')
        elif updates_status == 'Fix Released':
            retval_release.append('Released to updates')

        if (len(retval_release) > 0 and updates_status == 'Fix Released' and
                security_status == 'New'):
            retval_release.append('Holding before security')
        elif security_status == 'Confirmed':
            retval_release.append('Ready for security')
        elif security_status in ('In Progress', 'Fix Committed'):
            retval_release.append('Releasing to security')
        elif security_status == 'Fix Released':
            retval_release.append('released to security')

        if len(retval_release) > 0:
            retval = __coloured('. '.join(retval_release), '#1496bb')
            break

        # Is it being prepared for upload/built?
        #
        prep_status = __task_status(bug, 'prepare-package')
        if prep_status == 'Invalid':
            prep_status = __task_status(bug, 'prepare-package-meta')
        if prep_status == 'New':
            retval = __coloured('Not ready to be cranked', 'grey')
            break
        elif prep_status == 'Confirmed':
            retval = __coloured('Ready to be cranked', '#bca136')
            break
        elif prep_status == 'In Progress':
            retval = __coloured('Being cranked by: %s' % (__assignee(bug, 'prepare-package')), '#1496bb')
            break
        elif prep_status == 'Fix Committed':
            retval = __coloured('Uploaded by: %s' % (__assignee(bug, 'prepare-package')), '#1496bb')
            break
        elif prep_status == 'Fix Released' and proposed_status == 'New':
            retval = __coloured('Building', '#1496bb')
            break

        # Is it in testing?
        #
        automated_testing_status = __task_status(bug, 'automated-testing')
        certification_testing_status = __task_status(bug, 'certification-testing')
        regression_testing_status = __task_status(bug, 'regression-testing')
        verification_testing_status = __task_status(bug, 'verification-testing')
        testing_valid = (
                automated_testing_status != 'n/a' or
                certification_testing_status != 'n/a' or
                regression_testing_status != 'n/a' or
                verification_testing_status != 'n/a')
        testing_complete = (
                automated_testing_status in ('Invalid', 'Fix Released') and
                certification_testing_status in ('Invalid', 'Fix Released') and
                regression_testing_status in ('Invalid', 'Fix Released') and
                verification_testing_status in ('Invalid', 'Fix Released'))
        if testing_valid and not testing_complete:
            color = __testing_status_colors[automated_testing_status]
            retval += '<span style="display: inline-block; min-width: 100px; width=100px;">at: %-26s</span>' % (__coloured(automated_testing_status, color))

            color = __testing_status_colors[certification_testing_status]
            retval += '<span style="display: inline-block; min-width: 100px; width=100px;">ct: %-26s</span>' % (__coloured(certification_testing_status, color))

            color = __testing_status_colors[regression_testing_status]
            retval += '<span style="display: inline-block; min-width: 100px; width=100px;">rt: %-26s</span>' % (__coloured(regression_testing_status, color))

            color = __testing_status_colors[verification_testing_status]
            retval += '<span style="display: inline-block; min-width: 100px; width=100px;">vt: %-26s</span>' % (__coloured(verification_testing_status, color))

            break

        retval_tested = []

        stakeholder_signoff = __task_status(bug, 'stakeholder-signoff')
        security_signoff    = __task_status(bug, 'security-signoff')
        if stakeholder_signoff in ('Confirmed', 'In Progress', 'Fix Committed'):
            retval_tested.append(__coloured('Waiting for stakeholder signoff', 'red'))

        if security_signoff in ('Confirmed', 'In Progress', 'Fix Committed'):
            retval_tested.append(__coloured('Waiting for security signoff', 'red'))

        # If we are post testing but not releasable report this as something we cannot
        # see is causing us to hold.
        if testing_complete and len(retval_tested) == 0:
            retval_tested.append(__coloured('Not Releaseable', 'red'))

        # Insert the testing status now we have accumulated the underlying reasons.
        if testing_complete:
            retval_tested.insert(0, __coloured('Testing complete', '#1496bb'))

        if len(retval_tested) > 0:
            retval = '. '.join(retval_tested)
            break

        # No debs status.
        break

    # Report Debs release progress.
    debs_in = []
    security_status = __task_status(bug, 'promote-to-security')
    updates_status  = __task_status(bug, 'promote-to-updates')
    proposed_status = __task_status(bug, 'promote-to-proposed')
    if proposed_status not in ('n/a', 'New', 'Invalid', 'Opinion'):
        debs_in.append('ppa')
    if proposed_status in ('Fix Released'):
        debs_in.append('proposed')
    if updates_status in ('Fix Released'):
        debs_in.append('updates')
    if security_status in ('Fix Released'):
        debs_in.append('security')
    if len(debs_in) != 0:
        retval = '<span style="display: inline-block; min-width: 400px; width=400px;">' + retval + '</span>'
        if retval[-2:] not in ('', '  '):
            retval += '  '
        retval += 'in: ' + ','.join(debs_in)

    if retval != '':
        bites.append('<span style="display: inline-block; min-width: 20px; width=20px;">d:</span>' + retval)

    # snaps -- look at the bug with respect to any snap tracked.
    retval = ''
    while True:
        # Are there any snap publish tasks outstanding?
        edge_status = __task_status(bug, 'snap-release-to-edge')
        if edge_status == 'New':
            retval = __coloured('Snap not ready to be cranked', 'grey')
            break
        elif edge_status == 'Confirmed':
            retval = __coloured('Snap ready to be cranked', '#bca136')
            break
        beta_status = __task_status(bug, 'snap-release-to-beta')
        if beta_status == 'Confirmed':
            retval = __coloured('Snap ready to release to beta', '#bca136')
            break
        candidate_status = __task_status(bug, 'snap-release-to-candidate')
        if candidate_status == 'Confirmed':
            retval = __coloured('Snap ready to release to candidate', '#bca136')
            break
        stable_status = __task_status(bug, 'snap-release-to-stable')
        if stable_status == 'Confirmed':
            retval = __coloured('Snap ready to release to stable', '#bca136')
            break

        certification_testing_status = __task_status(bug, 'snap-certification-testing')
        qa_testing_status = __task_status(bug, 'snap-qa-testing')
        if (certification_testing_status != 'n/a' or
                qa_testing_status != 'n/a'):
            color = __testing_status_colors[certification_testing_status]
            retval += '<span style="display: inline-block; min-width: 100px; width=100px;">ct: %-26s</span>' % (__coloured(certification_testing_status, color))

            color = __testing_status_colors[qa_testing_status]
            retval += '<span style="display: inline-block; min-width: 100px; width=100px;">qa: %-26s</span>' % (__coloured(qa_testing_status, color))
            break

        if (edge_status in ('Fix Released', 'Invalid') and
                beta_status in ('Fix Released', 'Invalid') and
                candidate_status in ('Fix Released', 'Invalid') and
                stable_status in ('Fix Released', 'Invalid')):
            retval = __coloured('Snap promotions complete', 'green')

        # No snap status.
        break

    # Report Snap release progress.
    risk_in = []
    for risk in ['edge', 'beta', 'candidate', 'stable']:
        status = __task_status(bug, 'snap-release-to-' + risk)
        if status == 'Fix Released':
            risk_in.append(risk)
    if len(risk_in) != 0:
        retval = '<span style="display: inline-block; min-width: 400px; width=400px;">' + retval + '</span>'
        if retval[-2:] not in ('', '  '):
            retval += '  '
        retval += 'in: ' + ','.join(risk_in)

    if retval != '':
        bites.append('<span style="display: inline-block; min-width: 20px; width=20px;">s:</span>' + retval)

    return bites

%>
<%
import re

cycles = {}
cadence = {}
for bid in data['swm']:
    b = data['swm'][bid]

    try:
        cycle = 'unknown'
        if 'cycle' in b:
            cycle = (b['cycle'].split('-') + [''])[0]

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

        cadence[cycle][sn][package].append({ 'bug': bid, 'version': version, 'phase': status })
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
