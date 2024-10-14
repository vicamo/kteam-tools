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
    'Fix Committed' : 'green', # '#1496bb',
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
    'Triaged'       : 'Ready/Bins',
    'Incomplete'    : 'Rejected',
    'Fix Committed' : 'Approved/aNR',
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

def add_in(thing_in, where, state, href=None):
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
        if href:
            where = '<a href="{}" class="archive">{}</a>'.format(href, where)
        thing_in.append(where)


def route_href(ks_package, route, stream="1"):
    if stream == "-":
        stream = "1"
    stream = int(stream)

    if ks_package.routing is None:
        return None
    ks_route = ks_package.routing.lookup_route(route)
    if ks_route is None:
        return None
    if len(ks_route) < stream:
        return None
    reference = ks_route[stream - 1].reference

    url = None
    if reference == "ubuntu":
        url = f"https://launchpad.net/ubuntu/+source/{ks_package.name}/{version}/+publishinghistory"

    elif reference.startswith("ppa:"):
        package_filter = ks_package.name.replace("linux-", "", 1)
        url = reference.replace("/", "/+archive/", 1)
        url = url.replace("ppa:", "https://launchpad.net/~", 1)
        url += f"/+packages?field.name_filter={package_filter}&field.series_filter={ks_package.series.codename}"

    return url

# status_bites
#
def __status_bites(bug, attrs, ks_package=None):
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
            add_in(thing_in, 'ppa', prep_status, href=route_href(ks_package, 'build', stream=stream))
            add_in(thing_in, 'proposed', proposed_status, href=route_href(ks_package, 'proposed', stream=stream))
            add_in(thing_in, 'updates', updates_status, href=route_href(ks_package, 'updates'))
            add_in(thing_in, 'security', security_status, href=route_href(ks_package, 'security'))
            add_in(thing_in, 'release', release_status, href=route_href(ks_package, 'release'))

    # Report Snap release progress.
    if bug.get('variant') == 'snap-debs':
        thing_prefix = 's:'
        for risk in ['edge', 'beta', 'candidate', 'stable']:
            status = __task_status(bug, 'snap-release-to-' + risk)
            href = None
            if "snap-name" in b:
                href = f"https://snapcraft.io/{b['snap-name']}/releases"
            add_in(thing_in, risk, status, href=href)

    # State sets.
    test_set_invalid = ('n/a', 'New', 'Invalid')
    test_set_complete = ('n/a', 'Invalid', 'Fix Released', "Won't Fix")

    # debs: testing status mashup (early phase Touch Testing)
    boot_testing_status = __task_status(bug, 'boot-testing')
    abi_testing_status = __task_status(bug, 'abi-testing')
    promote_to_proposed_status = __task_status(bug, 'promote-to-proposed')
    sru_review_status = __task_status(bug, 'sru-review')
    new_review_status = __task_status(bug, 'new-review')
    # Suppress new-review on the dashboard till it is in Triaged.
    if new_review_status == 'Confirmed':
        new_review_status = 'New'
    testing_valid = (
            boot_testing_status not in test_set_invalid or
            abi_testing_status not in test_set_invalid or
            new_review_status not in test_set_invalid or
            sru_review_status not in test_set_invalid)
    testing_complete = (
            boot_testing_status in test_set_complete and
            abi_testing_status in test_set_complete and
            new_review_status in test_set_complete and
            sru_review_status in test_set_complete)
    if testing_valid and not testing_complete:
        retval = ''

        color = __testing_status_colors[boot_testing_status]
        boot_testing_status = __testing_status_text.get(boot_testing_status, boot_testing_status)
        retval += tagged_block_valid('bt:', boot_testing_status, color)
        color = __testing_status_colors[abi_testing_status]
        abi_testing_status = __testing_status_text.get(abi_testing_status, abi_testing_status)
        retval += tagged_block_valid('At:', abi_testing_status, color)
        color = __review_status_colors[sru_review_status]
        sru_review_status = __review_status_text.get(sru_review_status, sru_review_status)
        retval += tagged_block_valid('sr:', sru_review_status, color)
        if new_review_status != 'Invalid':
            color = __review_status_colors[new_review_status]
            new_review_status = __review_status_text.get(new_review_status, new_review_status)
            retval += tagged_block_valid('nr:', new_review_status, color)
        else:
            retval += tagged_block('', '')

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
    signing_signoff_status = __task_status(bug, 'signing-signoff')
    signoff_valid = (
            security_signoff_status not in ('n/a', 'New', 'Invalid') or
            kernel_signoff_status not in ('n/a', 'New', 'Invalid') or
            stakeholder_signoff_status not in ('n/a', 'New', 'Invalid') or
            signing_signoff_status not in ('n/a', 'New', 'Invalid'))
    signoff_complete = (
            security_signoff_status in ('n/a', 'Invalid', 'Fix Released') and
            kernel_signoff_status in ('n/a', 'Invalid', 'Fix Released') and
            stakeholder_signoff_status in ('n/a', 'Invalid', 'Fix Released') and
            signing_signoff_status in ('n/a', 'Invalid', 'Fix Released'))
    if signoff_valid and not signoff_complete:
        retval = ''

        color = __testing_status_colors[security_signoff_status]
        retval += tagged_block_valid('ss:', security_signoff_status, color)

        color = __testing_status_colors[stakeholder_signoff_status]
        retval += tagged_block_valid('Ss:', stakeholder_signoff_status, color)

        color = __testing_status_colors[kernel_signoff_status]
        retval += tagged_block_valid('ks:', kernel_signoff_status, color)

        color = __testing_status_colors[signing_signoff_status]
        retval += tagged_block_valid('xs:', signing_signoff_status, color)

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
        (state, flags, reason) = reason.split(' ', 2)
        if task.startswith('prepare-package') and state != 'Stalled':
            continue
        # Elide things which are on one of the three "status box" rows.
        if 's' in flags:
            continue
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

        workflow_status = __task_status(bug, 'kernel-sru-workflow')
        if workflow_status not in ('Invalid', 'Fix Committed', 'Fix Released'):
            bites.append(bite_format(thing_prefix, retval, thing_in))

    return bites, thing_in

