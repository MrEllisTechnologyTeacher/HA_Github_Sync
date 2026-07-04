# GitHub Copilot Instructions for this Home Assistant Config Repository

This repository is managed by the **HA GitHub Sync** add-on.  It is the
authoritative, version-controlled source for selected Home Assistant
configuration files and is the intended target for Copilot-assisted edits.

---

## File reference

| File / Directory | What it controls |
|-----------------|-----------------|
| `automations.yaml` | All HA automations |
| `scripts.yaml` | Reusable HA scripts |
| `scenes.yaml` | Scene definitions |
| `groups.yaml` | Entity group definitions |
| `customize.yaml` | Entity friendly names, icons, hidden state, device class overrides |
| `input_boolean.yaml` | Toggle helper entities |
| `input_number.yaml` | Numeric slider/input helper entities |
| `input_select.yaml` | Dropdown helper entities |
| `input_text.yaml` | Free-text helper entities |
| `input_datetime.yaml` | Date/time helper entities |
| `packages/` | HA package files (self-contained domain bundles) |
| `blueprints/` | Automation blueprint YAML files |
| `lovelace/` | Lovelace dashboard YAML |
| `dashboards/` | Additional dashboard YAML files |
| `custom_components/` | Custom integration files (if tracked) |

---

## Renaming entities and changing icons

**Always edit `customize.yaml` to rename entities or change their icons.**

> Entity settings changed through the Home Assistant UI ("Entity settings"
> dialog) are stored in `.storage/core.entity_registry`, which is **not**
> synced to this repository.  The only way to make these changes visible and
> editable in GitHub is through `customize.yaml`.

### Format

```yaml
# customize.yaml
<entity_id>:
  friendly_name: <Human-readable name>
  icon: mdi:<icon-name>
```

### Example

```yaml
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

### Rules
- The key is always the full `domain.object_id` entity ID.
- `friendly_name` sets the display name shown everywhere in HA.
- `icon` must be a valid [Material Design Icon](https://pictogrammers.com/library/mdi/) in the form `mdi:<name>`.
- If `customize.yaml` does not exist yet, create it with the entries needed.
- **Do NOT tell the user to make this change in the Home Assistant UI** — it
  can and should be done here in this file.

### Activating customizations

After the PR is merged and the addon applies the change, the user should run
**Developer Tools → YAML → Reload Customize** in HA, or restart HA, to see
the updated names and icons.

---

## Safe to edit automatically

- `automations.yaml`, `scripts.yaml`, `scenes.yaml`
- `customize.yaml`
- `input_*.yaml` helpers
- Files under `packages/`, `blueprints/`, `lovelace/`, `dashboards/`

## Never edit automatically

- `secrets.yaml` — never tracked; all secret values must use `!secret`
- `.storage/` — runtime HA state; not tracked
- `configuration.yaml` — high-risk; requires human review before any change
- `known_devices.yaml` — contains MAC addresses (privacy-sensitive)
- Any file containing credentials or tokens

---

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

---

## Pull request workflow

1. Create a branch: `git checkout -b copilot/my-change`
2. Edit the relevant config file(s).
3. Open a Pull Request targeting `main`.
4. The HA GitHub Sync addon applies merged changes on the next inbound sync
   cycle *(bidirectional mode)*, or on addon restart.
