#!/usr/bin/python3

# SPDX-FileCopyrightText: Canonical Ltd.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import unittest

from adt_matrix.misc import summary_is_relaxed_pass

class TestAdtMatrixMisc(unittest.TestCase):
    def test_summary_is_relaxed_pass(self):
        # Some random edge cases.
        self.assertFalse(summary_is_relaxed_pass(''))
        self.assertFalse(summary_is_relaxed_pass(None))
        self.assertFalse(summary_is_relaxed_pass('\n'))
        self.assertFalse(summary_is_relaxed_pass('\n  '))
        self.assertFalse(summary_is_relaxed_pass(' \n'))

        # Simple 'one-test' cases.
        summary='dkms-autopkgtest     PASS'
        self.assertTrue(summary_is_relaxed_pass(summary))
        summary='dkms-autopkgtest     PASS (superficial)'
        self.assertTrue(summary_is_relaxed_pass(summary))
        summary='dkms-autopkgtest     FAIL'
        self.assertFalse(summary_is_relaxed_pass(summary))
        summary='dkms-autopkgtest     SKIP'
        self.assertFalse(summary_is_relaxed_pass(summary))
        summary='dkms-autopkgtest     FLAKY'
        self.assertFalse(summary_is_relaxed_pass(summary))
        summary='dkms-autopkgtest     PASS (superficial)\n  '
        self.assertTrue(summary_is_relaxed_pass(summary))
        summary='dkms-autopkgtest     PASS (superficial)\n\n    \n  '
        self.assertTrue(summary_is_relaxed_pass(summary))

        # Validate on PASS and superficial PASS.
        summary='\
dkms-autopkgtest      PASS (superficial)\n\
test_dm-writeboost.sh PASS\n\
'
        self.assertTrue(summary_is_relaxed_pass(summary))

        # Fail when at least on test failed.
        summary='\
rebuild               FAIL non-zero exit status 2\n\
test_dm-writeboost.sh PASS\n\
dkms-autopkgtest      PASS (superficial)\n\
'
        self.assertFalse(summary_is_relaxed_pass(summary))

        # Pass if all tests passed, are skipped or marked flaky but at least
        # one has passed.
        summary='\
rebuild               SKIP not now\n\
test_dm-writeboost.sh SKIP not now\n\
dkms-autopkgtest      SKIP\n\
dkms-autopkgtest1     FLAKY\n\
dkms-autopkgtest1     PASS (superficial)\n\
'
        self.assertTrue(summary_is_relaxed_pass(summary))

        # Fail if everything was ignored (SKIP or FLAKY).
        summary='\
rebuild               SKIP not now\n\
test_dm-writeboost.sh SKIP not now\n\
dkms-autopkgtest      SKIP\n\
dkms-autopkgtest      FLAKY\n\
'
        self.assertFalse(summary_is_relaxed_pass(summary))

if __name__ == '__main__':
    unittest.main()
