import click
import json
import subprocess
import re
import functools
from pathlib import Path
import glob
import logging
from ktl.log import cerror, cnotice
from matching import match_handles, match_patch, match_patch_count


def log_result(patchset_path, target_serie, msg, isFail, operation):
    if isFail:
        result = "fail"
        cerror(msg)
    else:
        result = "pass"
        cnotice(msg)
    with open(f"{patchset_path}.{target_serie}.{operation}_{result}", "w") as f:
        print(msg, file=f)


@click.command()
@click.option("--pending", help="use file as input instead of calling pending_SRU.sh")
@click.option("--kernel-dir", default="~/canonical/kernel/ubuntu/", help="Directory containing kernel in $SERIE.")
@click.option("--dry-run", is_flag=True, default=False, help="Don't do any thing.")
@click.option("--verbose", is_flag=True, default=False)
@click.option("--period", default="3month", help="Period to look back for patches, default to 3month.")
def check_pending(pending, period, kernel_dir, dry_run, verbose):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(message)s")
    if pending:
        with open(pending) as input:
            pending_patchsets_search = json.load(input)
    else:
        pending_patchsets_search = json.loads(
            subprocess.run(["./pending_SRU.sh", "-p", period, "-j"], stdout=subprocess.PIPE).result.stdout
        )
    for patchset in pending_patchsets_search:
        subject = patchset["subject"]
        path = patchset["path"]
        try:
            handles = match_handles(subject)
        except AttributeError:
            log_result(path, "Unknown", f"Unable to find the handles of {subject}", True, "parsing")
            continue
        try:
            patch_cnt = match_patch_count(subject)
        except AttributeError:
            log_result(path, "Unknown", f"Unable to find the patch count of {subject}", True, "parsing")
            continue
        for handle in handles:
            official_handle = handle[1]
            raw_handle = handle[0]
            if official_handle is None:
                log_result(path, "Unknown", "Unable to understand handle", True, "parsing")
                continue
            serie = official_handle.split(":")[0]
            related_patches = json.loads(
                subprocess.run(
                    ["mu", "find", "-o", "json", "-r", "-u", f"path:{path}"], stdout=subprocess.PIPE
                ).stdout.decode("utf-8")
            )
            patches = []
            for i in range(1, int(patch_cnt) + 1):
                patch = None
                patch_subject = filter(
                    functools.partial(match_patch, raw_handle=raw_handle, index=i, patch_count=patch_cnt),
                    related_patches,
                )
                for patch in patch_subject:
                    patches.append(patch)
                if patch is None:
                    cerror(f"No patch found for {i}/{patch_cnt} for {subject}")
            if len(patches) < int(patch_cnt):
                log_result(path, official_handle, f"Failed to parse patches for {official_handle}", True, "parsing")
                continue
            # Check if we skip
            if Path(f"{path}.skip").is_file():
                cnotice(f"Skipping {subject}, {path}.skip exist")
                continue
            # Check if already built
            if glob.glob(f"{path}.{serie}.am_failed"):
                Path.unlink(f"{path}.{serie}.am_failed")

            # Check if building
            if glob.glob(f"{path}.{serie}.build_*") or glob.glob(f"{path}.{raw_handle}.build_*"):
                cnotice(f"Skipping {subject}, already built")
                continue

            cnotice(f"Working on {subject}/{serie}")
            if dry_run:
                continue

            # checkout correct kernel dir
            subprocess.run(["cranky", "checkout", official_handle, "--pristine"], check=True)

            kernel_path = (
                subprocess.run(["cranky", "shell-helper", "tree-main-path", official_handle], stdout=subprocess.PIPE)
                .stdout.decode("utf-8")
                .strip("\n")
            )

            # Apply patches
            cmd = ["git", "am", "--ignore-space-change"]
            cmd += [x[":path"] for x in patches]
            try:
                subprocess.run(cmd, cwd=kernel_path, check=True)
            except subprocess.CalledProcessError:
                subprocess.run(["git", "am", "--abort"], cwd=kernel_path, check=True)
                log_result(path, official_handle, "Failed to apply", True, "am")
                continue
            log_result(path, official_handle, "", False, "am")
            path_name = Path(path).name
            cnotice(f"Building {official_handle} for {subject}")
            try:
                result = subprocess.run(
                    ["git", "push", "--progress", "cbd", f"HEAD:refs/heads/{path_name}"],
                    cwd=kernel_path,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )
            except subprocess.CalledProcessError:
                cerror("Failed to push {subject} for {official_handle}")
                continue
            search = re.search("\\S+/BUILD-FAILED", result.stdout.decode("utf-8"))
            if search:
                log_result(path, serie, f"Failed to build {search[0]}", True, "build")
            else:
                search = re.search("\\S+/BUILD-OK", result.stdout.decode("utf-8"))
                log_result(path, serie, f"{search[0]}", False, "build")


if __name__ == "__main__":
    check_pending()
