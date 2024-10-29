from jinja2 import Environment, FileSystemLoader
import json
import subprocess
from glob import glob
import datetime
import re

env = Environment(loader=FileSystemLoader("templates"))
template = env.get_template("dash.jinja")

period = "3 month"
end_date = subprocess.run(["date", "--date=today", "+%Y/%m/%d"], stdout=subprocess.PIPE).stdout.decode("utf-8")
begin_date = subprocess.run(
    ["date", "--date=" + end_date + "- " + period + " + 1 day", "+%Y/%m/%d"], stdout=subprocess.PIPE
).stdout.decode("utf-8")
with open("pending.json", "w") as outfile:
    subprocess.run(["env", "LC_ALL=C.UTF-8", "./pending_SRU.sh", "-p", period, "-j"], stdout=outfile)
with open("all.json", "w") as outfile:
    subprocess.run(["env", "LC_ALL=C.UTF-8", "./pending_SRU.sh", "-a", "-p", period, "-j"], stdout=outfile)

with open("pending.json") as input:
    pending_patchsets_search = json.load(input)
    pending_patchsets = []
    active_reviewers = []
    print(len(pending_patchsets_search))
    for patch_cover in pending_patchsets_search:
        print(patch_cover["path"])
        date = subprocess.run(
            ["env", "LC_ALL=C.UTF-8", "mu", "find", "-f", "d", "--nocolor", 'path:"' + patch_cover["path"] + '"'],
            stdout=subprocess.PIPE,
        ).stdout.decode("utf-8")
        patchset = {
            "subject": patch_cover["subject"],
            "date": date,
            "author": patch_cover["from"],
            "email": patch_cover["email"],
            "pending_acks": patch_cover["pending_acks"],
            "patches": [],
            "result": "",
            "status": [],
            "reviewer": patch_cover["reviewer"],
        }
        if patch_cover["reviewer"]:
            active_reviewers.append(patch_cover["email"])
        active_reviewers.append(patch_cover["reviewer"])
        related_patches = json.loads(
            subprocess.run(
                ["mu", "find", "-r", "-o", "json", 'path:"' + patch_cover["path"] + '"'], stdout=subprocess.PIPE
            ).stdout.decode("utf-8")
        )

        # Find all results associated
        for results in glob(patch_cover["path"] + ".*.*_*"):
            match = re.search(patch_cover["path"] + "\\.(.*)\\.(.*)_(.*)", results)
            status = {"serie": match.group(1), "operation": match.group(2)}
            res = match.group(3)
            if "failed" in res or "fail" in res:
                status["ret"] = "1"
            if "succeed" in res or "pass" in res:
                status["ret"] = "0"
            with open(results) as f:
                status["comment"] = f.read()
            patchset["status"].append(status)

        # Find all patches to list them
        for patch in related_patches:
            patch["body"] = subprocess.run(
                ["env", "LC_ALL=C.UTF-8", "mu", "view", patch[":path"]], stdout=subprocess.PIPE
            ).stdout.decode("utf-8")
            patch["subject"] = patch[":subject"]
            patchset["patches"].append(patch)
        pending_patchsets.append(patchset)

with open("all.json") as input:
    total = len(json.load(input))
with open("renders/index.html", "w") as f:
    print(
        template.render(
            active_reviewers=list(set(active_reviewers)),
            total_patchsets=total,
            pending_patchsets=pending_patchsets,
            date=datetime.datetime.now(datetime.UTC),
            begin_date=begin_date,
            end_date=end_date,
        ),
        file=f,
    )
with open("renders/raw.json", "w") as f:
    print(json.dumps(pending_patchsets, indent=4), file=f)
