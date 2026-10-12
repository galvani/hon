# Changelog

## 0.19.2.1

This release moves the integration onto [hOn Revived](https://github.com/mmalolepszy/hon-revived) 0.19.2 by [mmalolepszy](https://github.com/mmalolepszy) and its contributors, so you get everything they have built since the original integration stopped: more oven, dishwasher, washing machine and air conditioner entities, translations, and the current [pyhon-revived](https://pypi.org/project/pyhon-revived/) library.

### Before you update

- **Home Assistant 2026.7 or newer is required.** HACS will not offer this update on older versions.
- **Restart twice if setup fails with `function takes exactly 43 arguments (45 given)`.** The first start installs the new library; when another integration already loaded the same component (for example LG ThinQ), the second restart finishes the job.
- **Leave the old `pyhOn` package installed** if you see it next to `pyhon-revived`. Both use the same folder; removing the old one by hand also removes files the new one needs.

### New

- **Washing machine card.** A dashboard card for washing machines, washer-dryers and dryers: time left, the current stage, program and favourite pickers, temperature and spin, start, pause and stop. Add it from the card picker ("hOn washing machine"); it is installed with the integration. Use `layout: compact` for a single row with your two most recent programs.
- **Favourite program.** A new select per appliance with the favourites you saved in the hOn app.
- **Recent programs.** The integration remembers the programs your machine runs, whether started on the machine, in the hOn app or in Home Assistant, and the card offers the last two as one-tap choices.

### Fixed

- Sensors with an empty value report 0 instead of an error.
- Hood and air purifier lights work on current Home Assistant.
- Live updates from the hOn cloud are handed to Home Assistant safely.
- Reloading the integration starts cleanly.

### Removed

- The certificate workaround from earlier releases of this fork. hOn's servers no longer need it, and it modified Home Assistant's shared certificate store.
