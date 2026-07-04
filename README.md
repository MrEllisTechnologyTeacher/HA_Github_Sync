# HA GitHub Sync

[![Validate Add-on](https://github.com/MrEllisTechnologyTeacher/HA_Github_Sync/actions/workflows/validate-addon.yml/badge.svg)](https://github.com/MrEllisTechnologyTeacher/HA_Github_Sync/actions/workflows/validate-addon.yml)

A Home Assistant Add-on that syncs and backs up your Home Assistant
configuration to a GitHub repository, enabling agentic editing with
**GitHub Copilot**.

## What it does

| Feature | Description |
|---------|-------------|
| **Export** | Commits selected HA config files to GitHub on a configurable schedule |
| **Bidirectional sync** | Optionally applies Copilot-edited changes from GitHub back into HA |
| **Validation** | YAML syntax checking and secret scanning before every commit/apply |
| **Safety** | Auto-rollback on validation failure; divergence detection; process lock |
| **Copilot-ready** | Structured commits, branch workflow guide, and Copilot instructions |

## Repository layout

```
ha-github-sync/        ← The Home Assistant Add-on (install from here)
  config.yaml          ← Addon metadata and option schema
  build.yaml           ← Multi-arch image references
  Dockerfile           ← Container definition
  run.sh               ← Entrypoint
  DOCS.md              ← Setup and configuration guide
  sync/                ← Python sync package (ha_github_sync)

ha-config-template/    ← Copy this to your HA config repository
  .gitignore           ← Default ignores for HA config repos
  manifest.yaml        ← Tracked/excluded path contract
  README.md            ← Copilot workflow guide for your config repo

.github/
  copilot-instructions.md  ← Copilot coding conventions for this repo
  workflows/
    validate-addon.yml     ← CI: lint, type-check, YAML validation
```

## Quick start

1. **Add the repository** to your Home Assistant add-on store:
   ```
   https://github.com/MrEllisTechnologyTeacher/HA_Github_Sync
   ```

2. **Install and configure** the *HA GitHub Sync* add-on.  
   See [`ha-github-sync/DOCS.md`](ha-github-sync/DOCS.md) for all options.

3. **Set up your config repository** by copying the files from
   [`ha-config-template/`](ha-config-template/) into your GitHub config repo.

4. **Enable Copilot** on your config repository and open pull requests to
   make agentic changes to your automations, scripts, dashboards, and more.

## Recommended workflow

```
[Home Assistant] ──(export on schedule)──► [GitHub config repo]
                                                    │
                                           Copilot opens PR
                                                    │
                                             Human reviews
                                                    │
                                               Merge to main
                                                    │
                         [Home Assistant] ◄──(inbound apply)──
```

## Contributing

See [`.github/copilot-instructions.md`](.github/copilot-instructions.md)
for coding conventions and security rules.

## License

MIT
