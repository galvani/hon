# AGENTS.md

Guide for anyone — human or coding agent — changing this repository. Read it before the first edit.

## What this is

A Home Assistant custom integration (domain `hon`) for Haier, Candy and Hoover appliances connected to Haier's hOn cloud. It is distributed through HACS as a custom repository.

This repository is **galvani/hon**, maintained on top of [mmalolepszy/hon-revived](https://github.com/mmalolepszy/hon-revived), which continues [Andre0512/hon](https://github.com/Andre0512/hon). Most of the integration code is theirs; see [Syncing with hon-revived](#syncing-with-hon-revived) before restyling anything.

## Documentation map

| File | Holds |
| --- | --- |
| `AGENTS.md` | How to work here: architecture, standards, recipes, checks (this file) |
| `SPEC.md` | What the integration does and deliberately does not do |
| `JOURNAL.md` | Decisions and why, newest first |
| `README.md` | User-facing: install, configure, supported appliances (partly generated) |
| `tests/fixtures/README.md` | Where the offline appliance data comes from and how to refresh it |
| `docs/history/` | The 2024 takedown story, kept as the original author wrote it |

Filing rule: a rule for contributors goes here; a behaviour promise goes in `SPEC.md`; the reason behind a decision goes in `JOURNAL.md`; anything a user needs to install or use it goes in `README.md`.

## Architecture

```
hOn cloud ──REST──► pyhon (pyhon-revived) ──► HonAppliance objects
     └──MQTT push──► Hon.notify() ──► coordinator ──► every entity refreshes
```

- **`__init__.py`** — `async_setup_entry` logs in with `pyhon.Hon`, stores `{"hon": hon, "coordinator": coordinator}` in `hass.data[DOMAIN][entry.unique_id]`, and forwards to the platforms in `const.PLATFORMS`. The coordinator does not poll: pyhon's MQTT client calls the function given to `hon.subscribe_updates`, from the MQTT library's own thread, so that function hands the update to the event loop with `call_soon_threadsafe`.
- **`entity.py`** — `HonEntity`, the base of every entity: device info, `unique_id`, and coordinator wiring.
- **One module per platform** (`sensor.py`, `switch.py`, `select.py`, `number.py`, `binary_sensor.py`, `button.py`, `climate.py`, `fan.py`, `light.py`, `lock.py`). Each one has:
  - a dict of **entity descriptions keyed by appliance type** (`SENSORS["WM"]`, `SWITCHES["AC"]`, …) — this table *is* the feature list;
  - an `async_setup_entry` that walks `hon.appliances` and creates an entity for each description the device actually has;
  - the entity classes.
- **Appliance types** are the codes in `const.APPLIANCES` (`WM` washing machine, `TD` tumble dryer, `WD` washer-dryer, `DW` dishwasher, `AC`, `OV`, `REF`, …). Combined types reuse others: `SENSORS["WD"] = unique_entities(SENSORS["WM"], SENSORS["TD"])`.

### Favourites and the washer card

- **`favourite.py`** — one `select` per appliance listing the favourites saved in the hOn app. pyhon loads them at startup and adds each as an extra program, but it shallow-copies the base program, so the base also carries the `favourite` flag and shares its parameters. A favourite is told apart by its key differing from its category's program name. New favourites appear after the integration reloads.
- **`recent.py`** — remembers the last programs each washer, dryer or dishwasher started (from the machine, the app or HA) in `.storage/hon.recent_programs.<entry_id>`, seeded from hOn's command history on first start. It reads the program from `prCode` itself, because pyhon's `programName` skips the base program of a favourite. The card reads it over the `hon/recent_programs` websocket command.
- **`frontend.py` + `www/hon-washer-card.js`** — a dependency-free Lovelace card (`custom:hon-washer-card`, `layout: full` or `compact`), served from the integration at `/hon_static/` and registered automatically, so installing the integration installs the card. It finds its entities by `device_id` and `translation_key` from `hass.entities`, so renaming a `translation_key` it uses breaks the card. Iterate on it with `dev/card-preview.html` (serve the repo root with `python -m http.server`, open `/dev/card-preview.html`), which mounts the card with a mock `hass` in three states.

### Where an entity's value comes from

Description classes come in three kinds, and the kind decides where the value is read and how it is written:

| Kind | Example class | Reads | Writes | Created when |
| --- | --- | --- | --- | --- |
| Plain | `HonSensorEntityDescription` | `device.get(key)` — live attributes | — or `settings.<key>` + `commands["settings"].send()` | `device.get(key) is not None` |
| Config | `HonConfigSensorEntityDescription`, `HonConfigNumberEntityDescription` | `device.settings[key]` — a command parameter such as `startProgram.temp` | sets the parameter; it is sent with the next program start | `key in device.available_settings` |
| Control | `HonControlSwitchEntityDescription` | `device.get(key)` | sends the `turn_on_key` / `turn_off_key` command | as plain |

Option values: `option_list` (an `int → str` map, usually from `const`) turns a raw device code into a translation key; `util.get_readable` applies it.

### Identity is load-bearing

`unique_id` is `device.unique_id + description.key`. Renaming a `key`, or moving a description to another appliance type, orphans the entity in every user's installation and breaks their automations and history. Add new descriptions; never re-key existing ones.

## Coding standards

1. **Leave existing code as it is, unless it is wrong.** The integration is merged from hon-revived regularly. Reformatting, reordering, renaming or "tidying" their files turns every future merge into conflicts. Change only what your task needs, in the style already there.
2. **New behaviour goes in a description table first.** A new sensor is a new `Hon…EntityDescription` entry, not a new entity class. Add a class only when the read/write mechanics differ from every existing kind.
3. **Every entity has a `translation_key`.** `name=` is the English fallback; the UI label comes from `translations/<lang>.json`. `scripts/check.py` lists descriptions that are missing one.
4. **Use Home Assistant's units and device classes** (`UnitOfEnergy`, `SensorDeviceClass`, `SensorStateClass`, …). Never write a unit as a string, and give cumulative counters `TOTAL_INCREASING`.
5. **No blocking I/O on the event loop.** File and network work goes through `hass.async_add_executor_job` or pyhon's async API. Anything arriving from pyhon's MQTT thread must cross to the loop with `hass.loop.call_soon_threadsafe` before it touches HA state.
6. **Typed.** `mypy -p custom_components.hon` is part of CI. Don't silence it with `# type: ignore` when a narrower type fixes it.
7. **Comments only for traps the code cannot show.** One line, present tense. The why of a change goes in the commit message or `JOURNAL.md`, not in the code.
8. **Tests prove behaviour against real appliance data.** Use the fixtures in `tests/fixtures/hon-test-data/` (real dumps from real appliances), assert exact values and counts, and add a fixture rather than loosening an assertion.

## Recipes

### Add a sensor (or switch, number, select…) to an appliance type

1. Find the key. Enable and press the appliance's diagnostic **Show Device Info** button in HA (it is disabled by default), or read `attributes.json` / `commands.json` in a fixture dump) and note the attribute or parameter name.
2. Add a description to the right table, e.g. `SENSORS["WM"]` in `sensor.py`. Choose the plain or config kind from the table above.
3. Add a `translation_key` and its English text in `translations/en.json` under `entity.<platform>.<translation_key>.name`. Other languages: see [Translations](#translations).
4. If the device needs a fixture that has this key, add one to `tests/fixtures/`. Extend the entity-count test for that appliance.
5. Run `python scripts/create_docs.py` to refresh the generated entity tables in `README.md`.
6. Run the checks below.

### Add an appliance type

Add the code and name to `const.APPLIANCES`, add a tuple for it to each platform table that applies, add a fixture, and add the model names to `supported_models.yml`. Prefer composing from an existing type with `unique_entities` when the device is a combination.

### Translations

`translations/*.json` are generated from hOn's own app translations so labels match what users see on their phones:

- `scripts/translation_keys.py` maps our translation keys to hOn's keys (e.g. `WASHING_CMD&CTRL.PHASE_SPIN.TITLE`).
- `scripts/generate_translation.py` downloads hOn's translations (anonymous, no account needed) and rewrites every language file.

Add the mapping, then run the generator. Edit `en.json` by hand only for strings hOn does not have.

### Generated content — don't hand-edit

- `README.md` → *Supported Appliances* section and the Entities/Models badges: `scripts/create_docs.py` (from the description tables and `supported_models.yml`).
- `translations/*.json`: `scripts/generate_translation.py`.

## Checks

Run all of these before pushing; CI runs the same set on every push and pull request.

```sh
uv sync --group dev                    # dev environment (Python 3.14, current Home Assistant)
uv run ruff check .
uv run black --check .
uv run mypy -p custom_components.hon
uv run pytest
```

`uvx pre-commit install` runs the formatters and linters on each commit.

The tests start a real Home Assistant instance in-process (`pytest-homeassistant-custom-component`) and load appliances from the fixture dumps through pyhon's `TestAPI`. Nothing reaches the network, and no hOn account is needed.

## Syncing with hon-revived

```sh
git remote add revived https://github.com/mmalolepszy/hon-revived.git   # once
git fetch revived
git merge revived/main
```

Then restore this fork's identity, which their merge may overwrite:

- `manifest.json`: `name` "Haier hOn", `codeowners` led by `@galvani`, `documentation` and `issue_tracker` pointing at galvani/hon, and `version` `<their version>.<n>` (e.g. `0.19.2.1`);
- `hacs.json`: `name` "Haier hOn";
- `README.md`: the header and Credits;
- the issue-template assignees and the issue link in `button.py`.

Run the checks, credit their release in the merge commit, and add a `JOURNAL.md` entry. Merge — never rebase or force-push `main`; installed copies and forks follow it.

## Releasing

HACS installs from GitHub **releases**, not from `main`: `release.yml` zips `custom_components/hon` into `haier_hon.zip` when a release is published. Pushing to `main` reaches nobody until a release is published. Bump `manifest.json` `version`, then tag `v<version>` and publish the release.
