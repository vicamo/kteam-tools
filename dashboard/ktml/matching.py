import os
import subprocess
import re
from difflib import get_close_matches


def match_patch_count(subject):
    patch_cnt_regex = r"\[.*([0-9]+\/[0-9]+)\]"
    patch_cnt = re.search(patch_cnt_regex, subject).group(1).split("/")[1]
    return patch_cnt


def match_handles(subject):
    handles_regex = r"\[((([XxBbFfJjNnOo]([a-zA-Z:\-]+)?)[/]?)+)\]"
    raw_handles = re.search(handles_regex, subject).group(1).split("/")
    handles = [(x, match_handle(x)) for x in raw_handles]
    return handles


def match_handle(raw_handle, cache="./handles.list"):
    try:
        with open(cache) as input:
            handles = input.readlines()
    except FileNotFoundError:
        with open(cache + ".new", "w") as handle_list_file:
            subprocess.run(["cranky", "shell-helper", "list-handles"], stdout=handle_list_file)
            os.rename(cache + ".new", cache)
        with open(cache) as input:
            handles = input.read().split(" ")
    handles = [s.strip("\n") for s in handles]
    original_len = len(handles)
    mapping = [[], []]
    for i in range(original_len):
        mapping[0].append(handles[i])
        mapping[1].append(handles[i])
        # Handle single letter handle
        if re.match(".*:linux$", handles[i]):
            mapping[0].append(handles[i])
            mapping[1].append(handles[i][0])
            mapping[0].append(handles[i])
            mapping[1].append(handles[i].split(":")[0])
            mapping[0].append(handles[i])
            mapping[1].append(handles[i][0] + ":" + handles[i].split(":")[1])

        # Handle derivatives without "linux" and shortening the series
        if re.match(".*:linux-.*", handles[i]):
            mapping[0].append(handles[i])
            short = handles[i].split(":")[0] + ":" + handles[i].split("-", 1)[1]
            mapping[1].append(short)
            mapping[0].append(handles[i])
            shorter = handles[i][0] + ":" + handles[i].split(":")[1]
            mapping[1].append(shorter)
            mapping[0].append(handles[i])
            shortest = handles[i][0] + ":" + handles[i].split("-", 1)[1]
            mapping[1].append(shortest)

    closest = get_close_matches(raw_handle.lower(), mapping[1], cutoff=0.9)
    if closest:
        return mapping[0][mapping[1].index(closest[0])]
    else:
        return None


def match_patch(patch, raw_handle, index, patch_count):
    return match_patch_subject(patch.get(":subject"), raw_handle, index, patch_count)


def match_patch_subject(subject, raw_handle, index, patch_count):
    patch_cnt_regex = f".*{index}/{patch_count}\\].*"
    escaped_raw_handle = raw_handle.replace("-", "\\-").replace(":", "\\:")
    handle_regex = f".*[\\[/]{escaped_raw_handle}[/\\]].*"

    if re.match(patch_cnt_regex, subject) and re.match(handle_regex, subject):
        return True
    return False
