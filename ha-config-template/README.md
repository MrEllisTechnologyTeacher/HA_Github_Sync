# Home Assistant Config Repository

This repository is managed by the **HA GitHub Sync** add-on.  
It contains a versioned copy of selected Home Assistant configuration files
and is the authoritative source for **GitHub Copilot-assisted edits**.

## Directory structure

```
.
├── automations.yaml         # HA automations
├── scripts.yaml             # HA scripts
├── scenes.yaml              # HA scenes
├── groups.yaml              # HA groups
├── input_boolean.yaml       # Input booleans
├── input_number.yaml        # Input numbers
├── input_select.yaml        # Input selects
├── input_text.yaml          # Input text helpers
├── input_datetime.yaml      # Input datetime helpers
├── packages/                # HA packages (optional)
├── blueprints/              # Automation blueprints
├── custom_components/       # Custom integrations (if tracked)
├── lovelace/                # Dashboard YAML (if applicable)
├── dashboards/              # Additional dashboards
└── .ha-sync-manifest.json   # Auto-generated: tracked paths & metadata
```

## Branch workflow

| Branch | Purpose |
|--------|---------|
| `main` | Active config – sync target for the HA addon |
| `copilot/*` | Copilot-generated change branches |
| `backup/pre-inbound` | Auto-created by addon before applying inbound changes |

### Copilot editing workflow

1. Open a new branch: `git checkout -b copilot/my-change`
2. Edit one or more config files.
3. Open a Pull Request targeting `main`.
4. Review the PR; ensure CI validation passes.
5. Merge into `main`.
6. The HA GitHub Sync addon picks up the change on the next inbound sync
   cycle *(bidirectional mode only)*, or you can restart the addon to
   trigger an immediate apply.

## What Copilot should and should not touch

### ✅ Safe to edit automatically

- `automations.yaml`, `scripts.yaml`, `scenes.yaml`
- `input_*.yaml` helpers
- Files under `packages/`
- Files under `blueprints/`
- Dashboard YAML under `lovelace/` or `dashboards/`

### ❌ Never edit automatically

- `secrets.yaml` – never tracked; all secret values must use `!secret`
- `.storage/` – runtime HA state; not tracked
- `configuration.yaml` – high-risk; requires human review before change
- `known_devices.yaml` – contains MAC addresses (privacy)
- Any file containing credentials or tokens

## Secret handling

All credential values **must** use the Home Assistant `!secret` tag:

```yaml
# ✅ Correct
mqtt:
  password: !secret mqtt_password

# ❌ Never commit this
mqtt:
  password: my-real-password
```

The addon's secret scanner will warn about patterns that look like bare
credentials.

## Validation

Before merging a PR, ensure:

1. All YAML files are syntactically valid (`yamllint` or similar).
2. No bare secrets are present.
3. Any automation/script IDs are unique.
4. The PR description explains what Home Assistant domain is affected.

## Questions & issues

Open an issue at https://github.com/MrEllisTechnologyTeacher/HA_Github_Sync
