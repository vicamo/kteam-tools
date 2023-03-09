#!/usr/bin/python3

# SPDX-FileCopyrightText: Canonical Ltd.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import re

def summary_is_relaxed_pass(summary):
    '''
    An autopkgtest summary file contains autopkgtest test result logs. This
    function validates if all reported tests are either marked as PASS
    (including superficial), SKIP or FLAKY while at least one was reported as
    PASS (including superficial). In other words, not all tests were ignored.
    '''

    pass_result = re.compile(r'^^(\S+)\s+(PASS|SKIP|FLAKY).*$')
    passed = False

    if not summary:
        return False

    for line in summary.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        match = pass_result.match(line)
        if not match:
            return False
        if not passed and match[2] == 'PASS':
            passed = True

    return passed
