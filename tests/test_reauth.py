from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util
from pyhon.exceptions import HonAuthenticationError
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.hon import AUTH_CHECK_INTERVAL
from custom_components.hon.const import DOMAIN

from .conftest import FakeHon


def _reauth_flows(hass: HomeAssistant) -> list[dict]:
    return [
        flow
        for flow in hass.config_entries.flow.async_progress()
        if flow["handler"] == DOMAIN and flow["context"]["source"] == SOURCE_REAUTH
    ]


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_rejected_login_at_setup_asks_to_sign_in_again(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    class _Factory:
        def __init__(self, **kwargs: object) -> None:
            pass

        async def create(self) -> FakeHon:
            raise HonAuthenticationError("Can't get session id")

    config_entry.add_to_hass(hass)
    with patch("custom_components.hon.Hon", _Factory):
        assert not await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    assert len(_reauth_flows(hass)) == 1


async def test_rejected_command_asks_to_sign_in_again(
    hass: HomeAssistant, mock_hon: FakeHon, config_entry: MockConfigEntry
) -> None:
    await _setup(hass, config_entry)
    switch = next(
        state.entity_id
        for state in hass.states.async_all("switch")
        if state.state != STATE_UNAVAILABLE
    )
    with (
        patch(
            "pyhon.commands.HonCommand.send",
            AsyncMock(side_effect=HonAuthenticationError("Can't login")),
        ),
        pytest.raises(HomeAssistantError) as err,
    ):
        await hass.services.async_call(
            "switch", "turn_off", {"entity_id": switch}, blocking=True
        )
    assert err.value.translation_key == "auth_failed"
    await hass.async_block_till_done()
    assert len(_reauth_flows(hass)) == 1


async def test_failed_background_login_asks_to_sign_in_again(
    hass: HomeAssistant, mock_hon: FakeHon, config_entry: MockConfigEntry
) -> None:
    await _setup(hass, config_entry)
    auth = mock_hon.api.auth
    auth.cognito_token = ""
    auth.error = HonAuthenticationError("Can't get session id")
    for tick in (1, 2):
        async_fire_time_changed(hass, dt_util.utcnow() + AUTH_CHECK_INTERVAL * tick)
        await hass.async_block_till_done()
    assert auth.logins == 1
    assert len(_reauth_flows(hass)) == 1


async def test_background_check_restores_a_lost_session(
    hass: HomeAssistant, mock_hon: FakeHon, config_entry: MockConfigEntry
) -> None:
    await _setup(hass, config_entry)
    auth = mock_hon.api.auth
    auth.cognito_token = ""
    async_fire_time_changed(hass, dt_util.utcnow() + AUTH_CHECK_INTERVAL)
    await hass.async_block_till_done()
    assert auth.logins == 1
    assert auth.cognito_token == "cognito"
    assert _reauth_flows(hass) == []


async def test_background_check_leaves_a_live_session_alone(
    hass: HomeAssistant, mock_hon: FakeHon, config_entry: MockConfigEntry
) -> None:
    await _setup(hass, config_entry)
    async_fire_time_changed(hass, dt_util.utcnow() + AUTH_CHECK_INTERVAL)
    await hass.async_block_till_done()
    assert mock_hon.api.auth.logins == 0


@pytest.mark.parametrize("error", ["invalid_auth", "cannot_connect"])
async def test_reauth_keeps_asking_while_login_fails(
    hass: HomeAssistant, mock_hon: FakeHon, config_entry: MockConfigEntry, error: str
) -> None:
    await _setup(hass, config_entry)
    result = await config_entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"
    with patch(
        "custom_components.hon.config_flow.async_check_login", return_value=error
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PASSWORD: "still-wrong"}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}
    assert config_entry.data[CONF_PASSWORD] == "secret"


async def test_reauth_stores_the_new_password_and_reloads(
    hass: HomeAssistant, mock_hon: FakeHon, config_entry: MockConfigEntry
) -> None:
    await _setup(hass, config_entry)
    result = await config_entry.start_reauth_flow(hass)
    with patch(
        "custom_components.hon.config_flow.async_check_login", return_value=""
    ) as check:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PASSWORD: "new-secret"}
        )
        await hass.async_block_till_done()
    check.assert_awaited_once_with(hass, "user@example.com", "new-secret")
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert config_entry.data[CONF_EMAIL] == "user@example.com"
    assert config_entry.data[CONF_PASSWORD] == "new-secret"
    assert config_entry.state is ConfigEntryState.LOADED
