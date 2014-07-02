<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<%
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
                        <h1>${config['title']}</h1>
                    </div> <!-- header -->

                    <div class="dash-section">
                        <table width="100%" border="0"> <!-- The section is one big table -->
                            <tr>
                                <td>
                                    <table width="100%">
                                        <tr>
                                            <td width="44%" valign="top"> <!-- LEFT -->
                                                <table width="100%"> <tr><td><h3><a href="https://launchpad.net/builders">Builders Status</a></h3></td></tr> <tr><td><hr /></td></tr> </table>
                                                <table width="100%">
                                                    <tr>
                                                        <td>Registered</td>
                                                        <td>Available </td>
                                                        <td>Disabled  </td>
                                                        <td>Auto      </td>
                                                        <td>Manual    </td>
                                                    </tr>
                                                    <tr>
                                                        <td><span class="up"><strong>${data['builders']['totals']['registered']}</strong></span></td>
                                                        <td><span class="up"><strong>${data['builders']['totals']['available']} </strong></span></td>
                                                        <td><span class="down"><strong>${data['builders']['totals']['disabled']}</strong></span></td>
                                                        <td><span class="up"><strong>${data['builders']['totals']['auto']}      </strong></span></td>
                                                        <td><span class="down"><strong>${data['builders']['totals']['manual']}  </strong></span></td>
                                                    </tr>
                                                </table>
                                            </td>

                                            <td width="2%">&nbsp;</td>

                                            <td width="44%" valign="top"> <!-- RIGHT -->
                                                <table width="100%"> <tr><td><h3><a href="http://qa.ubuntuwire.org/ftbfs/">FTBFS          </a></h3></td></tr> <tr><td><hr /></td></tr> </table>
                                                <table id="dash-table" width="100%">
                                                    <tr><td class="legend" rowspan="2" style="text-align: center;">Failure</td> <td class="legend" colspan="2" style="text-align: center;">Main archive</td> <td class="legend"  colspan="3" style="text-align: center;">Ports archive</td> </td>
                                                    <tr>                                <td class="legend" style="text-align: center;">i386</td><td class="legend" style="text-align: center;">amd64</td><td class="legend" style="text-align: center;">armel</td><td class="legend" style="text-align: center;">armhf</td><td class="legend" style="text-align: center;">powerpc</td></tr>
                                                    <% ftbfs = data['ftbfs'] %>
                                                    % for state in sorted(ftbfs):
                                                        <tr>
                                                            <td class="legend">${state}</td>
                                                        % for arch in ('i386', 'amd64', 'armel', 'armhf', 'powerpc'):
                                                            % try:
                                                            <td>${ftbfs[state]['__stats__'][arch]}</td>
                                                            % except KeyError:
                                                            0</td>
                                                            % endtry
                                                        % endfor
                                                        </tr>
                                                    % endfor
                                                </table>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>

                            <tr style="line-height: 50%"><td>&nbsp;<hr />&nbsp;</td></tr>

                            <tr>
                                <td>
                                    <table width="100%" border="0">
                                        <tr>
                                            <td width="40%" valign="top"> <!-- LEFT -->
                                                <h3><a href="https://launchpad.net/builders">Builders</a></h3>
                                                <table id="dash-table" width="100%">
                                                    <tr><td class="legend">&nbsp;</td> <td class="legend" colspan="2" style="text-align: center;">Non-Virtual</td><td class="legend" colspan="2" style="text-align: center;">Virtual</td></tr>
                                                    <tr><td class="legend">&nbsp;</td> <td class="legend">count</td> <td class="legend">queue</td> <td class="legend">count</td> <td class="legend">queue</td> </tr>

                                                    % for proc in sorted(data['builders']['nonvirt']):
                                                        <tr>
                                                        % if data['builders']['nonvirt'][proc]['disabled'] > 0:
                                                        <td class="legend">${proc}</td> <td><span class="available">${data['builders']['nonvirt'][proc]['available']}</span> <span class="disabled">(${data['builders']['nonvirt'][proc]['disabled']})</span></td> <td>${data['builders']['nonvirt'][proc]['queue']}</td>
                                                            % if proc in data['builders']['nonvirt']:
                                                                % if data['builders']['nonvirt'][proc]['disabled'] > 0:
                                                                <td><span class="available">${data['builders']['nonvirt'][proc]['available']}</span> <span class="disabled">(${data['builders']['nonvirt'][proc]['disabled']})</span></td> <td>${data['builders']['nonvirt'][proc]['queue']}</td>
                                                                % else:
                                                                <td><span class="available">${data['builders']['nonvirt'][proc]['available']}</span></td> <td>${data['builders']['nonvirt'][proc]['queue']}</td>
                                                                % endif
                                                            % else:
                                                                <td><span class="legend">&nbsp;</td> <td class=legend>&nbsp;</td>
                                                            % endif
                                                        % else:
                                                        <td class="legend">${proc}</td> <td><span class="available">${data['builders']['nonvirt'][proc]['available']}</span></td> <td>${data['builders']['nonvirt'][proc]['queue']}</td>
                                                        <td class="legend">&nbsp;</td> <td class=legend>&nbsp;</td>
                                                        % endif
                                                        </tr>
                                                    % endfor

                                                </table>
                                            </td>

                                            <td width="20%" valign="top">
                                                <!-- <table width="100%"> <tr><td><h3><a href="http://people.canonical.com/~ubuntu-archive/pending-sru.html">SRUS</a></h3></td></tr> <tr><td><hr /></td></tr> </table> -->
                                                <table width="100%" border="0">
                                                    <tr>
                                                        <td width="13%">&nbsp;</td>
                                                        <td valign="top" width="100%">
                                                            <h3><a href="http://people.canonical.com/~ubuntu-archive/pending-sru.html">SRUS</a></h3>
                                                            <table id="dash-table">
                                                                <tbody>
                                                                    <tr><td class="legend">&nbsp;</td> <td class="legend">pending</td> </tr>
                                                                % for rls in sorted(data['srus']):
                                                                    <% ct = len(data['srus'][rls]) %>
                                                                    <tr> <td class="legend">${rls}</td> <td>${ct}</td> </tr>
                                                                % endfor
                                                                </tbody>
                                                            </table>
                                                        </td>
                                                    </tr>
                                                </table>
                                            </td>

                                            <td width="40%" valign="top">
                                                <h3>Upload Queues</a></h3>
                                                <table id="dash-table" width="100%">
                                                    <tr><td class="legend">&nbsp;</td><td class="legend" colspan="2" style="text-align: center;">Proposed</td><td class="legend" colspan="2" style="text-align: center;">Backports</td></tr>
                                                    <tr><td class="legend">&nbsp;</td><td class="legend">Unapp.</td> <td class="legend">New</td> <td class="legend">Unapp.</td> <td class="legend">New</td> </tr>
                                                    % for rls in sorted(data['upload-queues']['Proposed'], reverse=True):
                                                        <tr>
                                                            <td class="legend">${rls}</td>
                                                            <td><a href="https://launchpad.net/ubuntu/${rls}/+queue?queue_state=1">${data['upload-queues']['Proposed'][rls]['unapproved']}</a></td> <td><a href="https://launchpad.net/ubuntu/${rls}/+queue?queue_state=0">${data['upload-queues']['Proposed'][rls]['new']}</a></td>
                                                            <td><a href="https://launchpad.net/ubuntu/${rls}/+queue?queue_state=1">${data['upload-queues']['Backports'][rls]['unapproved']}</a></td> <td><a href="https://launchpad.net/ubuntu/${rls}/+queue?queue_state=0">${data['upload-queues']['Backports'][rls]['new']}</a></td>
                                                        </tr>
                                                    % endfor
                                                </table>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                        </table>
                    </div> <!-- dash-section -->

                    <!--
                        1. Output from testing scripts (outdate, probs, mismatches)     [ToDo]
                        2. Pending SRUs                                                 [DONE]
                        3. Logs for jenkins install/upgrade CI runs.                    [DONE]
                        4. FTBS tracker                                                 [DONE]
                        5. Livefs/cd build logs                                         [DONE]
                    <h2>Quick Links</h2>
                    -->
                    <div class="dash-section">
                    <table width="100%">
                        <tr>
                            <td width="25%" valign="top"><a href="http://people.canonical.com/~ubuntu-archive/pending-sru.html">SRUs Pending</a>
                            </td> <td>&nbsp;</td>
                            <td valign="top">
                                This report shows all the SRU packages currently waiting verification before being moved to -updates.
                            </td>
                        </tr>
                        <tr>
                            <td valign="top"><a href="http://qa.ubuntuwire.org/ftbfs/">FTBFS (Fail To Build From Source)</a></td>
                            </td> <td>&nbsp;</td>
                            <td valign="top">
                                A report of all the packages that are failing to build from their source.
                            </td>
                        </tr>
                        <tr>
                            <td valign="top"><a href="http://jenkins.qa.ubuntu.com/">Jenkins CI</a></td>
                            </td> <td>&nbsp;</td>
                            <td valign="top">
                                Jenkins Continuous Integration jobs and their output.
                            </td>
                        </tr>
                        <tr>
                            <td valign="top"><a href="http://people.canonical.com/~ubuntu-archive/livefs-build-logs/quantal/">Quantal LiveFS Build Logs</a></td>
                            </td> <td>&nbsp;</td>
                            <td valign="top">
                                A link to the directory tree where the build logs for the Quantal livefs builds can be found. You will have to drill down a bit to find them.
                            </td>
                        </tr>
                        <tr>
                            <td valign="top"><a href="http://people.canonical.com/~ubuntu-archive/cd-build-logs/">CD Build Logs</a></td>
                            </td> <td>&nbsp;</td>
                            <td valign="top">
                                A link to the directory tree where the build logs for the the various CD builds can be found. You will have to drill down a bit to find them.
                            </td>
                        </tr>
                        <tr>
                            <td valign="top"><a href="http://people.canonical.com/~ubuntu-archive/nbs.html">NBS (Not Built from Source)</a></td>
                            </td> <td>&nbsp;</td>
                            <td valign="top">
                                Things in the pool for which we no longer have the source packages for.
                            </td>
                        </tr>
                        <tr>
                            <td valign="top"><a href="http://people.canonical.com/~ubuntu-archive/component-mismatches.svg">Component Mismatches</a></td>
                            </td> <td>&nbsp;</td>
                            <td valign="top">
                                Packages in an archive (main) that depend on a package that is not in the same archive (main). An MIR (Main Inclusion Request) is required to fix this.
                            </td>
                        </tr>
                    </table>
                    </div> <!-- section -->

                </div>
            </div>
        -</div>
    </body>

</html>
<!-- vi:set ts=4 sw=4 expandtab: -->
