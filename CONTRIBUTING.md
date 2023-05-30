# Contributing

Contributions are welcome!

Some guidelines:

- Our minimum Python version is pinned to Focal which means everything must
run on **Python 3.8**.

- Dependencies must be installable from apt. Again, we're pinned to Focal so
use the highest version available on Focal.

- All new Python code should have basic test coverage using the unittest
module.

- Sign off all of your commits

## Merge Requests / Pull Requests

### Canonical Kernel Team

We are currently putting Gitea on trial for code review. Yes, kteam-tools is a
different animal than kernels but this is a test bed for flexing the process.
If you are a Canonical employee:

1. Follow the [Getting Started Guide](https://canonical-kteam-docs.readthedocs-hosted.com/en/latest/docs/code-review/getting_started.html)
2. That's it.

### External Contributors

Please submit a [merge proposal](https://code.launchpad.net/~canonical-kernel/+git/kteam-tools/+ref/master/+register-merge)
to Launchpad and be sure to add `Canonical Kernel` as a reviewer. Someone from
our team will review your contribution when possible.

## TODO

[ ] Establish formatting rules for Python (ruff)

[ ] Establish linting rules for Python (ruff)

[ ] Establish shell format/linting rules

