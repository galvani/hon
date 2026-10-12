from hashlib import sha1
from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN

URL_BASE = "/hon_static"
CARDS = ("hon-washer-card.js",)
_REGISTERED = "hon_frontend_registered"


async def async_register_cards(hass: HomeAssistant) -> None:
    if hass.data.get(_REGISTERED):
        return
    hass.data[_REGISTERED] = True
    websocket_api.async_register_command(hass, websocket_recent_programs)
    if hass.http is None or "frontend" not in hass.config.components:
        return
    root = Path(__file__).parent
    await hass.http.async_register_static_paths(
        [StaticPathConfig(URL_BASE, str(root / "www"), cache_headers=False)]
    )
    for card in CARDS:
        content = await hass.async_add_executor_job((root / "www" / card).read_bytes)
        add_extra_js_url(hass, f"{URL_BASE}/{card}?v={sha1(content).hexdigest()[:10]}")


RECENT_PROGRAMS_SCHEMA: dict[Any, Any] = {
    vol.Required("type"): "hon/recent_programs",
    vol.Required("device_id"): str,
}


@websocket_api.websocket_command(RECENT_PROGRAMS_SCHEMA)
@callback
def websocket_recent_programs(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    device = dr.async_get(hass).async_get(msg["device_id"])
    identifiers = (
        {value for domain, value in device.identifiers if domain == DOMAIN}
        if device is not None
        else set()
    )
    for data in hass.data.get(DOMAIN, {}).values():
        for appliance in data["hon"].appliances:
            if appliance.unique_id in identifiers:
                connection.send_result(
                    msg["id"], {"programs": data["recent"].get(appliance)}
                )
                return
    connection.send_error(msg["id"], "not_found", "No hOn appliance for this device")
