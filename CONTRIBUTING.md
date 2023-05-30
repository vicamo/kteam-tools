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

## Development

Development on kteam-tools requires adhering to our coding style and lint checks.
We use the following tools:

- **black**: Python code style, all default (except line length is raised to 120 from 88)
- **ruff**: Python linter, all defaults
- **shellcheck**: Shell linter, all defaults

For more information see `pyproject.toml`.

All of these checks can be run as a pre-commit hook using [pre-commit](https://pre-commit.com).
Setting up pre-commit is straight forward:

```bash
pip install .[nag,testing]
pre-commit install
```
This will install runtime libraries, linters, and test dependencies. Once
installed, a git pre-commit hook will run the hooks defined in `.pre-commit-config.yaml`.
Your commit will be blocked until your changes satisfy all of the checks. Our CI
expects the same tests to pass in order for your PR to be accepted.

For example, one of our checks will trim trailing space from Python and shell
scripts. These changes are done automatically but it is up to you to stage them.

Another example is when shellcheck complains about something. You must manually
appease the warning or provide an annotated comment to suppress the issue.

```bash
# shellcheck disable=SC2086 # space separated string used as arg list
commit "$msg" $HELPERS
```


### FAQ

Q: Why bother enforcing source code formatting?
A: Standardization helps code readability scale across larger teams.

Q: Why are my neatly arranged lists, named function parameters, etc. getting
   collapsed into a single line?
A: PEP8 has changed a bit. Try adding [magic commas](https://black.readthedocs.io/en/stable/the_black_code_style/current_style.html#the-magic-trailing-comma) to
   tell black to respect your intent.

### Modifying Checks

Configuration changes are applied to `pyproject.toml`. This allows us to run
tools like black directly or from pre-commit and still produce the same result.
### Manual Checks

Each tool can be run directly from your system or explicitly through pre-commit.

Warning: We pin specific versions of each tool in `.pre-commit-config.yaml`. You
may see different results if the version on your system is different from what
our managed pre-commit environment is using.

```bash
# Run all checks in directory or list of file paths
pre-commit run --files some/glob/path* or/single/file

# Lint but do not black
SKIP=black pre-commit run --files some/glob/path* or/single/file

# Directly test black format compliance
black path/to/foo.py --check

# Directly apply black format
black path/to/foo.py

# Directly lint foo
ruff path/to/foo.py

# Directly lint and fix foo
ruff path/to/foo.py --fix

# Directly lint shell
ruff path/to/foo.sh
```
