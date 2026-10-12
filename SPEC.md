# Haier hOn — Specification

## Purpose

Expose appliances registered in Haier's hOn app (Haier, Candy, Hoover) as Home Assistant devices and entities: their state, their settings, and the commands the app can send.

## Behaviour

- **Setup:** a config flow asks for the hOn account email and password. The refresh token is stored in the config entry and reused on the next start.
- **Discovery:** every appliance on the account becomes one HA device. An appliance that reports several zones becomes one device per zone, plus one for the whole appliance.
- **Entities:** for each appliance type in `const.APPLIANCES`, the platform tables declare the possible entities. An entity is created only when the appliance reports the attribute or setting behind it, so two models of the same type can show different entity sets.
- **Updates:** state arrives as MQTT push from the hOn cloud; the integration does not poll.
- **Control:** switches, selects, numbers, buttons, climate, fan, light and lock entities send commands through the hOn cloud, as the app does.
- **Language:** entity names and states come from hOn's own app translations, in the 28 languages listed in `const.LANGUAGES`.
- **Diagnostics:** two disabled-by-default buttons per appliance: one shows the raw device data, the other writes an anonymised data archive for bug reports.

## Constraints

- Cloud only: no local API exists, so the integration needs the internet and a working hOn account.
- Stability of entity identity: an entity's `unique_id` is the appliance id plus the description key, and must not change across releases.
- Minimum Home Assistant version: the one in `hacs.json`.

## Not in scope

- Local control without the hOn cloud.
- Appliances that use other Haier apps (Haier U+, Uhome, Evo, GE SmartHQ).
- Editing appliance programs or recipes beyond what the hOn command parameters allow.
