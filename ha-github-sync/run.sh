#!/bin/bash
set -e

echo "[INFO] HA GitHub Sync starting up"

# Add the package root to PYTHONPATH so the ha_github_sync package is importable
export PYTHONPATH=/opt/ha-github-sync

exec python3 -m ha_github_sync
