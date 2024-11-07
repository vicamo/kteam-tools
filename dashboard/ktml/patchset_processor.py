from ktl.log import cerror, cnotice, cdebug
from patch_checks import PatchChecks, CheckError
from patch_results import PatchResults
from matching import match_handles, match_patch_count, match_patchset, ParsingPatchesError


class PatchsetProcessor:
    def __init__(self, patchset, dry_run):
        self.path = patchset["path"]
        self.subject = patchset["subject"]
        self.patchset = patchset
        self.dry_run = dry_run
        self.patch_result = PatchResults(self.path, dry_run)

    def skip_checks(self, official_handle, raw_handle):
        # Check if already built
        # Multiple checks needed to be retro-compatible
        if (
            self.patch_result.exist("build", official_handle.split(":")[0])
            or self.patch_result.exist("build", raw_handle)
            or self.patch_result.exist("build", official_handle)
        ):
            cdebug(f"Skipping {self.subject}, already built")
            return True

        if self.dry_run:
            cdebug(f"Skipping {self.subject}, dry_run")
            return True

    def log_result(self, target_serie, msg, isFail, operation):
        if isFail:
            result = "fail"
            cerror(msg)
        else:
            result = "pass"
            cnotice(msg)
        self.patch_result.update(operation, result, target_serie, msg)

    def patchset_processing(self):
        try:
            handles = match_handles(self.subject)
        except AttributeError:
            self.log_result("Unknown", f"Unable to find the handles of {self.subject}", True, "parsing")
            return
        try:
            patch_cnt = match_patch_count(self.subject)
        except AttributeError:
            self.log_result("Unknown", f"Unable to find the patch count of {self.subject}", True, "parsing")
            return
        for handle_mapping in handles:
            raw_handle = handle_mapping[0]
            official_handle = handle_mapping[1]
            if official_handle is None:
                self.log_result("Unknown", "Unable to understand handle", True, "parsing")
                continue
            cdebug(f"Processing {raw_handle}/{official_handle} for {self.subject}")
            try:
                patches = self.build_patchset(patch_cnt, raw_handle)
            except ParsingPatchesError:
                self.log_result(official_handle, f"Failed to parse patches for {official_handle}", True, "parsing")
                continue

            cdebug(f"Patchset ready for {self.subject}/{official_handle}")
            if self.skip_checks(official_handle, raw_handle):
                continue

            self.run_checks(official_handle, patches)

    def build_patchset(self, patch_cnt, raw_handle):
        return match_patchset(self.patchset["patches"], raw_handle, patch_cnt)

    def run_checks(self, official_handle, patches):
        pc = PatchChecks(official_handle, patches, self.patchset)
        try:
            pc.check_am()
            self.log_result(official_handle, "", False, "am")
        except CheckError:
            self.log_result(official_handle, "Failed to apply", True, "am")
            return

        cnotice(f"Building {official_handle} for {self.subject}")
        try:
            msg = pc.check_build()
            self.log_result(official_handle, msg, False, "build")
        except CheckError as e:
            self.log_result(official_handle, str(e), True, "build")
            return
