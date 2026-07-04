"""
Main entry point for the HA GitHub Sync addon.

Lifecycle:
  1. Load configuration from /data/options.json
  2. Initialise the local git working copy
  3. Enter the sync loop (outbound every sync_interval; inbound when
     mode=bidirectional)
"""
import logging
import os
import signal
import sys
import time
from types import FrameType

from .config import load_config
from .git_ops import GitOps
from .status import StatusTracker
from .sync_engine import SyncEngine
from .validator import Validator
from .version import APP_VERSION

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)
logger = logging.getLogger("ha_github_sync")

REPO_DIR = "/data/repo"
LOCK_FILE = "/data/.sync.lock"

_shutdown = False


# ------------------------------------------------------------------
# Signal handling
# ------------------------------------------------------------------

def _handle_signal(sig: int, _frame: FrameType | None) -> None:
    global _shutdown
    logger.info("Signal %s received – shutting down gracefully", sig)
    _shutdown = True


# ------------------------------------------------------------------
# Lock file helpers (prevent overlapping sync runs)
# ------------------------------------------------------------------

def _acquire_lock() -> bool:
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as fh:
                pid = int(fh.read().strip())
            os.kill(pid, 0)  # Check if PID is alive
            return False  # Another instance is running
        except (ValueError, ProcessLookupError, OSError):
            pass  # Stale lock – safe to overwrite

    with open(LOCK_FILE, "w") as fh:
        fh.write(str(os.getpid()))
    return True


def _release_lock() -> None:
    try:
        os.unlink(LOCK_FILE)
    except OSError:
        pass


# ------------------------------------------------------------------
# Single sync cycle
# ------------------------------------------------------------------

def _run_sync_cycle(engine: SyncEngine, mode: str) -> None:
    logger.info("=== Sync cycle start (mode=%s) ===", mode)

    if mode in ("export", "bidirectional"):
        success, commit, changed, errors = engine.run_outbound()
        if success:
            if commit:
                logger.info(
                    "Outbound complete – commit=%s files=%d", commit[:8], len(changed)
                )
            else:
                logger.info("Outbound complete – no changes")
        else:
            logger.error("Outbound failed: %s", errors)

    if mode == "bidirectional":
        success, changed, errors = engine.run_inbound()
        if success:
            if changed:
                logger.info("Inbound complete – files=%d", len(changed))
            else:
                logger.info("Inbound complete – no changes")
        else:
            logger.error("Inbound failed: %s", errors)

    logger.info("=== Sync cycle end ===")


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main() -> None:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    logger.info("HA GitHub Sync v%s starting", APP_VERSION)

    # ---- Load config -------------------------------------------------
    try:
        config = load_config()
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Configuration error: %s", exc)
        sys.exit(1)

    logger.info(
        "Config: repo=%s branch=%s mode=%s interval=%ds dry_run=%s",
        config.github_repo,
        config.branch,
        config.mode,
        config.sync_interval,
        config.dry_run,
    )

    # ---- Initialise components --------------------------------------
    status = StatusTracker()
    status.set_mode(config.mode)

    git = GitOps(
        repo_dir=REPO_DIR,
        repo_url=config.github_repo,
        token=config.github_token,
        branch=config.branch,
        author_name=config.commit_author_name,
        author_email=config.commit_author_email,
    )

    validator = Validator(
        config_dir="/config",
        allow_paths=config.include_paths,
        deny_paths=config.exclude_paths,
    )

    engine = SyncEngine(
        git=git,
        validator=validator,
        status=status,
        repo_dir=REPO_DIR,
        mode=config.mode,
        dry_run=config.dry_run,
        validate_on_sync=config.validate_on_sync,
        include_paths=config.include_paths,
        exclude_paths=config.exclude_paths,
    )

    # ---- Initialise git repo ----------------------------------------
    try:
        git.init_or_clone()
        git.checkout_branch()
        git.set_gitignore(config.exclude_paths)
    except Exception as exc:
        logger.error("Failed to initialise git working copy: %s", exc)
        sys.exit(1)

    logger.info("Ready – entering sync loop (interval=%ds)", config.sync_interval)

    # ---- Main sync loop ---------------------------------------------
    last_sync_time: float = 0.0
    while not _shutdown:
        now = time.monotonic()
        if now - last_sync_time >= config.sync_interval:
            if _acquire_lock():
                try:
                    _run_sync_cycle(engine, config.mode)
                    last_sync_time = time.monotonic()
                finally:
                    _release_lock()
            else:
                logger.warning("Sync already running (stale lock?), skipping cycle")

        # Sleep in small increments so SIGTERM is handled quickly
        for _ in range(10):
            if _shutdown:
                break
            time.sleep(0.5)

    logger.info("HA GitHub Sync stopped")
