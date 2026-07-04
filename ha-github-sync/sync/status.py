"""Persist addon health and last-sync metadata to /data/status.json."""
import json
import logging
import os
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger("ha_github_sync.status")

STATUS_FILE = "/data/status.json"
ADDON_VERSION = "0.1.0"


class StatusTracker:
    """Reads and writes the addon status file."""

    def __init__(self):
        self._data: dict = {
            "addon_version": ADDON_VERSION,
            "mode": None,
            "last_sync": None,
            "last_commit": None,
            "last_commit_message": None,
            "changed_files": [],
            "validation_result": None,
            "apply_result": None,
            "conflict_state": False,
            "errors": [],
        }
        self._load()

    def _load(self):
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self._data.update(saved)
            except Exception as exc:
                logger.warning("Could not load status file: %s", exc)

    def save(self):
        try:
            with open(STATUS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, default=str)
        except Exception as exc:
            logger.warning("Could not write status file: %s", exc)

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def set_mode(self, mode: str):
        self._data["mode"] = mode
        self.save()

    def set_error(self, error: str):
        self._data["errors"] = [error]
        self.save()

    def record_sync(
        self,
        commit: Optional[str],
        message: Optional[str],
        changed_files: List[str],
        validation_result: Optional[str],
        apply_result: Optional[str],
        conflict_state: bool,
        mode: str,
        errors: List[str],
    ):
        self._data.update(
            {
                "last_sync": datetime.now(timezone.utc).isoformat(),
                "last_commit": commit,
                "last_commit_message": message,
                "changed_files": changed_files,
                "validation_result": validation_result,
                "apply_result": apply_result,
                "conflict_state": conflict_state,
                "mode": mode,
                "errors": errors,
            }
        )
        self.save()

    @property
    def data(self) -> dict:
        return dict(self._data)