%>
<%
import re
import urllib.parse
from datetime import datetime, timezone

def cycle_key(cycle):
    # Move any cycle type prefix character to the end.
    if not cycle[0].isdigit():
        cycle = cycle[1:] + cycle[0]
    return cycle

# Match the suffix on linux-uc20 and linux-uc22-efi style packages.  We will
# subsitute this off as the primary "package" so that we consider them more
# like dependent packages of the primary kernel from an ordering perspective.
pkg_key_re = re.compile(r"-uc[0-9]+(?:-efi)?")
def pkg_key(pkg):
    bits = pkg.split()
    bits[0] = pkg_key_re.sub("", bits[0])

    return bits[0], pkg

cycles = {}
cadence = {}
owners = {}
swm_trackers = data['swm'].trackers
for bid in sorted(swm_trackers):
    b = swm_trackers[bid]

    try:
        cycle = 'unknown'
        spin = '?'
        if 'cycle' in b:
            (cycle, spin) = (b['cycle'].split('-') + ['?'])[0:2]

        package = b.get('source') or 'unknown'
        version = b.get('version') or '-'

        if 'snap-name' in b:
            package = package + ' / ' + b['snap-name']
    except:
        cycle = 'unknown'
        package = 'unknown'
        version = 'unknown'

    cycles[cycle] = True

    phase = b.get('phase') or 'unknown (no phase set)'

    stream = b.get('built', {}).get('route-entry') or '-'

    sn = b.get('series') or 'unknown'

    abi_testing = b.get('comments', {}).get('abi-testing')
    kernel_signoff = b.get('comments', {}).get('kernel-signoff')
    signing_signoff = b.get('comments', {}).get('signing-signoff')
    for pocket, prefix in (
        ('proposed', '/debs/'),
        ('beta', '/snaps/'),
    ):
        ct_testing = b.get('test-observer', {}).get(pocket)
        if ct_testing is not None:
            ct_testing = prefix + str(ct_testing)
            break

    if cycle not in cadence:
        cadence[cycle] = {}
    if sn not in cadence[cycle]:
        cadence[cycle][sn] = {}
    if package not in cadence[cycle][sn]:
        cadence[cycle][sn][package] = []

    # Pull together any suplemental links etc we need.
    attrs = {}
    attrs['at:'] = 'http://kernel.ubuntu.com/adt-matrix/{}-{}.html'.format(sn, package.replace('linux', 'linux-meta'))
    if abi_testing is not None:
        attrs['At:'] = 'https://bugs.launchpad.net/kernel-sru-workflow/+bug/{}/comments/{}'.format(bid, abi_testing)
    if kernel_signoff is not None:
        attrs['ks:'] = 'https://bugs.launchpad.net/kernel-sru-workflow/+bug/{}/comments/{}'.format(bid, kernel_signoff)
    if signing_signoff is not None:
        attrs['xs:'] = 'https://bugs.launchpad.net/kernel-sru-workflow/+bug/{}/comments/{}'.format(bid, signing_signoff)
    if ct_testing is not None:
        attrs['ct:'] = 'https://test-observer.canonical.com/#{}'.format(ct_testing)
    attrs['vt:'] = 'http://kernel.ubuntu.com/reports/sru-report.html#{}--{}'.format(sn, package)
    attrs['rt:'] = 'http://test-results.kernel/{}/rtr-lvl1.html#{}:{}:{}:sru'.format(cycle, sn, package, urllib.parse.quote_plus(version))
    attrs['bt:'] = 'http://test-results.kernel/{}/rtr-lvl1.html#{}:{}:{}:boot'.format(cycle, sn, package, urllib.parse.quote_plus(version))

    attrs['tooltip-at:'] = 'Automated Testing'
    attrs['tooltip-At:'] = 'ABI Testing'
    attrs['tooltip-ct:'] = 'Certification Testing'
    attrs['tooltip-rt:'] = 'Regression Testing'
    attrs['tooltip-vt:'] = 'Verification Testing'
    attrs['tooltip-bt:'] = 'Boot Testing'
    attrs['tooltip-ss:'] = 'Security Signoff'
    attrs['tooltip-Ss:'] = 'Stakeholder Signoff'
    attrs['tooltip-xs:'] = 'Signing Signoff'
    attrs['tooltip-ks:'] = 'Kernel Signoff'
    attrs['tooltip-nr:'] = 'New Review'
    attrs['tooltip-sr:'] = 'SRU Review'

    # Look the current package up in the appropriate cycle.
    ks_package = None
    ks = data["kernel-series"].for_cycle(cycle)
    if ks is None:
        ks = data["kernel-series"].tip()
    if ks is not None:
        ks_series = ks.lookup_series(codename=sn)
        if ks_series is not None:
            ks_package = ks_series.lookup_source(package)

    status_list, thing_in = __status_bites(b, attrs, ks_package=ks_package)
    first = True
    #row_style = ' background: #f0f0f0;' if row_number % 2 == 0 else ''
    row_class = ['entry-any']
    master_class = 'master' if 'master-bug' not in b else 'derivative'

    row_owner = b.get('owner', 'unassigned')
    row_class.append('owner-' + row_owner)
    if row_owner != 'unassigned':
        owners[row_owner] = row_class

    sru_review_status = __task_status(b, 'sru-review')
    ptp_status = __task_status(b, 'promote-to-proposed')
    if (sru_review_status not in ('n/a', 'Invalid', 'New', 'Fix Released') or
            ptp_status not in ('n/a', 'Invalid', 'New', 'Fix Released')):
        row_class.append('phase-reviews')

    if b.get('flag', {}).get('jira-in-review', False):
        row_class.append('phase-peer-reviews')

    snap_tasks = ['snap-prepare']
    for risk in ('edge', 'beta', 'candidate', 'stable'):
        snap_tasks.append('snap-release-to-' + risk)
    for snap_task in snap_tasks:
        status = __task_status(b, snap_task)
        if status not in ('n/a', 'Invalid', 'New', 'Fix Released'):
            row_class.append('phase-snap-promotions')
            break

    for testing_task in ('boot-testing', 'abi-testing', 'automated-testing',
            'certification-testing', 'regression-testing', 'verification-testing'):
        status = __task_status(b, testing_task)
        if status not in ('n/a', 'Invalid', 'New', 'Fix Released'):
            row_class.append('phase-testing')
            break

    for testing_task in ('boot-testing', 'abi-testing', 'automated-testing',
            'certification-testing', 'regression-testing', 'verification-testing',
            'snap-certification-testing', 'snap-qa-testing'):
        status = __task_status(b, testing_task)
        if status not in ('n/a', 'Invalid', 'New', 'Fix Released'):
            testing_task = testing_task.replace('snap-', '')
            row_class.append('phase-' + testing_task)

    for task_name in ('promote-to-updates', 'promote-to-security',
            'promote-to-release'):
        status = __task_status(b, task_name)
        if status not in ('n/a', 'Invalid', 'New', 'Fix Released'):
            row_class.append('phase-deb-promotions')
            break

    for task_name in b['task']:
        if not task_name.startswith('prepare-package') and task_name != 'snap-prepare':
            continue
        status = __task_status(b, task_name)
        if status not in ('n/a', 'Invalid', 'New', 'Fix Released'):
            row_class.append('phase-prepare')
            break

    for task_name in ('signing-signoff', 'kernel-signoff'):
        status = __task_status(b, task_name)
        if status not in ('n/a', 'Invalid', 'New', 'Fix Released'):
            row_class.append('phase-team-signoffs')
            break

    row_class.append('cycle-' + cycle)

    for status in status_list:
        status_row = {'bug': None, 'version': None, 'phase': status, 'spin': spin, 'master-class': master_class, 'row-class': ' '.join(row_class)}
        if first:
            status_row['bug'] = bid
            status_row['version'] = version
            status_row['stream'] = stream
            status_row['thing-in'] = thing_in
            first = False
        cadence[cycle][sn][package].append(status_row)

