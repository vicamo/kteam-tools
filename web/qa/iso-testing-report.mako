<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" dir="ltr" lang="en-US">
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
	<title>${report_title}</title>

        <link title="light" rel="stylesheet" href="http://people.canonical.com/~kernel/reports/css/themes/blue/style.css" type="text/css" media="print, projection, screen" />
        <link title="light" rel="stylesheet" href="http://people.canonical.com/~kernel/reports/css/light.css" type="text/css" media="print, projection, screen" />

        <link title="dark" rel="stylesheet" href="http://people.canonical.com/~kernel/reports/css/themes/bjf/style.css" type="text/css" media="print, projection, screen" />
        <link title="dark" rel="stylesheet" href="http://people.canonical.com/~kernel/reports/css/dark.css" type="text/css" media="print, projection, screen" />

        <script type="text/javascript" src="http://people.canonical.com/~kernel/reports/js/styleswitcher.js"></script>

        <link href='http://fonts.googleapis.com/css?family=Cantarell&subset=latin'              rel='stylesheet' type='text/css'>
        <script type="text/javascript" src="http://people.canonical.com/~kernel/reports/js/jquery-latest.js"></script>
        <script type="text/javascript" src="http://people.canonical.com/~kernel/reports/js/jquery.tablesorter.js"></script>
        <script type="text/javascript">
           // add parser through the tablesorter addParser method
           $.tablesorter.addParser({
               // set a unique id
               id: 'age',
               is: function(s) {
                   // return false so this parser is not auto detected
                   return false;
               },
               format: function(s) {
                   // format your data for normalization
                   fields  = s.split('.')
                   days    = parseInt(fields[0], 10) * (60 * 24);
                   hours   = parseInt(fields[1], 10) * 60;
                   minutes = parseInt(fields[2]);
                   total   = minutes + hours + days
                   return total;
               },
               // set type, either numeric or text
               type: 'numeric'
           });

           // add parser through the tablesorter addParser method
           $.tablesorter.addParser({
               // set a unique id
               id: 'importance',
               is: function(s) {
                   // return false so this parser is not auto detected
                   return false;
               },
               format: function(s) {
                   // format your data for normalization
                       return s.toLowerCase().replace(/critical/,6).replace(/high/,5).replace(/medium/,4).replace(/low/,3).replace(/wishlist/,2).replace(/undecided/,1).replace(/unknown/,0);
               },
               // set type, either numeric or text
               type: 'numeric'
           });

           // add parser through the tablesorter addParser method
           $.tablesorter.addParser({
               // set a unique id
               id: 'status',
               is: function(s) {
                   // return false so this parser is not auto detected
                   return false;
               },
               format: function(s) {
                   // format your data for normalization
                       return s.toLowerCase().replace(/new/,12).replace(/incomplete/,11).replace(/confirmed/,10).replace(/triaged/,9).replace(/in progress/,8).replace(/fix committed/,7).replace(/fix released/,6).replace(/invalid/,5).replace(/won't fix/,4).replace(/confirmed/,3).replace(/opinion/,2).replace(/expired/,1).replace(/unknown/,0);
               },
               // set type, either numeric or text
               type: 'numeric'
           });
           $(function() {
                $("#linux").tablesorter({
                    headers: {
                        3: {
                            sorter:'importance'
                        },
                        4: {
                            sorter:'status'
                        }
                    },
                    widgets: ['zebra']
                });
            });
        </script>

    </head>


    <body class="bugbody">
        <div class="outermost">
            <div class="title">
		    ${report_title}
            </div>
            <div class="section">
                <table id="linux" class="tablesorter" border="0" cellpadding="0" cellspacing="1" width="100%%">
                    <thead>
                        <tr>
                            <th width="40">Bug</th>
                            <th>Summary</th>
                            <th width="100">Task</th>
                            <th width="80">Importance</th>
                            <th width="80">Status</th>
                            <th width="140">Assignee</th>
                            <th width="120">Milestone</th>
                            <th width="80">Nominations</th>
                        </tr>
                    </thead>
		    <tbody>
                <%
                    importance_color = {
                            "Unknown"       : "importance-unknown",
                            "Critical"      : "importance-critical",
                            "High"          : "importance-high",
                            "Medium"        : "importance-medium",
                            "Low"           : "importance-low",
                            "Wishlist"      : "importance-wishlist",
                            "Undecided"     : "importance-undecided"
                        }
                    status_color     = {
                            "New"           : "status-new",
                            "Incomplete"    : "status-incomplete",
                            "Confirmed"     : "status-confirmed",
                            "Triaged"       : "status-triaged",
                            "In Progress"   : "status-in_progress",
                            "Fix Committed" : "status-fix_committed",
                            "Fix Released"  : "status-fix_released",
                            "Invalid"       : "status-invalid",
                            "Won't Fix"     : "status-wont_fix",
                            "Opinion"       : "status-opinion",
                            "Expired"       : "status-expired",
                            "Unknown"       : "status-unknown"
                        }

                    tasks = template_data['tasks']
                %>
                % for bid in tasks:
                    % for t in tasks[bid]:
                        <%
                            importance       = t['importance']
                            importance_class = importance_color[importance]

                            status           = t['status']
                            status_class     = status_color[status]

                            assignee         = t['assignee'] if 'assignee'    in t else 'unknown'

                            nominations = ''
                            noms = t['bug']['nominations']
                            noms.sort()
                            noms.reverse()
                            for n in noms:
                                if nominations != '':
                                    nominations += ', '
                                nominations += n.title()[0]

                            task_name = t['bug_target_name'].replace('(Ubuntu Oneiric)', '').strip()
                        %>
                        <tr>
                            <td><a href="http://launchpad.net/bugs/${bid}">${bid}</a></td>
                            <td>${t['bug']['title']}</td>
                            <td>${task_name}
                            <td class="${importance_class}">${importance}</td>
                            <td class="${status_class}">${status}</td>
                            <td>${assignee}</td>
                            <td>${t['milestone']}</td>
                            <td align="center">${nominations}</td>
                        </tr>
                    % endfor
                % endfor
		    </tbody>
                </table>
            </div>
            <br />
            <br />
            <div>
                <br />
                <hr />
                <table width="100%%" cellspacing="0" cellpadding="0">
                    <tr>
                        <td>
                            ${timestamp}
                        </td>
                        <td align="right">
                            Themes:&nbsp;&nbsp;
                            <a href='#' onclick="setActiveStyleSheet('dark'); return false;">DARK</a>
                            &nbsp;
                            <a href='#' onclick="setActiveStyleSheet('light'); return false;">LIGHT</a>
                        </td>
                    </tr>
                </table>
                <br />
            </div>


        </div> <!-- Outermost -->
    </body>


</html>
<!-- vi:set ts=4 sw=4 expandtab: -->
