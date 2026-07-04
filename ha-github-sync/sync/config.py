"""Load and validate addon configuration from /data/options.json."""
import json
import os
from dataclasses import dataclass, field
from typing import List


OPTIONS_FILE = "/data/options.json"

DEFAULT_INCLUDE_PATHS = [
    "automations.yaml",
    "scripts.yaml",
    "scenes.yaml",
    "groups.yaml",
    "input_boolean.yaml",
    "input_number.yaml",
    "input_select.yaml",
    "input_text.yaml",
    "input_datetime.yaml",
    "packages",
    "blueprints",
    "custom_components",
    "lovelace",
    "dashboards",
]

DEFAULT_EXCLUDE_PATHS = [
    "secrets.yaml",
    ".storage",
    "*.log",
    "*.db",
    "*.db-shm",
    "*.db-wal",
    "home-assistant_v2.db",
    ".cloud",
    ".HA_VERSION",
    "deps",
    "tts",
    "known_devices.yaml",
]


@dataclass
class SyncConfig:
    github_repo: str
    github_token: str
    branch: str = "main"
    commit_author_name: str = "HA GitHub Sync"
    commit_author_email: str = "ha-sync@localhost"
    sync_interval: int = 3600
    mode: str = "export"
    dry_run: bool = False
    validate_on_sync: bool = True
    include_paths: List[str] = field(default_factory=lambda: list(DEFAULT_INCLUDE_PATHS))
    exclude_paths: List[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDE_PATHS))


def load_config() -> SyncConfig:
    """Load SyncConfig from the addon options file."""
    if not os.path.exists(OPTIONS_FILE):
        raise FileNotFoundError(
            f"Options file not found: {OPTIONS_FILE}. "
            "Ensure the addon is started through Home Assistant."
        )

    with open(OPTIONS_FILE, "r", encoding="utf-8") as f:
        opts = json.load(f)

    github_repo = opts.get("github_repo", "").strip()
    github_token = opts.get("github_token", "").strip()

    if not github_repo:
        raise ValueError(
            "github_repo is required. "
            "Set it in the addon configuration to a GitHub repository URL."
        )
    if not github_token:
        raise ValueError(
            "github_token is required. "
            "Create a GitHub Personal Access Token with repo scope "
            "and set it in the addon configuration."
        )

    mode = opts.get("mode", "export")
    if mode not in ("export", "bidirectional"):
        raise ValueError(f"Invalid mode '{mode}'. Must be 'export' or 'bidirectional'.")

    return SyncConfig(
        github_repo=github_repo,
        github_token=github_token,
        branch=opts.get("branch", "main") or "main",
        commit_author_name=(
            opts.get("commit_author_name", "HA GitHub Sync") or "HA GitHub Sync"
        ),
        commit_author_email=(
            opts.get("commit_author_email", "ha-sync@localhost") or "ha-sync@localhost"
        ),
        sync_interval=int(opts.get("sync_interval", 3600)),
        mode=mode,
        dry_run=bool(opts.get("dry_run", False)),
        validate_on_sync=bool(opts.get("validate_on_sync", True)),
        include_paths=opts.get("include_paths", DEFAULT_INCLUDE_PATHS) or DEFAULT_INCLUDE_PATHS,
        exclude_paths=opts.get("exclude_paths", DEFAULT_EXCLUDE_PATHS) or DEFAULT_EXCLUDE_PATHS,
    )
