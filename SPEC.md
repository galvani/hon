# Haier hOn — Specification

## Purpose

Expose appliances registered in Haier's hOn app (Haier, Candy, Hoover) as Home Assistant devices and entities: their state, their settings, and the commands the app can send.

## Behaviour

- **Setup:** a config flow asks for the hOn account email and password and checks them against hOn before creating the entry. The refresh token is stored in the config entry and reused on the next start.
- **Rejected login:** when hOn rejects the stored login — at start, on a command, or in pyhon's own background re-login (checked every 5 minutes) — Home Assistant shows its "re-authentication required" notification, and the user enters the password again without removing the integration. A command that fails this way raises a readable error instead of an unexpected exception. hOn being unreachable at start retries the setup instead.
- **Discovery:** every appliance on the account becomes one HA device. An appliance that reports several zones becomes one device per zone, plus one for the whole appliance.
- **Entities:** for each appliance type in `const.APPLIANCES`, the platform tables declare the possible entities. An entity is created only when the appliance reports the attribute or setting behind it, so two models of the same type can show different entity sets.
- **Updates:** state arrives as MQTT push from the hOn cloud. Every 5 minutes the integration also re-reads each appliance over REST, so a push that never arrived (above all an appliance coming back online) is corrected within 5 minutes instead of staying wrong until Home Assistant restarts.
- **Control:** switches, selects, numbers, buttons, climate, fan, light and lock entities send commands through the hOn cloud, as the app does.
- **Language:** entity names and states come from hOn's own app translations, in the 28 languages listed in `const.LANGUAGES`.
- **Diagnostics:** two disabled-by-default buttons per appliance: one shows the raw device data, the other writes an anonymised data archive for bug reports.

## Constraints

- Cloud only: no local API exists, so the integration needs the internet and a working hOn account.
- Stability of entity identity: an entity's `unique_id` is the appliance id plus the description key, and must not change across releases.
- Minimum Home Assistant version: the one in `hacs.json` (2026.7.0, the first release with `UnitOfDensity` and `UnitOfRatio`).

## Not in scope

- Local control without the hOn cloud.
- Appliances that use other Haier apps (Haier U+, Uhome, Evo, GE SmartHQ).
- Editing appliance programs or recipes beyond what the hOn command parameters allow.
