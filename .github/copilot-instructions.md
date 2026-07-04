# GitHub Copilot Instructions for HA GitHub Sync

This repository is the addon that powers **HA GitHub Sync** – a Home
Assistant add-on that syncs HA configuration files to GitHub and enables
agentic editing via Copilot.

## Repository layout

```
ha-github-sync/          ← The Home Assistant add-on
  config.yaml            ← Addon metadata and option schema
  build.yaml             ← Multi-arch base image configuration
  Dockerfile             ← Container definition (Alpine + Python)
  run.sh                 ← Container entrypoint
  DOCS.md                ← User-facing documentation
  sync/                  ← Python package (ha_github_sync)
    __init__.py
    __main__.py          ← Entry: python3 -m ha_github_sync
    main.py              ← Sync loop and signal handling
    config.py            ← Options loading (/data/options.json)
    git_ops.py           ← All git subprocess calls
    sync_engine.py       ← Outbound and inbound sync flows
    validator.py         ← YAML syntax, secret scanning, path filtering
    status.py            ← /data/status.json writer

ha-config-template/      ← Template for synced HA config repositories
  .gitignore             ← Default ignores for HA config repos
  manifest.yaml          ← Tracked/excluded path contract
  README.md              ← Workflow guide for config repo users
```

## Coding conventions

- **Python 3.11** – match the base image.
- Type-annotate all public functions and methods.
- All git operations live in `git_ops.py` – do not shell out to git
  anywhere else.
- Log with `logging.getLogger("ha_github_sync.<module>")`.
- Never log the GitHub token; `git_ops.py` scrubs it from all error messages.
- Raise `GitError` (defined in `git_ops.py`) for all git failures.
- The `SyncEngine` methods return `(success: bool, ..., errors: List[str])`
  – never raise from them.
- Keep `main.py` as thin orchestration only; business logic lives in
  `sync_engine.py` and `validator.py`.

## Security rules (never violate)

1. **Never write the GitHub token to any tracked file** – it must only
   exist in the authenticated URL at runtime.
2. **Never commit `secrets.yaml`** or any file matching the hard-coded
   deny list in `validator.py::ALWAYS_DENY`.
3. **Never auto-merge** a PR that modifies `configuration.yaml` or files
   outside the `include_paths` list without human review.
4. **Always validate** (YAML syntax + secret scan) before committing
   outbound changes or applying inbound changes.
5. **Always roll back** inbound changes if validation fails.

## Addon option schema

Changes to addon options must be reflected in **all three** of:
- `ha-github-sync/config.yaml` (schema + defaults)
- `ha-github-sync/sync/config.py` (`SyncConfig` dataclass + loader)
- `ha-github-sync/DOCS.md` (configuration table)

## Path filtering logic

`Validator.is_path_allowed(rel_path)` is the single source of truth for
path decisions.  The precedence is:

1. Hard-coded `ALWAYS_DENY` list in `validator.py` (highest priority).
2. User-configured `exclude_paths` (merged with ALWAYS_DENY).
3. User-configured `include_paths` (allow list; empty = allow all non-denied).

When changing filtering logic, update `Validator._matches_any` and add a
test case in `.github/workflows/validate-addon.yml`.

## Sync flow summary

```
Outbound (HA → GitHub)
  collect_tracked_files()  →  sync_files_to_repo()  →  validate  →  commit  →  push

Inbound (GitHub → HA)  [bidirectional mode only]
  fetch  →  divergence_check  →  backup_branch  →  fast_forward_merge
  →  validate  →  apply_files_to_ha   (rolls back if validation fails)
```

## Pull request guidelines for Copilot-generated changes

When Copilot opens a PR against this repository:

1. Clearly state which module(s) are affected.
2. Include a "Security considerations" section.
3. Never change `ALWAYS_DENY` to be less restrictive without explicit
   human approval.
4. Never weaken the rollback logic in `SyncEngine.run_inbound`.
5. Include the relevant test command in the PR description:
   ```
   python -m pytest ha-github-sync/
   ```
