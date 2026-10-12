# Journal

Decisions and their reasons, newest first.

## 2026-10-12 — Favourites and the washer card

- **Decision:** expose hOn app favourites as their own `select` ("Favourite program") instead of only as entries hidden among 175 programs. pyhon already loads them; it flags the base program too because it shallow-copies it, so favourites are identified by key ≠ program name.
- **Decision:** ship the washer card inside the integration (served from `www/`, registered with `add_extra_js_url`) rather than as a separate HACS frontend repo, so the card version always matches the entity keys it reads.
- **Decision:** no frontend dependencies or CDN: a plain web component, themed only through Home Assistant's CSS variables.
- **Known upstream issue:** sharing parameters between a favourite and its base program means the Program select can show a favourite's name while the Program sensor shows the real program. Not fixed here; it belongs in pyhon-revived.
- **Fixed:** lights had no `color_mode`, which current Home Assistant rejects when the light is on.

## 2026-10-12 — Agent docs, tooling and tests

- **Decision:** add `AGENTS.md` (with `CLAUDE.md` importing it), `SPEC.md` and this journal, written from the code rather than from memory.
- **Decision:** the cleanup leaves hon-revived's Python code as it is. Restyling it would turn every future merge from upstream into conflicts; tooling, tests, CI and docs carry the improvements instead.
- **Decision:** add an offline test suite (`pytest-homeassistant-custom-component` + real appliance dumps from hon-test-data via pyhon's `TestAPI`) and run CI against current Home Assistant. It previously ran on HA 2024.2/2024.3 only and had no tests.
- **Decision:** move the 2024 takedown story into `docs/history/`; it is history, not usage documentation.

## 2026-10-12 — Rebased the fork on hon-revived

- **Decision:** merge `mmalolepszy/hon-revived` v0.19.2 into this fork, and keep maintaining galvani/hon on top of it, synced by merge.
- **Rationale:** the original Andre0512/hon has had no commits since August 2024. hon-revived is maintained (v0.19.x, new entities, translations, pyhon-revived) and already contained most of this fork's own fixes. Keeping this fork lets its users keep their HACS source and lets this repo carry its own changes.
- **Alternatives considered:** retiring the fork in favour of hon-revived (or gvigroux/hon, which is in the HACS default list); rejected so this repo stays independently updatable.
- **Dropped:** the module that appended a RapidSSL intermediate to Home Assistant's shared certifi bundle. The hOn servers now send a complete chain (checked with `openssl s_client` and Python + certifi), and patching the shared bundle forced a restart after every certifi update.
- **Dropped:** the 60-second polling of every appliance. It was a workaround for entities not refreshing on MQTT push, which hon-revived fixed with `schedule_update_ha_state`.
- **Kept on top of hon-revived:** sensors with a state class report 0 for an empty value instead of overwriting it; the MQTT callback crosses to the event loop with `call_soon_threadsafe`; unloading an entry removes its data.
- **Versioning:** `<hon-revived version>.<n>`, e.g. `0.19.2.1`.
