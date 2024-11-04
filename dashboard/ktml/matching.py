import subprocess
import re
from difflib import get_close_matches


def match_handle(raw_handle):
    try:
        with open("./handles.list") as input:
            handles = input.readlines()
    except FileNotFoundError:
        with open("./handles.list", "w") as handle_list_file:
            subprocess.run(["cranky", "shell-helper", "list-handles"], stdout=handle_list_file)
        with open("./handles.list") as input:
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

        # Handle derivatives without "linux" and shortening the series
        if re.match(".*:linux-.*", handles[i]):
            mapping[0].append(handles[i])
            short = handles[i].split(":")[0] + ":" + handles[i].split("-")[1]
            mapping[1].append(short)
            mapping[0].append(handles[i])
            shorter = handles[i][0] + ":" + handles[i].split("-")[1]
            mapping[1].append(shorter)
    closest = get_close_matches(raw_handle.lower(), mapping[1])
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
