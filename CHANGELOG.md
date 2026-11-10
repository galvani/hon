# Changelog

## 0.19.2.5

### Fixed

- **The Program sensor names the program that is running**, including programs started from the hOn app and your favourites. It used to show "No Program" for them.
- **The washing machine card no longer shows the previous wash right after a start.** Until the machine sends its first update, the card shows "Starting…" and the program you picked, instead of the last run's time left and program.

## 0.19.2.4

### New

- **Wash options on the washing machine card.** Pre-wash, extra water, hygiene, quiet night and anti-crease are now toggles on the card, and extra rinses (+1, +2, +3) are one choice row. The card shows only the options the selected program allows, so picking a favourite shows that favourite's options, ready to change before you press Start.

## 0.19.2.3

### Fixed

- **Appliances no longer stay "offline" after they come back.** When Home Assistant missed the message that an appliance had reconnected, it kept showing it as disconnected, and its start switch and other controls stayed unavailable until Home Assistant restarted, even though the appliance worked in the hOn app. The integration now re-reads every appliance from hOn every 5 minutes, so the connection status and the controls come back on their own.

## 0.19.2.2

### New

- **Sign in again without removing the integration.** When hOn stops accepting your login, for example after you change your password in the hOn app, Home Assistant shows a "re-authentication required" notification. Enter your password there and the integration reloads with your devices, entities and history intact.
- **Login check during setup.** Adding the integration checks your email and password with hOn and tells you right away if they are wrong or hOn cannot be reached.

### Fixed

- A switch, button or other control used while hOn rejects the login now shows a message telling you to sign in again.
- When hOn cannot be reached while Home Assistant starts, the integration retries on its own.

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
