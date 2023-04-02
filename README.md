# Haier hOn
[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)

Home Assistant integration for Haier hOn: support for Haier/Candy/Hoover home appliances like washing machines.
## Supported Appliances
- Washing Machine
- Tumble Dryer


## Installation
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Andre0512&repository=hon&category=integration)

**Method 1:** [HACS](https://hacs.xyz/) > Integrations > Add Integration > **Haier hOn** > Install  

**Method 2.** Manually copy `hon` folder from [latest release](https://github.com/Andre0512/hon/releases/latest) to `/config/custom_components` folder.

## Configuration

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=hon)

Settings > Devices & Services > Add Integration > **Haier hOn**

If the integration is not in the list, you need to clear the browser cache.

## Contribute
Any kind of contribution is welcome!
#### Add appliances or additional attributes
1. Install [pyhOn](https://github.com/Andre0512/pyhOn)
   ```commandline
    $ pip install pyhOn
    ```
2. Use the commandline tool to read out all appliance data from your account
    ```commandline
    $ pyhOn
    User for hOn account: user.name@example.com
    Password for hOn account: ********
    ========== WM - Washing Machine ==========
    commands:
      pauseProgram: pauseProgram command
      resumeProgram: resumeProgram command
      startProgram: startProgram command
      stopProgram: stopProgram command
    data:
      actualWeight: 0
      airWashTempLevel: 0
      airWashTime: 0
      antiAllergyStatus: 0
      ...
    ```
3. Fork this repository and clone it to your local machine
4. Add the keys of the attributes you'd like to have as `EntityDescription` into this Repository  
   _Example: Add pause button_
    ```python
    BUTTONS: dict[str, tuple[ButtonEntityDescription, ...]] = {
        "WM": (                        # WM is the applianceTypeName
            ButtonEntityDescription(
                key="pauseProgram",    # key from pyhOn
                name="Pause Program",  # name in home assistant
                icon="mdi:pause",      # icon in home assistant
                ...
            ),
        ...
    ```
5. Create a [pull request](https://github.com/Andre0512/hon/pulls)

#### Tips and Tricks
- If you want to have some states humanreadable, have a look at the `translation_key` parameter of the `EntityDescription`
- If you need to implement some more logic, create a pull request to the underlying library. There we collect special requirements in the `appliances` directory.

## Tested Devices
- Haier WD90-B14TEAM5
- Haier HD80-A3959

## About this Repo
The existing integrations missed some features from the app I liked to have in HomeAssistant.
I tried to create a pull request, but in the structures of these existing repos, I find it hard to fit in my needs, so I basically rewrote everything. 
I moved the api related stuff into the package [pyhOn](https://github.com/Andre0512/pyhOn).
