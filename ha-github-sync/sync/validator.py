"""
Validation helpers:
  - path allow/deny filtering
  - YAML syntax checking
  - basic secret scanning
  - optional Home Assistant config check
"""
import fnmatch
import logging
import os
import re
import subprocess
from typing import List, Tuple

logger = logging.getLogger("ha_github_sync.validator")

try:
    import yaml as _yaml

    HAS_YAML = True

    class _HaSafeLoader(_yaml.SafeLoader):
        """SafeLoader variant that accepts Home Assistant custom tags."""

    def _construct_ha_tag(
        loader: _HaSafeLoader, _tag_suffix: str, node: _yaml.Node
    ) -> object:
        if isinstance(node, _yaml.ScalarNode):
            return loader.construct_scalar(node)
        if isinstance(node, _yaml.SequenceNode):
            return loader.construct_sequence(node)
        if isinstance(node, _yaml.MappingNode):
            return loader.construct_mapping(node)
        return None

    _HaSafeLoader.add_multi_constructor("!", _construct_ha_tag)  # type: ignore[no-untyped-call]
except ImportError:
    HAS_YAML = False
    logger.warning("PyYAML not available – YAML syntax validation disabled")

# -------------------------------------------------------------------
# Paths that are ALWAYS excluded regardless of user configuration.
# These protect secrets, runtime state, and privacy-sensitive files.
# -------------------------------------------------------------------
ALWAYS_DENY = [
    "secrets.yaml",
    "secrets.yml",
    ".storage",
    ".storage/**",
    "*.log",
    "*.db",
    "*.db-shm",
    "*.db-wal",
    "home-assistant_v2.db",
    ".cloud",
    ".cloud/**",
    "deps",
    "deps/**",
    "tts",
    "tts/**",
    ".HA_VERSION",
    "known_devices.yaml",  # contains MAC addresses – privacy-sensitive
]

# Patterns that suggest an unredacted secret value in a YAML file.
# The negative lookahead `(?!.*!secret)` allows the HA `!secret` tag.
_SECRET_RE = re.compile(
    r"(?ix)"
    r"(?:password|token|api_key|secret|private_key)\s*:\s*[\"']?(?!.*!secret)[\w\-\.@#$%^&*]{8,}"
    r"|ghp_[A-Za-z0-9]{36}"
    r"|github_pat_[A-Za-z0-9_]{36}"
    r"|glpat-[A-Za-z0-9\-_]{20}"
)


class Validator:
    def __init__(
        self,
        config_dir: str,
        allow_paths: List[str],
        deny_paths: List[str],
    ):
        self.config_dir = config_dir
        self.allow_paths = allow_paths
        # Merge user-supplied deny list with the hard-coded always-deny list
        seen: set[str] = set()
        merged = []
        for p in list(deny_paths) + list(ALWAYS_DENY):
            if p not in seen:
                seen.add(p)
                merged.append(p)
        self.deny_paths = merged

    # ------------------------------------------------------------------
    # Path filtering
    # ------------------------------------------------------------------

    def is_path_allowed(self, rel_path: str) -> bool:
        """Return True when *rel_path* is permitted under current rules."""
        # Deny wins over allow
        if self._matches_any(rel_path, self.deny_paths):
            return False

        # If no allow-list is configured, everything (not denied) is allowed
        if not self.allow_paths:
            return True

        return self._matches_any(rel_path, self.allow_paths)

    @staticmethod
    def _matches_any(rel_path: str, patterns: List[str]) -> bool:
        for pattern in patterns:
            norm = pattern.rstrip("/")
            # Exact or glob match on the full relative path
            if fnmatch.fnmatch(rel_path, norm):
                return True
            # Recursive directory match  (e.g. "packages" matches "packages/lights.yaml")
            if fnmatch.fnmatch(rel_path, norm + "/**"):
                return True
            if rel_path.startswith(norm + "/"):
                return True
            # Match basename only for wildcard patterns like "*.log"
            if "*" in norm and fnmatch.fnmatch(os.path.basename(rel_path), norm):
                return True
        return False

    # ------------------------------------------------------------------
    # YAML syntax
    # ------------------------------------------------------------------

    def check_yaml_syntax(self, file_path: str) -> Tuple[bool, str]:
        """Return (is_valid, message)."""
        if not HAS_YAML:
            return True, "skipped (PyYAML not available)"
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                _yaml.load(fh.read(), Loader=_HaSafeLoader)
            return True, "ok"
        except _yaml.YAMLError as exc:
            return False, str(exc)
        except OSError as exc:
            return False, f"read error: {exc}"

    # ------------------------------------------------------------------
    # Secret scanning
    # ------------------------------------------------------------------

    def scan_for_secrets(self, file_path: str) -> List[str]:
        """Return a list of warning strings for any suspected secrets found."""
        warnings: List[str] = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
                for lineno, line in enumerate(fh, 1):
                    if _SECRET_RE.search(line):
                        warnings.append(
                            f"Possible unredacted secret at "
                            f"{os.path.basename(file_path)}:{lineno} – "
                            "use !secret or move to secrets.yaml"
                        )
        except OSError as exc:
            warnings.append(f"Could not scan {file_path}: {exc}")
        return warnings

    # ------------------------------------------------------------------
    # Whole-repo validation
    # ------------------------------------------------------------------

    def validate_repo_files(
        self, repo_dir: str
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Walk *repo_dir* and validate every tracked YAML file.

        Returns (is_valid, errors, warnings).
        """
        errors: List[str] = []
        warnings: List[str] = []

        for root, dirs, files in os.walk(repo_dir):
            dirs[:] = [d for d in dirs if d != ".git"]

            for fname in files:
                fpath = os.path.join(root, fname)
                rel = os.path.relpath(fpath, repo_dir)

                if fname.endswith((".yaml", ".yml")):
                    ok, msg = self.check_yaml_syntax(fpath)
                    if not ok:
                        errors.append(f"YAML syntax error in {rel}: {msg}")

                    warnings.extend(self.scan_for_secrets(fpath))

        return len(errors) == 0, errors, warnings

    # ------------------------------------------------------------------
    # Optional HA config check
    # ------------------------------------------------------------------

    def try_ha_config_check(self, config_dir: str) -> Tuple[bool, str]:
        """
        Attempt to run the Home Assistant config check script.

        Returns (is_valid, output).  Falls back gracefully if the HA
        runtime is not present in the container.
        """
        candidates = [
            ["hass", "--script", "check_config", "--config", config_dir],
            ["python3", "-m", "homeassistant", "--script", "check_config",
             "--config", config_dir],
        ]
        for cmd in candidates:
            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=60
                )
                if result.returncode == 0:
                    return True, result.stdout
                return False, (result.stderr or result.stdout).strip()
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue

        return True, "HA config check binary not available – skipping"
