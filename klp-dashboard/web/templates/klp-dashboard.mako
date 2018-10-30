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
<%
    __phase_colours = {
        'Payload Testing'                       : 'blue',
        'Ready to promote tarball to Proposed'  : '#149gbb',
        'Promoting tarball to Proposed'         : 'green',
        'Ready to promote tarball to Release'   : '#149gbb',
        'Promoting tarball to Release'          : 'green',
        'Ready to promote tarball to Stable'    : '#149gbb',
        'Promoting tarball to Stable'           : 'green',
        'Ready to promote to Proposed'          : '#149gbb',
        'Promoting to Proposed'                 : 'green',
    }

    def __phase_coloured(msg, colour='black'):
        return '<span style="color: %s;font-weight: bold">%s</span>' % (__phase_colours[msg], msg)

    cadence = data['workflow']['canonical-lkp-workflow']
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
                        <h1>Canonical Kernel Livepatch Dashboard</h1>
                    </div> <!-- header -->

                    <div class="dash-section">
                        <table width="100%"> <!-- The section is one big table -->
                            <tr>
                                <td width="100%" valign="top">
                                    <table width="100%" style="font-size: 0.8em">
                                    <%
                                        releases = data['releases']
                                    %>
                                    % for rls in sorted(releases, reverse=True):
                                        <%
                                            codename = releases[rls].capitalize()
                                        %>
                                        <tr>
                                            <td colspan="5" style="background: #ffff99;">${rls} &nbsp;&nbsp; ${codename}</td>
                                        </tr>
                                        % if rls in cadence:
                                            % for kernel_package in cadence[rls]:
                                                <tr>
                                                    <td>&nbsp;</td> <td colspan="4" style="background: #e9e7e5;">${kernel_package}</td>
                                                </tr>

                                                <%
                                                    bugz = {}
                                                    for bug in cadence[rls][kernel_package]:
                                                        bugz[cadence[rls][kernel_package][bug]['package-name']] = bug

                                                %>
                                                % for k in sorted(bugz):
                                                    <% bug = bugz[k] %>
                                                    <tr style="line-height: 100%">
                                                        <td width="25">&nbsp;</td>
                                                        <%
                                                            url = "https://bugs.launchpad.net/canonical-lkp-workflow/+bug/%s" % cadence[rls][kernel_package][bug]['id']
                                                            phase = __phase_coloured(cadence[rls][kernel_package][bug]['phase'])
                                                        %>
                                                        <td width="180" align="right" style="color: green"><a href="${url}">${cadence[rls][kernel_package][bug]['package-name']}</a></td>
                                                        <td width="50">${cadence[rls][kernel_package][bug]['cycle']}</td>
                                                        <td width="50">${cadence[rls][kernel_package][bug]['kernel']}</td>
                                                        <td>${phase}</td>
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
