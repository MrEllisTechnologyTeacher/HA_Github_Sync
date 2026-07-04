"""
Core sync engine: copies files between the HA config directory and the
local git working copy, drives outbound (HA → GitHub) and inbound
(GitHub → HA) sync flows.
"""
import json
import logging
import os
import shutil
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from .git_ops import GitError, GitOps
from .status import StatusTracker
from .validator import Validator

logger = logging.getLogger("ha_github_sync.engine")

# The HA config directory is bind-mounted here by the supervisor
HA_CONFIG_DIR = "/homeassistant"
# Internal manifest file tracked inside the repo
MANIFEST_FILE = ".ha-sync-manifest.json"


class SyncEngine:
    def __init__(
        self,
        git: GitOps,
        validator: Validator,
        status: StatusTracker,
        repo_dir: str,
        mode: str,
        dry_run: bool,
        validate_on_sync: bool,
        include_paths: List[str],
        exclude_paths: List[str],
    ):
        self.git = git
        self.validator = validator
        self.status = status
        self.repo_dir = repo_dir
        self.mode = mode
        self.dry_run = dry_run
        self.validate_on_sync = validate_on_sync
        self.include_paths = include_paths
        self.exclude_paths = exclude_paths

    # ------------------------------------------------------------------
    # File collection helpers
    # ------------------------------------------------------------------

    def _collect_tracked_files(self) -> List[Tuple[str, str]]:
        """
        Walk the HA config directory and return all (abs_src, rel_path)
        tuples that pass the include/exclude filter.
        """
        tracked: List[Tuple[str, str]] = []
        for entry in self.include_paths:
            src = os.path.join(HA_CONFIG_DIR, entry)
            if os.path.isfile(src):
                if self.validator.is_path_allowed(entry):
                    tracked.append((src, entry))
            elif os.path.isdir(src):
                for root, dirs, files in os.walk(src):
                    dirs[:] = [d for d in dirs if not d.startswith(".")]
                    for fname in files:
                        full = os.path.join(root, fname)
                        rel = os.path.relpath(full, HA_CONFIG_DIR)
                        if self.validator.is_path_allowed(rel):
                            tracked.append((full, rel))
        return tracked

    def _sync_files_to_repo(
        self, tracked: List[Tuple[str, str]]
    ) -> List[str]:
        """
        Copy each tracked file from the HA config into the repo working
        copy.  Returns a list of relative paths that actually changed.
        """
        changed: List[str] = []
        for abs_src, rel_path in tracked:
            dest = os.path.join(self.repo_dir, rel_path)
            os.makedirs(os.path.dirname(dest), exist_ok=True)

            if os.path.exists(dest):
                with open(abs_src, "rb") as f1, open(dest, "rb") as f2:
                    if f1.read() == f2.read():
                        continue

            shutil.copy2(abs_src, dest)
            changed.append(rel_path)
        return changed

    def _write_manifest(self):
        """Write the sync manifest into the repo root."""
        manifest = {
            "managed_by": "ha-github-sync",
            "version": "0.1.0",
            "tracked_paths": self.include_paths,
            "excluded_paths": self.exclude_paths,
            "last_generated": datetime.now(timezone.utc).isoformat(),
        }
        path = os.path.join(self.repo_dir, MANIFEST_FILE)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2)

    def _apply_files_to_ha(self, changed_files: List[str]) -> List[str]:
        """
        Copy the listed repo files back into the HA config directory.
        Skips files that are excluded by the current rules.
        Returns a list of paths that were actually written.
        """
        applied: List[str] = []
        for rel_path in changed_files:
            if not self.validator.is_path_allowed(rel_path):
                logger.warning("Skipping inbound path (not allowed): %s", rel_path)
                continue

            src = os.path.join(self.repo_dir, rel_path)
            if not os.path.exists(src):
                logger.warning("Inbound file missing from repo: %s", rel_path)
                continue

            dest = os.path.join(HA_CONFIG_DIR, rel_path)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(src, dest)
            applied.append(rel_path)
            logger.info("Applied inbound: %s", rel_path)
        return applied

    # ------------------------------------------------------------------
    # Build a structured commit message
    # ------------------------------------------------------------------

    @staticmethod
    def _build_commit_message(changed: List[str]) -> str:
        summary_files = changed[:5]
        suffix = (
            f" … and {len(changed) - 5} more" if len(changed) > 5 else ""
        )
        subjects = ", ".join(summary_files) + suffix
        ts = datetime.now(timezone.utc).isoformat()
        return (
            f"chore: sync HA config [{subjects}]\n\n"
            f"Files changed: {len(changed)}\n"
            f"Sync time: {ts}\n"
        )

    # ------------------------------------------------------------------
    # Outbound sync  (HA config → GitHub)
    # ------------------------------------------------------------------

    def run_outbound(self) -> Tuple[bool, Optional[str], List[str], List[str]]:
        """
        Copy changed HA config files into the repo, commit, and push.

        Returns (success, commit_hash_or_None, changed_files, errors).
        """
        errors: List[str] = []
        try:
            tracked = self._collect_tracked_files()
            if not tracked:
                logger.warning(
                    "No files matched include_paths – verify addon configuration"
                )

            changed = self._sync_files_to_repo(tracked)
            self._write_manifest()

            pending = self.git.get_status()
            if not pending:
                logger.info("No changes detected, nothing to commit")
                return True, None, [], []

            # Validate before committing
            validation_result = "skipped"
            if self.validate_on_sync:
                ok, val_errors, val_warnings = self.validator.validate_repo_files(
                    self.repo_dir
                )
                for w in val_warnings:
                    logger.warning("Validation warning: %s", w)
                if not ok:
                    for e in val_errors:
                        logger.error("Validation error: %s", e)
                    errors.extend(val_errors)
                    validation_result = "fail"
                    self.status.record_sync(
                        commit=None,
                        message=None,
                        changed_files=changed,
                        validation_result=validation_result,
                        apply_result=None,
                        conflict_state=False,
                        mode=self.mode,
                        errors=errors,
                    )
                    return False, None, changed, errors
                validation_result = "pass"

            commit_msg = self._build_commit_message(changed)

            if self.dry_run:
                logger.info(
                    "Dry run – would commit %d file(s): %s", len(changed), changed
                )
                self.status.record_sync(
                    commit=None,
                    message="[dry-run] " + commit_msg.splitlines()[0],
                    changed_files=changed,
                    validation_result=validation_result,
                    apply_result=None,
                    conflict_state=False,
                    mode=self.mode,
                    errors=[],
                )
                return True, None, changed, []

            self.git.stage_all()
            commit_hash = self.git.commit(commit_msg)
            logger.info(
                "Committed %d file(s) as %s", len(changed), commit_hash[:8]
            )

            self.git.push()
            self.status.record_sync(
                commit=commit_hash,
                message=commit_msg.splitlines()[0],
                changed_files=changed,
                validation_result=validation_result,
                apply_result=None,
                conflict_state=False,
                mode=self.mode,
                errors=[],
            )
            return True, commit_hash, changed, []

        except GitError as exc:
            errors.append(f"Git error: {exc}")
            logger.error("Outbound git error: %s", exc)
            self.status.set_error(str(exc))
            return False, None, [], errors
        except Exception as exc:
            errors.append(f"Unexpected error: {exc}")
            logger.exception("Unexpected outbound error")
            self.status.set_error(str(exc))
            return False, None, [], errors

    # ------------------------------------------------------------------
    # Inbound sync  (GitHub → HA config)
    # ------------------------------------------------------------------

    def run_inbound(self) -> Tuple[bool, List[str], List[str]]:
        """
        Fetch remote changes, validate them, then apply to HA config.

        Returns (success, changed_files, errors).
        """
        errors: List[str] = []
        try:
            self.git.fetch()

            if self.git.is_diverged():
                logger.error(
                    "Conflict: local and remote have diverged. "
                    "Manual resolution required – inbound sync halted."
                )
                self.status.record_sync(
                    commit=None,
                    message=None,
                    changed_files=[],
                    validation_result=None,
                    apply_result="conflict",
                    conflict_state=True,
                    mode=self.mode,
                    errors=["Branches have diverged – manual resolution required"],
                )
                return False, [], ["branches diverged – manual resolution required"]

            ahead = self.git.get_remote_commits_ahead()
            if ahead == 0:
                logger.info("No remote changes to apply")
                return True, [], []

            logger.info("Remote has %d new commit(s) to apply", ahead)

            # Save rollback point
            pre_merge_commit = self.git.current_commit()
            if pre_merge_commit:
                self.git.backup_branch("backup/pre-inbound")

            self.git.fast_forward_merge()

            changed_files = (
                self.git.get_changed_files_since(pre_merge_commit)
                if pre_merge_commit
                else []
            )

            # Validate inbound changes
            if self.validate_on_sync:
                ok, val_errors, val_warnings = self.validator.validate_repo_files(
                    self.repo_dir
                )
                for w in val_warnings:
                    logger.warning("Inbound validation warning: %s", w)
                if not ok:
                    logger.error(
                        "Inbound validation failed – rolling back to %s",
                        pre_merge_commit,
                    )
                    if pre_merge_commit:
                        self.git.reset_to(pre_merge_commit)
                    errors.extend(val_errors)
                    self.status.record_sync(
                        commit=None,
                        message=None,
                        changed_files=changed_files,
                        validation_result="fail",
                        apply_result="rolled_back",
                        conflict_state=False,
                        mode=self.mode,
                        errors=errors,
                    )
                    return False, changed_files, errors

            # Apply to HA config
            if self.dry_run:
                logger.info(
                    "Dry run – would apply %d file(s): %s",
                    len(changed_files),
                    changed_files,
                )
                apply_result = "dry_run"
            else:
                applied = self._apply_files_to_ha(changed_files)
                logger.info("Applied %d inbound file(s) to HA config", len(applied))
                apply_result = "success"

            new_commit = self.git.current_commit()
            self.status.record_sync(
                commit=new_commit,
                message=f"Applied {len(changed_files)} inbound file(s)",
                changed_files=changed_files,
                validation_result="pass" if self.validate_on_sync else "skipped",
                apply_result=apply_result,
                conflict_state=False,
                mode=self.mode,
                errors=[],
            )
            return True, changed_files, []

        except GitError as exc:
            errors.append(f"Git error: {exc}")
            logger.error("Inbound git error: %s", exc)
            self.status.set_error(str(exc))
            return False, [], errors
        except Exception as exc:
            errors.append(f"Unexpected error: {exc}")
            logger.exception("Unexpected inbound error")
            self.status.set_error(str(exc))
            return False, [], errors
