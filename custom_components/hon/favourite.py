from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from pyhon.appliance import HonAppliance

from .entity import HonEntity

PROGRAM_KEY = "startProgram.program"

FAVOURITE_DESCRIPTION = SelectEntityDescription(
    key="favourite_program",
    icon="mdi:star",
    translation_key="favourite_program",
)


def _program_name(category: str) -> str:
    return category.split(".")[-1].lower() if "PROGRAM" in category else category


def favourite_names(device: HonAppliance) -> list[str]:
    # pyhon shallow-copies a favourite's base program, so the base program carries
    # the "favourite" flag too; only the favourite's key differs from its category.
    if (command := device.commands.get("startProgram")) is None:
        return []
    return sorted(
        name
        for name, program in command.categories.items()
        if "favourite" in program.parameters and name != _program_name(program.category)
    )


def favourite_entities(
    hass: HomeAssistant, entry: ConfigEntry, devices: list[HonAppliance]
) -> list["HonFavouriteSelectEntity"]:
    return [
        HonFavouriteSelectEntity(hass, entry, device)
        for device in devices
        if PROGRAM_KEY in device.available_settings and favourite_names(device)
    ]


class HonFavouriteSelectEntity(HonEntity, SelectEntity):
    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, device: HonAppliance
    ) -> None:
        super().__init__(hass, entry, device, FAVOURITE_DESCRIPTION)

    async def async_select_option(self, option: str) -> None:
        self._device.settings[PROGRAM_KEY].value = option
        self.coordinator.async_set_updated_data({})

    @callback
    def _handle_coordinator_update(self, update: bool = True) -> None:
        self._attr_options = favourite_names(self._device)
        setting = self._device.settings.get(PROGRAM_KEY)
        current = str(setting.value) if setting is not None else None
        self._attr_current_option = current if current in self._attr_options else None
        if update:
            self.schedule_update_ha_state()
