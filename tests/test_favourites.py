from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import FakeHon


def _favourite_entity_ids(hass: HomeAssistant, entry: MockConfigEntry) -> list[str]:
    return [
        entity.entity_id
        for entity in er.async_entries_for_config_entry(
            er.async_get(hass), entry.entry_id
        )
        if entity.unique_id.endswith("favourite_program")
    ]


async def test_favourites_become_a_select(
    hass: HomeAssistant, mock_hon: FakeHon, config_entry: MockConfigEntry
) -> None:
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    entity_ids = _favourite_entity_ids(hass, config_entry)
    assert len(entity_ids) == 1
    state = hass.states.get(entity_ids[0])
    assert state is not None
    assert state.attributes["options"] == ["Bed linen 60", "Kids"]


async def test_selecting_a_favourite_sets_the_program(
    hass: HomeAssistant, mock_hon: FakeHon, config_entry: MockConfigEntry
) -> None:
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    entity_id = _favourite_entity_ids(hass, config_entry)[0]

    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": entity_id, "option": "Kids"},
        blocking=True,
    )
    await hass.async_block_till_done()

    washer = next(a for a in mock_hon.appliances if a.appliance_type == "WM")
    assert washer.settings["startProgram.program"].value == "Kids"
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "Kids"
