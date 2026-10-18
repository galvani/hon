import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import voluptuous as vol  # type: ignore[import-untyped]
from aiohttp import ClientError
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers import config_validation as cv, aiohttp_client
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from pyhon import Hon
from pyhon.exceptions import HonAuthenticationError

from .const import DOMAIN, PLATFORMS, MOBILE_ID, CONF_REFRESH_TOKEN
from .frontend import async_register_cards
from .recent import async_setup_recent

_LOGGER = logging.getLogger(__name__)

AUTH_CHECK_INTERVAL = timedelta(minutes=5)

HON_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema(vol.All(cv.ensure_list, [HON_SCHEMA]))},
    extra=vol.ALLOW_EXTRA,
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = aiohttp_client.async_get_clientsession(hass)
    if (config_dir := hass.config.config_dir) is None:
        raise ValueError("Missing Config Dir")
    try:
        hon = await Hon(
            email=entry.data[CONF_EMAIL],
            password=entry.data[CONF_PASSWORD],
            mobile_id=MOBILE_ID,
            session=session,
            test_data_path=Path(config_dir),
            refresh_token=entry.data.get(CONF_REFRESH_TOKEN, ""),
        ).create()
    except HonAuthenticationError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except (ClientError, TimeoutError) as err:
        raise ConfigEntryNotReady(str(err)) from err

    # Save the new refresh token
    hass.config_entries.async_update_entry(
        entry, data={**entry.data, CONF_REFRESH_TOKEN: hon.api.auth.refresh_token}
    )

    coordinator: DataUpdateCoordinator[dict[str, Any]] = DataUpdateCoordinator(
        hass, _LOGGER, name=DOMAIN
    )

    def _notify(data: Any) -> None:
        hass.loop.call_soon_threadsafe(coordinator.async_set_updated_data, data)

    hon.subscribe_updates(_notify)

    # pyhon clears its tokens before a login, so empty tokens mean its last re-login failed.
    async def _check_auth(_now: datetime) -> None:
        if hon.api.auth.cognito_token or any(
            entry.async_get_active_flows(hass, {SOURCE_REAUTH})
        ):
            return
        try:
            await hon.api.auth.authenticate()
        except HonAuthenticationError:
            _LOGGER.warning("hOn rejected the stored credentials")
            entry.async_start_reauth(hass)
        except (ClientError, TimeoutError) as err:
            _LOGGER.debug("hOn login retry failed: %s", err)

    entry.async_on_unload(
        async_track_time_interval(hass, _check_auth, AUTH_CHECK_INTERVAL)
    )

    hass.data.setdefault(DOMAIN, {})
    recent = await async_setup_recent(hass, entry.entry_id, hon.appliances, coordinator)
    hass.data[DOMAIN][entry.unique_id] = {
        "hon": hon,
        "coordinator": coordinator,
        "recent": recent,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_register_cards(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    refresh_token = hass.data[DOMAIN][entry.unique_id]["hon"].api.auth.refresh_token

    hass.config_entries.async_update_entry(
        entry, data={**entry.data, CONF_REFRESH_TOKEN: refresh_token}
    )
    unload = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload:
        hass.data[DOMAIN].pop(entry.unique_id, None)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN, None)
    return unload
