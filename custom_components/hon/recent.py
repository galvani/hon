import logging
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from pyhon.appliance import HonAppliance

from .favourite import program_name

_LOGGER = logging.getLogger(__name__)

STORAGE_KEY = "hon.recent_programs"
KEEP = 5
RUNNING_MODES = {2, 3}
PROGRAM_TYPES = {"WM", "WD", "TD", "DW"}


class RecentPrograms:
    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, list[str]]] = Store(
            hass, 1, f"{STORAGE_KEY}.{entry_id}"
        )
        self._programs: dict[str, list[str]] = {}
        self._running: dict[str, bool] = {}

    def get(self, device: HonAppliance) -> list[str]:
        return list(self._programs.get(device.unique_id, []))

    async def async_load(self, devices: list[HonAppliance]) -> None:
        self._programs = await self._store.async_load() or {}
        for device in devices:
            if device.appliance_type not in PROGRAM_TYPES:
                continue
            self._running[device.unique_id] = self._is_running(device)
            if device.unique_id not in self._programs:
                self._programs[device.unique_id] = await self._from_history(device)
        self._save()

    @callback
    def async_update(self, devices: list[HonAppliance]) -> None:
        for device in devices:
            if device.appliance_type not in PROGRAM_TYPES:
                continue
            running = self._is_running(device)
            started = running and not self._running.get(device.unique_id, False)
            self._running[device.unique_id] = running
            if started and (program := self._running_program(device)):
                self._remember(device.unique_id, program)

    def _remember(self, unique_id: str, program: str) -> None:
        programs = self._programs.get(unique_id, [])
        self._programs[unique_id] = [program] + [p for p in programs if p != program]
        del self._programs[unique_id][KEEP:]
        self._save()

    def _save(self) -> None:
        self._store.async_delay_save(lambda: self._programs, 5)

    @staticmethod
    def _running_program(device: HonAppliance) -> str | None:
        try:
            code = int(device.get("prCode", 0))
        except TypeError, ValueError:
            return None
        if (command := device.commands.get("startProgram")) is None:
            return None
        for name, program in command.categories.items():
            parameter = program.parameters.get("prCode")
            if (
                parameter is not None
                and str(parameter.value) == str(code)
                and name == program_name(program.category)
            ):
                return name
        return None

    @staticmethod
    def _is_running(device: HonAppliance) -> bool:
        try:
            return int(device.get("machMode", 0)) in RUNNING_MODES
        except TypeError, ValueError:
            return False

    @staticmethod
    async def _from_history(device: HonAppliance) -> list[str]:
        try:
            history: list[dict[str, Any]] = await device.api.load_command_history(
                device
            )
        except Exception as error:  # noqa: BLE001
            _LOGGER.debug("No command history for %s: %s", device.nick_name, error)
            return []
        programs: list[str] = []
        for item in history or []:
            command = item.get("command", {})
            if command.get("commandName") != "startProgram":
                continue
            program = program_name(command.get("programName", ""))
            if program and program not in programs:
                programs.append(program)
        return programs[:KEEP]


async def async_setup_recent(
    hass: HomeAssistant,
    entry_id: str,
    devices: list[HonAppliance],
    coordinator: DataUpdateCoordinator[dict[str, Any]],
) -> RecentPrograms:
    recent = RecentPrograms(hass, entry_id)
    await recent.async_load(devices)
    coordinator.async_add_listener(lambda: recent.async_update(devices))
    return recent
