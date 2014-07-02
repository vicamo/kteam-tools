<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<% #>
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
    cadence[b['series name']][package]['phase'] = phase

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
        cadence[b['series name']][package]['phase'] = phase

%>
<html xmlns="http://www.w3.org/1999/xhtml" dir="ltr" lang="en-US">
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
        <!-- <meta http-equiv="refresh" content="60" /> -->
        <title>${config['title']}</title>
        <link rel="stylesheet" href="media/dashboard.css" type="text/css" media="screen" />
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

                                                    % if needing_verification == verified:
                                                    <td width="120" align="right" style="color: green">
                                                    % elif missing > 0:
                                                    <td width="120" align="right" style="color: red">
                                                    % else:
                                                    <td width="120" align="right">
                                                    % endif
                                                    ${cadence[rls][pkg]['version']}</td>

                                                    % if needing_verification == verified:
                                                    <td style="color: green">
                                                    % elif missing > 0:
                                                    <td style="color: red">
                                                    % else:
                                                    <td>
                                                    % endif
                                                    ${pkg}</td>

                                                    <td>
                                                        % if rls != dev_series:
                                                        <table width="100%">
                                                            <tr>
                                                            % if needing_verification == verified:
                                                            <td align="right" width="25%"><a title="Total bugs" href="" style="color: green">${bug_count}</a></td><td align="right" width="25%" ><a title="Needing verification" href="">${needing_verification}</a></td><td align="right" width="25%"><a title="Missing verification tags" href="">${missing}</a></td><td align="right" width="25%"><a title="Have been verified" href="" style="color: green">${verified}</a></td>
                                                            % elif missing > 0:
                                                            <td align="right" width="25%" ><a title="Total bugs" href="">${bug_count}</a></td><td align="right" width="25%"><a title="Needing verification" href="">${needing_verification}</a></td><td align="right" width="25%"><a title="Missing verifictation tags" href="" style="color: red;font-weight: bold">${missing}</a></td><td align="right" width="25%"><a title="Have been verified" href="">${verified}</a></td>
                                                            % else:
                                                            <td align="right" width="25%" ><a title="Total bugs" href="">${bug_count}</a></td><td align="right" width="25%"><a title="Needing verification" href="">${needing_verification}</a></td><td align="right" width="25%"><a title="Missing verification tags" href="">${missing}</a></td><td align="right" width="25%"><a title="Have been verified" href="">${verified}</a></td>
                                                            % endif
                                                            </tr>
                                                        </table>
                                                        % endif
                                                    </td>
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
