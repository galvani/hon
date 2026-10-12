from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.hon.const import DOMAIN

from .conftest import FakeHon


def _washer(fake_hon: FakeHon) -> Any:
    return next(a for a in fake_hon.appliances if a.appliance_type == "WM")


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    assert await async_setup_component(hass, "websocket_api", {})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def _recent(
    hass: HomeAssistant, client_factory: WebSocketGenerator, fake_hon: FakeHon
) -> dict[str, Any]:
    washer_id = (DOMAIN, _washer(fake_hon).unique_id)
    device = next(
        device
        for device in dr.async_entries_for_config_entry(
            dr.async_get(hass),
            next(iter(hass.config_entries.async_entries(DOMAIN))).entry_id,
        )
        if washer_id in device.identifiers
    )
    client = await client_factory()
    await client.send_json_auto_id(
        {"type": "hon/recent_programs", "device_id": device.id}
    )
    response: dict[str, Any] = await client.receive_json()
    return response


async def test_recent_programs_start_from_hon_history(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    mock_hon: FakeHon,
    config_entry: MockConfigEntry,
) -> None:
    await _setup(hass, config_entry)

    response = await _recent(hass, hass_ws_client, mock_hon)

    assert response["success"]
    assert response["result"]["programs"] == [
        "iot_wash_dark",
        "eco_40_60_new_energy_label",
        "iot_wash_pets_odours_stains_removal",
        "iot_wash_lingerie",
        "iot_wash_coloured_shirts",
    ]


async def test_a_started_program_moves_to_the_front(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    mock_hon: FakeHon,
    config_entry: MockConfigEntry,
) -> None:
    await _setup(hass, config_entry)
    washer = _washer(mock_hon)
    cottons = washer.commands["startProgram"].categories["cottons"]
    parameters = washer.attributes["parameters"]
    parameters["prCode"].value = str(cottons.parameters["prCode"].value)
    parameters["machMode"].value = "2"

    coordinator = hass.data[DOMAIN][config_entry.unique_id]["coordinator"]
    coordinator.async_set_updated_data({})
    await hass.async_block_till_done()

    response = await _recent(hass, hass_ws_client, mock_hon)
    assert response["result"]["programs"] == [
        "cottons",
        "iot_wash_dark",
        "eco_40_60_new_energy_label",
        "iot_wash_pets_odours_stains_removal",
        "iot_wash_lingerie",
    ]


async def test_unknown_device_is_an_error(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    mock_hon: FakeHon,
    config_entry: MockConfigEntry,
) -> None:
    await _setup(hass, config_entry)
    client = await hass_ws_client()
    await client.send_json_auto_id(
        {"type": "hon/recent_programs", "device_id": "missing"}
    )
    response = await client.receive_json()
    assert not response["success"]
    assert response["error"]["code"] == "not_found"
