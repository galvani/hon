import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol  # type: ignore[import-untyped]
from aiohttp import ClientError
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pyhon.connection.auth import HonAuth
from pyhon.connection.device import HonDevice
from pyhon.exceptions import HonAuthenticationError

from .const import DOMAIN, MOBILE_ID

_LOGGER = logging.getLogger(__name__)


async def async_check_login(hass: HomeAssistant, email: str, password: str) -> str:
    auth = HonAuth(async_get_clientsession(hass), email, password, HonDevice(MOBILE_ID))
    try:
        await auth.authenticate()
    except HonAuthenticationError:
        return "invalid_auth"
    except ClientError, TimeoutError:
        return "cannot_connect"
    return ""


class HonFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self) -> None:
        self._email: str | None = None
        self._password: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {vol.Required(CONF_EMAIL): str, vol.Required(CONF_PASSWORD): str}
                ),
            )

        self._email = user_input[CONF_EMAIL]
        self._password = user_input[CONF_PASSWORD]

        if self._email is None or self._password is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {vol.Required(CONF_EMAIL): str, vol.Required(CONF_PASSWORD): str}
                ),
            )

        # Check if already configured
        await self.async_set_unique_id(self._email)
        self._abort_if_unique_id_configured()

        if error := await async_check_login(self.hass, self._email, self._password):
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {vol.Required(CONF_EMAIL): str, vol.Required(CONF_PASSWORD): str}
                ),
                errors={"base": error},
            )

        return self.async_create_entry(
            title=self._email,
            data={
                CONF_EMAIL: self._email,
                CONF_PASSWORD: self._password,
            },
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> FlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            password = user_input[CONF_PASSWORD]
            if not (
                error := await async_check_login(
                    self.hass, entry.data[CONF_EMAIL], password
                )
            ):
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PASSWORD: password}
                )
            errors["base"] = error
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            description_placeholders={"email": entry.data[CONF_EMAIL]},
            errors=errors,
        )

    async def async_step_import(self, user_input: dict[str, str]) -> FlowResult:
        return await self.async_step_user(user_input)
