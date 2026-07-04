# HA GitHub Sync

Sync and backup your Home Assistant configuration to a GitHub repository,
enabling agentic editing with GitHub Copilot.

## Overview

HA GitHub Sync is a Home Assistant Add-on that:

- **Exports** selected config files from your HA instance to a GitHub repository on a configurable schedule.
- **Optionally imports** changes merged into GitHub back into your running HA config *(bidirectional mode)*.
- Acts as the bridge between your live Home Assistant environment and a GitHub repository that GitHub Copilot can read, edit, and submit pull requests against.

## Prerequisites

- Home Assistant OS or Supervised installation
- A GitHub account with a repository created for your HA config
- A [GitHub Personal Access Token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token) with the `repo` scope

## Installation

1. In Home Assistant, navigate to **Settings → Add-ons → Add-on Store**.
2. Click the **⋮ menu → Repositories** and add:
   ```
   https://github.com/MrEllisTechnologyTeacher/HA_Github_Sync
   ```
3. Find **HA GitHub Sync** in the store and click **Install**.

## Versioning

Addon versioning is automated on `main`. Every push that changes addon files
triggers a patch bump and creates a matching git tag (for example `v0.1.1`).

## Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `github_repo` | *(required)* | Full HTTPS URL of your GitHub config repository, e.g. `https://github.com/you/ha-config` |
| `github_token` | *(required)* | GitHub Personal Access Token with `repo` scope |
| `branch` | `main` | Branch to commit to and pull from |
| `commit_author_name` | `HA GitHub Sync` | Git commit author name |
| `commit_author_email` | `ha-sync@localhost` | Git commit author email |
| `sync_interval` | `3600` | Seconds between automatic sync cycles (60–86400) |
| `mode` | `export` | `export` – push HA → GitHub only. `bidirectional` – also apply GitHub → HA |
| `dry_run` | `false` | Log what would happen without writing or pushing |
| `validate_on_sync` | `true` | Validate YAML syntax and scan for secrets before committing or applying |
| `include_paths` | *see below* | List of file/directory paths (relative to `/config`) to track |
| `exclude_paths` | *see below* | List of file/directory paths or glob patterns to never sync |

### Default include_paths

```yaml
include_paths:
  - automations.yaml
  - scripts.yaml
  - scenes.yaml
  - groups.yaml
  - customize.yaml
  - input_boolean.yaml
  - input_number.yaml
  - input_select.yaml
  - input_text.yaml
  - input_datetime.yaml
  - packages
  - blueprints
  - custom_components
  - lovelace
  - dashboards
```

### Default exclude_paths (always enforced)

The following paths are **always excluded** regardless of configuration to
protect secrets and runtime state:

- `secrets.yaml`
- `.storage/`
- `*.log`, `*.db`, `*.db-shm`, `*.db-wal`
- `home-assistant_v2.db`
- `.cloud/`, `deps/`, `tts/`
- `.HA_VERSION`
- `known_devices.yaml`

## Modes

### Export (default, recommended for first-time use)

Changes in your HA config are committed and pushed to GitHub automatically.
Nothing is ever written back to HA without your explicit action.

### Bidirectional

In addition to exporting, the addon fetches any changes merged into the
configured branch and applies them to HA config files.

> **Safety note:** Before enabling bidirectional mode, review the
> [Copilot workflow guide](.github/copilot-instructions.md) and ensure
> `validate_on_sync: true` is set.

## Status file

The addon writes `/data/status.json` after each sync cycle with:

```json
{
  "last_sync": "2024-01-01T12:00:00+00:00",
  "last_commit": "abc12345",
  "last_commit_message": "chore: sync HA config [automations.yaml]",
  "changed_files": ["automations.yaml"],
  "validation_result": "pass",
  "apply_result": null,
  "conflict_state": false,
  "mode": "export",
  "errors": []
}
```

## Conflict handling

If both local HA config and the remote GitHub branch have advanced since
the last sync, the addon **stops** and logs:

```
Conflict: local and remote have diverged. Manual resolution required.
```

To recover:

1. Open the addon log for details on which files diverged.
2. Manually reconcile the repository branch with the expected state.
3. Restart the addon.

## Security notes

- Your GitHub token is stored in the addon's encrypted options storage and
  is **never written to any tracked file**.
- The token is injected into the HTTPS clone URL at runtime and scrubbed
  from any log output.
- Secret scanning warns you if a YAML file appears to contain an unredacted
  credential (you should use HA's `!secret` tag instead).
