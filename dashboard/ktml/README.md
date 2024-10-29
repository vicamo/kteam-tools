
# KTML dashboard generation

Besides regular shell dependencies (such as grep, sort, etc), these
scripts also depend on `mu`, `jq` and `cranky`.

`mu` is used to index emails and it assumes you have a way to retrieve
your emails to a local maildir using something like `mbsync`/`isync`
or `offlineimap`. `jq` is used to parse the json output from `mu`.

You can find more information about `mu` and to set it up at the
following links:

https://www.djcbsoftware.nl/code/mu/

https://www.djcbsoftware.nl/code/mu/mu4e/

# Workflow

`pending_SRU.sh` is using mu to find patchset cover which are neither ACKed twice, NACKed, nor applied.
This output a json file where each entry is a pending submission:

```
[
	{"subject": "[SRU][N][J][PATCH 0/1] s390/cpum_cf: make crypto counters upward compatible (LP: 2074380)",
	"path": "/home/thibf/canonical/.mozilla/thunderbird/139xj4oc.default-release/ImapMail/imap.gmail.com/kernel-team/cur/20240801105355.547635-1-frank.heimes@canonical.com.eml",
	"from": "Frank Heines <frank.heimes@canonical.com>",
	"email":"frank.heimes@canonical.com",
	"pending_acks": 1,
	"reviewer":"kevin.becker@canonical.com"}
]
```

# Checks

`check_pending.sh` takes the output from `pending_sru.sh` to apply and build each kernel.

All the check results will be stored in the same directory of the mail files.
As: 'ahsdgsdkga.eml.noble.XX_failed' or 'ahsdgsdkga.eml.noble.XX_suceeded'
The content of the file is used as a comment which is available by hovering
the results in the dashboard.

# Dashboard

`dashboard_gen.py` takes the output from `pending_sru.sh` to build an html page base on the template
in `templates` directory which is written to renders directory.
