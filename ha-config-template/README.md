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
├── customize.yaml           # Entity name, icon, and attribute overrides
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
- `customize.yaml` – entity friendly names, icons, and attribute overrides
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

## Editing entity names and icons

Entity attributes (friendly name, icon, hidden state, etc.) can be set for
**any** entity directly from this repository — no need to change them through
the Home Assistant UI.

> **Note:** Changes made via the HA UI "Entity settings" dialog are stored in
> `.storage/core.entity_registry`, which is intentionally excluded from sync
> (it contains runtime state and privacy-sensitive data).  
> The correct, version-controlled way to customise entities is `customize.yaml`.

### Prerequisites

Your `configuration.yaml` must include:

```yaml
homeassistant:
  customize: !include customize.yaml
```

If this line is already present, no further changes to `configuration.yaml`
are needed.  If `customize.yaml` does not yet exist in the repo it will be
created by the sync addon on the next outbound cycle, or you can create it
with the content below.

### customize.yaml format

```yaml
# customize.yaml
# Key: entity_id (domain.object_id)
light.living_room_main:
  friendly_name: Living Room Ceiling Light
  icon: mdi:ceiling-light

switch.garden_pump:
  friendly_name: Garden Irrigation Pump
  icon: mdi:water-pump

sensor.outdoor_temperature:
  friendly_name: Outside Temperature
  icon: mdi:thermometer

binary_sensor.front_door:
  friendly_name: Front Door
  device_class: door
```

### Supported attributes

| Attribute | Description |
|-----------|-------------|
| `friendly_name` | Display name shown in the HA UI |
| `icon` | Any [Material Design Icon](https://pictogrammers.com/library/mdi/) (`mdi:...`) |
| `hidden` | `true` to hide the entity from default views |
| `device_class` | Override the device class (e.g. `door`, `motion`, `temperature`) |
| `unit_of_measurement` | Override the unit shown for sensor entities |
| `entity_picture` | URL to a custom entity image |

After merging a PR that modifies `customize.yaml`, restart Home Assistant (or
use **Developer Tools → YAML → Reload Customize**) to apply the changes.
