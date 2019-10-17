#                             Verification Testing

When packages are copied to -proposed, we request the reporters of the bugs
fixed by these releases to verify if the issues are really fixed by the new
builds.

These requests are done automatically by SWM (Stable Workflow Manager),
which collects the bugs that need to be verified from the changelog entries of
the new version. SWM then adds a new comment to the bug reports, asking for
verification and stating that if not verified the fix might be dropped from the
release. It also adds a tag to the bug in the format
'verification-needed-[series]'. The reporters are then asked to change that tag
to 'verification-done-[series]' if the verification was successful, or
'verification-failed-[series]' otherwise.

Please note that only bugs fixed by the master kernels are "spammed" for
verification, backports and derivatives are not required to be verified.

The following report is generated with the verification status of the packages
currently in -proposed:

https://kernel.ubuntu.com/reports/sru-report.html

This report is not generated in real-time, so it might take some minutes for
it to be updated.

The report lists all the packages, including derivatives and backports, but
only the master kernels are relevant. The report adds a small icon on the
left-hand side of the bug with the current status of the verification, based
on the verification tags. Upstream stable update bugs have a special icon
(a magnifying glass) and are not required to be verified.

## Nagging bug reporters

After all the packages are in -proposed, we should allow some days for the bug
reporters to verify the fixes. If the bugs are still not verified after around
a week in -proposed, we should start nagging the bug reporters reminding of the
verification.

The most common methods for nagging are:
 - IRC (most efficient for people inside Canonical).
 - Additional comments on the bug.

## Failed verification

When the verification of a bug fix fails, we need to make a decision on a
per-case situation. If the bug was not completely fixed but the state is not
worse than before, we generally keep the changes and make sure people are
aware and will work on a follow-up fix. If the changes introduced a regression,
most of times the best solution is to revert (or remove) the patches and re-spin
the packages as soon as possible.

## Non verified fixes

When approaching the end of the cycle, if there are bugs that are still not
verified, we also need to make a per-case decision. In general, if the changes
are not critical (e.g. HW fixes or enablement) the most common decision is to
keep the patches as the regression potential for users is low. If the changes
are critical or impose a high risk of regression, we might consider removing
the patches and re-spinning the kernels.

## Tracking bugs update

The tracking bug task which is used for tracking the verification status is
'verification-testing'. As of now, this task needs to be manually updated based
on the SRU report. This task needs to be set to 'Fix Released' in order to
allow the package to be promoted to -updates/-security. If the release of a
package needs to be put on hold because of failed verification, the task
should be set to another state (e.g. 'Incomplete').

Only the master kernels tracking bugs need to have the 'verification-testing'
task updated. Once its done, SWM copies the status to all its derivatives and
backports.

## ESM and private kernels

The ESM and private kernels might receive bug fixes that need to be verified
before the release. Currently the SRU report doesn't include these fixes
because the kernels are uploaded to private PPA's, and for the same reason
the bugs are not spammed for verification.

Due to that issue, these kernels (mainly the master kernels of the ESM series)
need special attention. As of this writing, the only method to check which bugs
need verification is looking at the packages changelog and check which fixes
were applied. Note that it's also possible that fixes are applied without a link
to a public bug report, so following the references to any other report (e.g.
SalesForce case) might be needed to gather more information.
