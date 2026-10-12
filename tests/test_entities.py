from __future__ import annotations

import asyncio
import logging
import threading

import pytest
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import FakeHon

EXPECTED_COUNTS: dict[str, dict[str, int]] = {
    "AC397": {
        "binary_sensor": 3,
        "climate": 1,
        "number": 1,
        "select": 4,
        "sensor": 9,
        "switch": 9,
    },
    "AP137": {
        "binary_sensor": 1,
        "light": 1,
        "lock": 1,
        "number": 3,
        "select": 2,
        "sensor": 12,
        "switch": 1,
    },
    "DW522": {
        "binary_sensor": 6,
        "number": 2,
        "select": 3,
        "sensor": 11,
        "switch": 4,
    },
    "HO710": {"fan": 1, "light": 1, "sensor": 12, "switch": 1},
    "OV577": {
        "binary_sensor": 5,
        "climate": 1,
        "number": 4,
        "select": 1,
        "sensor": 5,
        "switch": 2,
    },
    "REF10009": {
        "binary_sensor": 5,
        "button": 2,
        "climate": 3,
        "number": 3,
        "select": 2,
        "sensor": 3,
    },
    "TD624": {
        "binary_sensor": 3,
        "number": 2,
        "select": 3,
        "sensor": 9,
        "switch": 3,
    },
    "WD209": {
        "binary_sensor": 8,
        "number": 3,
        "select": 6,
        "sensor": 15,
        "switch": 10,
    },
    "WH265": {},
    "WM1301": {
        "binary_sensor": 9,
        "number": 1,
        "select": 5,
        "sensor": 21,
        "switch": 11,
    },
}


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _entities_by_appliance(
    hass: HomeAssistant, entry: MockConfigEntry, fake_hon: FakeHon
) -> dict[str, list[er.RegistryEntry]]:
    devices = dr.async_get(hass)
    entities = er.async_get(hass)
    result: dict[str, list[er.RegistryEntry]] = {}
    for appliance in fake_hon.appliances:
        key = f"{appliance.appliance_type}{appliance.appliance_model_id}"
        device = devices.async_get_device_by_identifier(
            ("hon", appliance.unique_id), entry.entry_id
        )
        result[key] = er.async_entries_for_device(entities, device.id) if device else []
    return result


async def test_entity_counts_per_appliance(
    hass: HomeAssistant, mock_hon: FakeHon, config_entry: MockConfigEntry
) -> None:
    await _setup(hass, config_entry)
    found = _entities_by_appliance(hass, config_entry, mock_hon)
    counts = {
        key: {
            domain: sum(1 for entity in entities if entity.domain == domain)
            for domain in sorted({entity.domain for entity in entities})
        }
        for key, entities in found.items()
    }
    assert counts == EXPECTED_COUNTS


async def test_every_non_light_entity_is_in_the_state_machine(
    hass: HomeAssistant, mock_hon: FakeHon, config_entry: MockConfigEntry
) -> None:
    await _setup(hass, config_entry)
    for entities in _entities_by_appliance(hass, config_entry, mock_hon).values():
        for entity in entities:
            if entity.domain == "light":
                continue
            state = hass.states.get(entity.entity_id)
            assert state is not None, entity.entity_id


async def test_every_sensor_state_is_valid(
    hass: HomeAssistant, mock_hon: FakeHon, config_entry: MockConfigEntry
) -> None:
    await _setup(hass, config_entry)
    sensors = [
        entity
        for entities in _entities_by_appliance(hass, config_entry, mock_hon).values()
        for entity in entities
        if entity.domain == "sensor"
    ]
    assert len(sensors) == 97
    for entity in sensors:
        state = hass.states.get(entity.entity_id)
        assert state is not None, entity.entity_id
        assert state.state != STATE_UNAVAILABLE, entity.entity_id


async def test_lights_report_state(
    hass: HomeAssistant, mock_hon: FakeHon, config_entry: MockConfigEntry
) -> None:
    await _setup(hass, config_entry)
    lights = [
        entity
        for entities in _entities_by_appliance(hass, config_entry, mock_hon).values()
        for entity in entities
        if entity.domain == "light"
    ]
    assert len(lights) == 2
    for entity in lights:
        state = hass.states.get(entity.entity_id)
        assert state is not None, entity.entity_id
        assert state.state != STATE_UNAVAILABLE, entity.entity_id


def _wash_cycle_entity_id(
    hass: HomeAssistant, entry: MockConfigEntry, fake_hon: FakeHon
) -> tuple[str, object]:
    appliance = next(
        item
        for item in fake_hon.appliances
        if item.appliance_type == "WM" and str(item.appliance_model_id) == "1301"
    )
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        "sensor", "hon", f"{appliance.unique_id}totalWashCycle"
    )
    assert entity_id is not None
    return entity_id, appliance.attributes["parameters"]["totalWashCycle"]


async def _notify_from_thread(
    hass: HomeAssistant, fake_hon: FakeHon
) -> list[BaseException]:
    notify = fake_hon.notify_function
    assert notify is not None
    errors: list[BaseException] = []

    def _call() -> None:
        try:
            notify(None)
        except BaseException as error:
            errors.append(error)

    thread = threading.Thread(target=_call)
    thread.start()
    await hass.async_add_executor_job(thread.join)
    await asyncio.sleep(0)
    await hass.async_block_till_done()
    return errors


async def test_notify_callback_is_thread_safe(
    hass: HomeAssistant,
    mock_hon: FakeHon,
    config_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    await _setup(hass, config_entry)
    entity_id, parameter = _wash_cycle_entity_id(hass, config_entry, mock_hon)
    assert hass.states.get(entity_id).state == "45"  # type: ignore[union-attr]

    parameter.value = "99"  # type: ignore[attr-defined]
    caplog.clear()
    errors = await _notify_from_thread(hass, mock_hon)

    assert errors == []
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert hass.states.get(entity_id).state == "99"  # type: ignore[union-attr]


async def test_empty_value_with_state_class_reports_zero(
    hass: HomeAssistant, mock_hon: FakeHon, config_entry: MockConfigEntry
) -> None:
    await _setup(hass, config_entry)
    entity_id, parameter = _wash_cycle_entity_id(hass, config_entry, mock_hon)

    parameter.value = ""  # type: ignore[attr-defined]
    await _notify_from_thread(hass, mock_hon)

    assert hass.states.get(entity_id).state == "0"  # type: ignore[union-attr]
