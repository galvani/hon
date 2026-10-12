import json
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

URL_BASE = "/hon_static"
CARDS = ("hon-washer-card.js",)
_REGISTERED = "hon_frontend_registered"


async def async_register_cards(hass: HomeAssistant) -> None:
    if hass.data.get(_REGISTERED) or hass.http is None:
        return
    if "frontend" not in hass.config.components:
        return
    hass.data[_REGISTERED] = True
    root = Path(__file__).parent
    await hass.http.async_register_static_paths(
        [StaticPathConfig(URL_BASE, str(root / "www"), cache_headers=False)]
    )
    manifest = await hass.async_add_executor_job((root / "manifest.json").read_text)
    version = json.loads(manifest)["version"]
    for card in CARDS:
        add_extra_js_url(hass, f"{URL_BASE}/{card}?v={version}")
