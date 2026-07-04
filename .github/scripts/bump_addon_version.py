#!/usr/bin/env python3
"""Bump HA GitHub Sync patch version and update all version surfaces."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "ha-github-sync" / "config.yaml"
VERSION_MODULE_PATH = ROOT / "ha-github-sync" / "sync" / "version.py"
CHANGELOG_PATH = ROOT / "ha-github-sync" / "CHANGELOG.md"

CONFIG_RE = re.compile(r'^(version:\s*")(\d+)\.(\d+)\.(\d+)(")\s*$', re.MULTILINE)
MODULE_RE = re.compile(
    r'^(APP_VERSION\s*=\s*")(\d+)\.(\d+)\.(\d+)(")\s*$',
    re.MULTILINE,
)


def bump_patch(version: tuple[int, int, int]) -> tuple[int, int, int]:
    major, minor, patch = version
    return major, minor, patch + 1


def write_config_version(new_version: str) -> None:
    content = CONFIG_PATH.read_text(encoding="utf-8")
    if not CONFIG_RE.search(content):
        raise RuntimeError("Could not find version in ha-github-sync/config.yaml")
    updated = CONFIG_RE.sub(rf'\g<1>{new_version}\g<5>', content, count=1)
    CONFIG_PATH.write_text(updated, encoding="utf-8")


def write_module_version(new_version: str) -> None:
    content = VERSION_MODULE_PATH.read_text(encoding="utf-8")
    if not MODULE_RE.search(content):
        raise RuntimeError("Could not find APP_VERSION in ha-github-sync/sync/version.py")
    updated = MODULE_RE.sub(rf'\g<1>{new_version}\g<5>', content, count=1)
    VERSION_MODULE_PATH.write_text(updated, encoding="utf-8")


def prepend_changelog_unreleased(old_version: str, new_version: str) -> None:
    content = CHANGELOG_PATH.read_text(encoding="utf-8")
    marker = f"## [{old_version}]"
    if marker not in content:
        return

    unreleased = (
        f"## [{new_version}] - unreleased\n\n"
        "### Changed\n"
        "- Automated version bump.\n\n"
    )
    if f"## [{new_version}] - unreleased" in content:
        return
    updated = content.replace(marker, unreleased + marker, 1)
    CHANGELOG_PATH.write_text(updated, encoding="utf-8")


def main() -> None:
    config_content = CONFIG_PATH.read_text(encoding="utf-8")
    match = CONFIG_RE.search(config_content)
    if not match:
        raise RuntimeError("Could not parse current version in config.yaml")

    current = (int(match.group(2)), int(match.group(3)), int(match.group(4)))
    bumped = bump_patch(current)
    old_version = ".".join(str(p) for p in current)
    new_version = ".".join(str(p) for p in bumped)

    write_config_version(new_version)
    write_module_version(new_version)
    prepend_changelog_unreleased(old_version, new_version)
    print(new_version)


if __name__ == "__main__":
    main()