%>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" dir="ltr" lang="en-US">
    <head>
        <style>
        .name a {
            color: green;
            #background-color: transparent;
            text-decoration: none;
        }

        .master a {
            color: darkblue;
            #background-color: transparent;
            text-decoration: none;
        }

        .overdue .name a {
            color: red;
        }

        a.archive {
            color: inherit;
            text-decoration: none;
        }

        .note a {
            color: black;
            background-color: transparent;
            text-decoration: none;
        }

        /* Tooltip container */
        .tooltip {
          position: relative;
          display: inline-block;
        }

        /* Tooltip text */
        .tooltip .tooltiptext {
          visibility: hidden;
          width: 600px;
          background-color: black;
          color: #fff;
          text-align: left;
          padding: 10px;
          border-radius: 6px;

          /* Position the tooltip text. */
          position: absolute;
          z-index: 1;
          top: 10px;
          right: 105%;
        }

        /* Show the tooltip text when you mouse over the tooltip container */
        .tooltip:hover .tooltiptext {
          visibility: visible;
        }
        .tooltip:focus .tooltiptext{
          visibility: visible;
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
                                    <label for="limit-owner">Owner:</lable>
                                    <select name="limit-owner" id="limit-owner" onchange=selectAll() style="font-size: 0.8em">
                                        <option value="all">All</option>
                                    % for owner in sorted(owners):
                                        <!-- <button class="toggle-pressed" onclick="toggleOwners('${owner}')" id="toggle-${owner}">${owner}</button> -->
                                        <option value="${owner}">${owner}</option>
                                    % endfor
                                        <option value="unassigned">Unassigned</option>
                                    </select>
                                    &nbsp;
                                    <label for="limit-phase">Phase:</lable>
                                    <select name="limit-phase" id="limit-phase" onchange=selectAll() style="font-size: 0.8em">
                                        <option value="all">All</option>
                                        <option value="prepare">prepare</option>
                                        <option value="reviews">reviews</option>
                                        <option value="peer-reviews">peer-reviews</option>
                                        <option value="team-signoffs">team-signoffs</option>
                                        <option value="deb-promotions">deb-promotions</option>
                                        <option value="snap-promotions">snap-promotions</option>
                                        <option value="testing">testing</option>
                                        <option value="boot-testing">&nbsp;&nbsp;boot-testing</option>
                                        <option value="abi-testing">&nbsp;&nbsp;abi-testing</option>
                                        <option value="automated-testing">&nbsp;&nbsp;automated-testing</option>
                                        <option value="certification-testing">&nbsp;&nbsp;certification-testing</option>
                                        <option value="regression-testing">&nbsp;&nbsp;regression-testing</option>
                                        <option value="verification-testing">&nbsp;&nbsp;verification-testing</option>
                                    </select>
                                    &nbsp;
                                    <label for="limit-cycle">Cycle:</lable>
                                    <select name="limit-cycle" id="limit-cycle" onchange=selectAll() style="font-size: 0.8em">
                                        <option value="all">All</option>
                                    % for cycle in sorted(cycles, key=cycle_key):
                                        <option value="${cycle}">${cycle}</option>
                                    % endfor
                                    </select>
                                    </td></tr>

                                    <table width="100%" style="font-size: 0.8em"> <!-- SRU Data -->
                                    <%
                                        releases = data['releases']
                                        releases['00.00'] = 'unknown'
                                        cycle_first = True
                                        now = datetime.now(timezone.utc).date()
                                    %>
                                    % for cycle in sorted(cycles, key=cycle_key):
                                        % if cycle_first is False:
                                            <tr class="entry-any owner-any phase-any">
                                                <td colspan="7">&nbsp;</td>
                                            </tr>
                                        % endif
                                        <%
                                            cycle_first = False
                                            sru_cycle = data['sru-cycle'].lookup_cycle(cycle)
                                            cycle_notes = ""
                                            cycle_readme = ""
                                            cycle_readme_public = data['readme'].get(cycle)
                                            if sru_cycle is not None:
                                                cycle_notes = "{} to {}".format(sru_cycle.start_date, sru_cycle.release_date)
                                                if sru_cycle.notes_link is not None:
                                                    if cycle_readme_public is not None:
                                                        cycle_readme += '<div class="tooltip" tabindex="1">Notes<span class="tooltiptext">' + cycle_readme_public + '</span></div>'
                                                else:
                                                    cycle_readme += '<span style="color: grey;">Notes</span>'
                                                cycle_readme += '<a href="https://warthogs.atlassian.net/browse/' + sru_cycle.notes_link + '">&thinsp;&copysr;</a>'
                                        %>
                                        <tr class="entry-any owner-any phase-any cycle-${cycle}" style="background: #ffffc0; font-size: 140%;">
                                            <td colspan="1" >${cycle}</td><td colspan="4" class="note" style="text-align: right;">${cycle_readme}</td><td colspan="2" style="text-align: right;">${cycle_notes}</td>
                                        </tr>
                                        % for rls in sorted(releases, reverse=True):
                                            <%
                                                codename = releases[rls].capitalize()
                                                row_number = 0
                                            %>
                                            % if releases[rls] in cadence[cycle] and len(cadence[cycle][releases[rls]]) > 0:
                                                % for pkg in sorted(cadence[cycle][releases[rls]], key=pkg_key):
                                                    % for bug in cadence[cycle][releases[rls]][pkg]:
                                                        <%
                                                            cell_version = '&nbsp;'
                                                            cell_package = '&nbsp;'
                                                            cell_spin = '&nbsp;'
                                                            cell_stream = '&nbsp;'
                                                            cell_in = '&nbsp;'
                                                            if bug['bug'] is not None:
                                                                url = "https://bugs.launchpad.net/ubuntu/+source/linux/+bug/%s" % bug['bug']
                                                                cell_version = '<a href="{}">{}</a>'.format(url, bug['version'])
                                                                cell_package = '<a href="{}">{}</a>'.format(url, pkg)
                                                                cell_spin = '#{}'.format(bug['spin'])
                                                                cell_in = 'in: ' + __coloured('/', 'silver').join(bug['thing-in'])
                                                                cell_stream = bug['stream']
                                                                row_number += 1
                                                            row_style = ' background: #f6f6f6;' if row_number % 2 == 0 else ''
                                                            if sru_cycle is not None and now > sru_cycle.release_date:
                                                                overdue = " overdue"
                                                            else:
                                                                overdue = ""
                                                        %>
                                                        % if row_number == 1 and bug['bug'] is not None:
                                                            <tr class="entry-any owner-any phase-any cycle-${cycle}">
                                                                <td colspan="7" style="background: #e9e7e5;">${rls} &nbsp;&nbsp; ${codename}</td>
                                                            </tr>
                                                        % endif
                                                        <tr class="${bug['row-class']}${overdue}" style="line-height: 100%;${row_style}">
                                                            <td>&nbsp;</td>
                                                            <td width="120" align="right" class="${bug['master-class']} name">${cell_version}</td>
                                                            <td class="${bug['master-class']} name">${cell_package}</a></td>
                                                            <td style="color: grey">${cell_spin}</td>
                                                            <td>${bug['phase']}</td>
                                                            <td>${cell_stream}</td>
                                                            <td>${cell_in}</td>
                                                        </tr>
                                                    % endfor
                                                % endfor
                                            % endif
                                        % endfor
                                    % endfor
                                    % if cycle_first is True:
                                        <tr>
                                            <td colspan="7">No active SRU cycle at this time (see <a href="https://kernel.ubuntu.com/">kernel.ubuntu.com</a> for any announcements).</td>
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
