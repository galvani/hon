from __future__ import annotations

import json
from collections.abc import Callable, Generator
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from pyhon.appliance import HonAppliance
from pyhon.connection.api import TestAPI
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hon.const import DOMAIN

FIXTURES = Path(__file__).parent / "fixtures" / "hon-test-data" / "test_data"
FAVOURITES = Path(__file__).parent / "fixtures" / "favourites"


class FixtureAPI(TestAPI):
    async def load_favourites(self, appliance: HonAppliance) -> list[dict[str, Any]]:
        name = f"{appliance.appliance_type}_{appliance.appliance_model_id}".lower()
        if not (path := FAVOURITES / f"{name}.json").exists():
            return []
        favourites: list[dict[str, Any]] = json.loads(path.read_text())
        return favourites


class FakeHon:
    def __init__(self, appliances: list[HonAppliance]) -> None:
        self.appliances = appliances
        self.api = SimpleNamespace(auth=SimpleNamespace(refresh_token="refresh"))
        self.notify_function: Callable[[Any], None] | None = None

    def subscribe_updates(self, notify_function: Callable[[Any], None]) -> None:
        self.notify_function = notify_function


async def load_appliances(path: Path = FIXTURES) -> list[HonAppliance]:
    api = FixtureAPI(path)
    appliances: list[HonAppliance] = []
    for index, data in enumerate(
        sorted(await api.load_appliances(), key=lambda item: item["id"])
    ):
        data["macAddress"] = f"00-00-00-00-00-{index:02d}"
        appliance = await HonAppliance(api, data).create()
        await appliance.load_commands()
        await appliance.load_attributes()
        await appliance.load_statistics()
        appliances.append(appliance)
    return appliances


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    return None


@pytest.fixture
async def fake_hon() -> FakeHon:
    return FakeHon(await load_appliances())


@pytest.fixture
def mock_hon(fake_hon: FakeHon) -> Generator[FakeHon]:
    class _Factory:
        def __init__(self, **kwargs: Any) -> None:
            pass

        async def create(self) -> FakeHon:
            return fake_hon

    with patch("custom_components.hon.Hon", _Factory):
        yield fake_hon


@pytest.fixture
def config_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id="hon-test",
        data={CONF_EMAIL: "user@example.com", CONF_PASSWORD: "secret"},
    )
