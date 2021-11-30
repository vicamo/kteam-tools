# Hinting Regression Tests (RT)

Results from the boot and sru regression testing (RT) are collected and
reported at [http://sita/rtr-lvl0.html](http://sita/rtr-lvl0.html). Test
failures for individual test cases can be hinted to be interpretd as a passing
result.

Hints can be used to mark known test failures to avoid reviewing these tests on
future cycles. Hints can also be used to indicate a specific test failure has
been reviewed and determined not to be a regression. Judgement should be used
to not define a hint so broadly so as to unintentionally hide future
regressions.

## Reviewing Test Results

The first step is to review the test results and identify if any test cases
should be hinted. Each test report page belongs to a single test suite with
each test suite consisting of one or more test cases. If using the report
pages, the test cases are listed in the left side navigation panel and will be
indicated with a `PASS` or `FAIL` result. Clicking on these test case names
will jump the report to the end of the test case output in the report log. When
creating a hint, it is these test case names which will be checked against the
regular expression in the hint.

### Reviewing the raw report log

It is possible to review just the raw log file. This may be perfered when
working with large test reports. The following would fetch all of the
`ubuntu_ltp_syscalls` results for the `linux-aws` kernel for version
`5.13.0-1007.8`.  Note: the base url,
`http://sita/2021.11.08/impish/linux-aws/5.13.0-1007.8`, matches the base URL
of the kernel `lvl2` results matrix.

    wget -r -l1 -np http://sita/2021.11.08/impish/linux-aws/5.13.0-1007.8/ \
        -A "sru-aws-aws-*-ubuntu_ltp_syscalls-log.txt"

When reviewing the raw log files, test cases can be identified with the `START`
and `END ${RESULT}` markers. For example:

    09:56:31 INFO |     START    ubuntu_kernel_selftests.net:rtnetlink.sh    ubuntu_kernel_selftests.net:rtnetlink.sh    timestamp=1638266191    timeout=1800    localtime=Nov 30 09:56:31
    09:56:31 DEBUG| Persistent state client._record_indent now set to 2
    09:56:31 DEBUG| Persistent state client.unexpected_reboot now set to ('ubuntu_kernel_selftests.net:rtnetlink.sh', 'ubuntu_kernel_selftests.net:rtnetlink.sh')
    09:56:31 DEBUG| Waiting for pid 15677 for 1800 seconds
    ... snip ...
    09:56:47 INFO |     END ERROR    ubuntu_kernel_selftests.net:rtnetlink.sh    ubuntu_kernel_selftests.net:rtnetlink.sh    timestamp=1638266207    localtime=Nov 30 09:56:47

The test suite, `ubuntu_kernel_selftests`, and test case, `net:rtnetlink.sh`
are emedded in the `START` and `END` markers. You will need both of these when
creating the hint. Some test suites have additional levels of sub test cases.
However, it is currenty only possible to hint at the top level test case. Look
for the specific `END ERROR` marker lines as indicated in the example to find
the parent test case name.

## Creating and Updating Hints

The regression testing hints are defined in yaml files located in the git repo:

  lp:~canonical-kernel-team/+git/rt-hints

The hints are organized into individual files according to series and kernel
package. Once a change is made and pushed to the repo, it will become visibile
after the next report update. These occur every 30 minutes, meaning a change to
a hint could take up to 1 hour to be visible in the report.


### Hint file names

Hint files are named according to the following format:

    ${series-codename}-${kernel-source-package}.yaml

Hint files must end in `.yaml` and be valid yaml formatted files. All other
files are ignored by the parser.

Examples:

    focal-linux.yaml
    focal-linux-aws.yaml
    bionic-linux-hwe-5.11.yaml

Kernels without a corresponding hint file will have no hints applied.


### Hint file format

The hints are organized by the test suite name with an optional `DEFAULTS`
dictionary to specify file specific default values. Each test suite specifies
a list of hints in standard yaml format.

For example:

    DEFAULTS:
        key: value
    test_suite_name_1:
      - key: hint_1 value
        key2: hint_1 value2
      - key: hint_2 value
        key2: hint_2 value2
        key3: hint_2 value3
    test_suite_name_2:
      - key: hint_3 value
        key2: hint_3 value2

The test suite names must be an exact match for the test suite to be hinted.
The keys must consist of one of the valid key values below. Keys can be
ommitted in which case the default is used or `.*` if no default is specified.
Invalid key names will result in an error.

The valid keys and their meanings are:

 * series: regex for the ubuntu series codename (`focal`)
 * source: regex for the kernel source package name (`linux`,
   `linux-hwe-5.11`)
 * version: regex for the source package version (`5.4.0.*`)
 * flavour: regex for the kernel flavour (`generic`)
 * arch: regex for the kernel package architecture (`ppc64el`)
 * cloud: regex for the testing cloud (`metal`, `aws`, `azure`, `gcp`, `gke`,
   `oracle`)
 * instance-type: regex for the cloud instance type or maas machine names
   (`.*metal`, `f1-micro`, `gonzo`)
 * test-case: regex of the test case to match (`net`, `memory-hotplug`)
 * state: used to indicate how the hint is applied. Currently only one state
   is allowed:
   + `FLAKY` - Used to set a `failed` test to `hinted`, leaving `passed`
     results as `passed`. This is the default if no value is indicated.
 * comment: A free form string to provide basis for the rule or link to a bug. It is recommended to enclose this string in quotes so as to avoid the contents being interpretted as different yaml elements.

Examples:

    DEFAULTS:
      series: groovy
      source: linux
    ubuntu_lttng_smoke_test:
      - version: 5.8.0.*
        cloud: gcp
        instance-type: f1-micro
        state: FLAKY
        comment: 'lp:#1926962 - ubuntu_lttng_smoke_test failure on google f1-micro'
      - version: 5.8.0.*
        cloud: aws
        instance-type: .*nano
        state: FLAKY
        comment: 'lp:#1926962 - ubuntu_lttng_smoke_test failure on aws nano instances'
    ubuntu_kernel_selftests:
      - version: 5.8.0.*
        cloud: .*
        instance-type: .*
        test-case: net
        state: FLAKY
        comment: 'lp:#12345 - ubuntu_kernel_selftests.net is broken'


### Hint Checking

Hints can be checked for basic correctness by running the parser:

    ./run-test.sh

Please add it via pre-commit hoot:

    ln -s ../../etc/pre-commit .git/hooks/

You can compile hints manually with:

    compile-hints . /dev/null

An empty output is a sign of goodness. If you want to see the resulting hint
dictionaries, substitute `/dev/null` with a valid directory name.
