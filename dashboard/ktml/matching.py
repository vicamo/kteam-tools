import re
from difflib import get_close_matches
import functools
from ktl.kernel_series import KernelSeries


class ParsingPatchesError(Exception):
    pass


class MatchHandles:
    handle_cache = None

    @classmethod
    @property
    def handles(cls):
        if cls.handle_cache is None:
            handles = []
            ks = KernelSeries()
            for series in ks.series:
                if not series.supported:
                    continue
                for source in series.sources:
                    if not source.supported or source.copy_forward is not None:
                        continue
                    handles.append(series.codename + ":" + source.name)
            cls.handle_cache = handles
        return cls.handle_cache


def match_patch_count(subject):
    patch_cnt_regex = r"\[[^\]]*PATCH[^\]]*([0-9]+\/[0-9]+)\]"
    patch_cnt = re.search(patch_cnt_regex, subject).group(1).split("/")[1]
    return patch_cnt


def match_handles(subject):
    handles_regex = r"\[((([XxBbFfJjNnOo]([a-zA-Z:\-]+)?)[/]?)+)\]"
    raw_handles = re.search(handles_regex, subject).group(1).split("/")
    handles = [(x, match_handle(x)) for x in raw_handles]
    return handles


def match_handle(raw_handle):
    handles = MatchHandles.handles
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


def match_patch(patch, raw_handle, index):
    return match_patch_subject(patch.get(":subject"), raw_handle, index)


def match_patch_subject(subject, raw_handle, index):
    patch_cnt_regex = f"\\[.*{index}/[0-9]+\\].*"

    escaped_raw_handle = raw_handle.replace("-", "\\-").replace(":", "\\:")
    handle_regex = f".*[\\[/]{escaped_raw_handle}[/\\]].*"

    if re.match(patch_cnt_regex, subject) and re.match(handle_regex, subject):
        return True
    return False


def match_patchset(related_patches, raw_handle):
    patches = []
    i = 1
    finished = False
    while not finished:
        patch = None
        patch_subject = filter(
            functools.partial(match_patch, raw_handle=raw_handle, index=i),
            related_patches,
        )
        for patch in patch_subject:
            patches.append(patch)
            if int(match_patch_count(patch[":subject"])) == i:
                finished = True
        if patch is None:
            raise ParsingPatchesError
        i += 1
    return patches
