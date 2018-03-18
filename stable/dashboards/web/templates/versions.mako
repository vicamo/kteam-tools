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
%>
<html xmlns="http://www.w3.org/1999/xhtml" dir="ltr" lang="en-US">
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
        <!-- <meta http-equiv="refresh" content="60" /> -->
        <title>Kernel Package Versions</title>
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
                        <h1>Kernel Package Versions</h1>
                    </div> <!-- header -->

                    <% releases = data['releases'] %>
                    <div class="dash-section">
                        <table width="100%"> <!-- The section is one big table -->
                            <tr>
                                <td width="100%" valign="top"> <!-- LEFT -->
                                    <table width="100%" style="font-size: 0.8em"> <!-- SRU Data -->
                                    % for ver in sorted(releases, reverse=True):
                                        <% 
                                            rls = releases[ver]
                                            codename = releases[ver].capitalize()
                                        %>
                                        <tr>
                                            <td colspan="5" style="background: #e9e7e5">${ver} &nbsp;&nbsp; ${codename}</td>
                                        </tr>
                                        <tr><th>Package</th><th align="left">PPA</th><th align="left">Release</th><th align="left">Updates</th><th align="left">Proposed</th><th align="left">&nbsp;</th></tr>
                                        <% odd = False %>
                                        % for pkg in sorted(data['bugs']['releases'][rls]):
                                            % if odd:
                                                <tr style="background: #f8f8f8">
                                                <% odd = False %>
                                            % else:
                                                <tr>
                                                <% odd = True %>
                                            % endif
                                                % if pkg.startswith('linux'):
                                                    <td style="padding: 0 0"><a href="https://launchpad.net/ubuntu/artful/+source/${pkg}">${pkg}</a></td>
                                                    % if 'ppa' in data['bugs']['releases'][rls][pkg]:
                                                        <td style="padding: 0 0"><a href="https://launchpad.net/~canonical-kernel-team/+archive/ubuntu/ppa/+packages">${data['bugs']['releases'][rls][pkg]['ppa']}</a></td>
                                                    % else:
                                                        <td style="padding: 0 0"></td>
                                                    % endif

                                                    % if 'Release' in data['bugs']['releases'][rls][pkg]:
                                                        <td style="padding: 0 0"><a href="https://launchpad.net/ubuntu/+source/${pkg}/${data['bugs']['releases'][rls][pkg]['Release']}">${data['bugs']['releases'][rls][pkg]['Release']}</a></td>
                                                    % else:
                                                        <td style="padding: 0 0"></td>
                                                    % endif

                                                    % if 'Updates' in data['bugs']['releases'][rls][pkg]:
                                                        <td style="padding: 0 0"><a href="https://launchpad.net/ubuntu/+source/${pkg}/${data['bugs']['releases'][rls][pkg]['Updates']}">${data['bugs']['releases'][rls][pkg]['Updates']}</a></td>
                                                    % else:
                                                        <td style="padding: 0 0"></td>
                                                    % endif

                                                    % if 'Proposed' in data['bugs']['releases'][rls][pkg]:
                                                        <td style="padding: 0 0"><a href="https://launchpad.net/ubuntu/+source/${pkg}/${data['bugs']['releases'][rls][pkg]['Proposed']}">${data['bugs']['releases'][rls][pkg]['Proposed']}</a></td>
                                                    % else:
                                                        <td style="padding: 0 0"></td>
                                                    % endif
                                                % endif
                                            </tr>
                                        % endfor
                                        <tr><td>&nbsp;</td></tr>
                                    % endfor
                                    </table>
                                </td>
                            </tr>
                        </table>
                    </div> <!-- dash-section -->
                </div>
            </div>
        -</div>
    </body>

</html>
<!-- vi:set ts=4 sw=4 expandtab: -->
