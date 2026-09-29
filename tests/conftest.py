"""Fixtures for the SolarEdge Monitoring API v2 tests."""

from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path
import time
from typing import Any

from homeassistant.components.application_credentials import (
    ClientCredential,
    async_import_client_credential,
)
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.solaredge_v2.api import BASE_URL
from custom_components.solaredge_v2.const import (
    AUTH_TYPE_API_KEY,
    AUTH_TYPE_OAUTH,
    CONF_AUTH_TYPE,
    CONF_DEVICE_TELEMETRY,
    CONF_SITE_ID,
    DOMAIN,
)

SITE_ID = 1234567
SITE = f"{BASE_URL}/sites/{SITE_ID}"
FIXTURES = Path(__file__).parent / "fixtures"
CLIENT_ID = "client-id"
CLIENT_SECRET = "client-secret"


def load(name: str) -> Any:
    """Load a JSON fixture."""
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Allow custom_components to load in every test."""


type MockApi = Callable[..., None]


@pytest.fixture
def mock_api(aioclient_mock: AiohttpClientMocker) -> MockApi:
    """Register every endpoint; keyword arguments replace one route's status or body."""

    def _register(
        headers: dict[str, str] | None = None, **overrides: int | dict[str, Any] | list[Any]
    ) -> None:
        aioclient_mock.clear_requests()
        routes: dict[str, tuple[str, Any]] = {
            "sites": (f"{BASE_URL}/sites", load("sites.json")),
            "site": (SITE, load("site.json")),
            "overview": (f"{SITE}/overview", load("overview.json")),
            "power": (f"{SITE}/power", load("power.json")),
            "energy": (f"{SITE}/energy", load("energy_total.json")),
            "alerts": (f"{SITE}/alerts", load("alerts.json")),
            "devices": (f"{SITE}/devices", load("devices.json")),
            "inverters": (f"{SITE}/inverters/telemetry", load("inverters_telemetry.json")),
            "meters": (f"{SITE}/meters/telemetry", load("meters_telemetry.json")),
            "storage": (f"{SITE}/storage/telemetry", load("storage_telemetry.json")),
        }
        for name, (url, body) in routes.items():
            override = overrides.get(name)
            if isinstance(override, int):
                aioclient_mock.get(
                    url,
                    status=override,
                    json={"title": "error", "detail": "mocked"},
                    headers=headers,
                )
            else:
                aioclient_mock.get(url, json=body if override is None else override)

    _register()
    return _register


@pytest.fixture
def api_key_entry(hass: HomeAssistant) -> MockConfigEntry:
    """A Fleet Access entry with device telemetry on."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Example Home",
        unique_id=str(SITE_ID),
        data={CONF_AUTH_TYPE: AUTH_TYPE_API_KEY, CONF_API_KEY: "test-key", CONF_SITE_ID: SITE_ID},
        options={CONF_DEVICE_TELEMETRY: True},
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
async def credentials(hass: HomeAssistant) -> None:
    """Register application credentials for the OAuth path."""
    assert await async_setup_component(hass, "application_credentials", {})
    await async_import_client_credential(
        hass, DOMAIN, ClientCredential(CLIENT_ID, CLIENT_SECRET), DOMAIN
    )


@pytest.fixture
def oauth_entry(hass: HomeAssistant, credentials: None) -> MockConfigEntry:
    """A Site Access entry with a valid token."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Example Home",
        unique_id=str(SITE_ID),
        data={
            CONF_AUTH_TYPE: AUTH_TYPE_OAUTH,
            CONF_SITE_ID: SITE_ID,
            "auth_implementation": DOMAIN,
            "token": {
                "access_token": "access",
                "refresh_token": "refresh",
                "token_type": "Bearer",
                "expires_in": 7200,
                "expires_at": time.time() + 7200,
            },
        },
    )
    entry.add_to_hass(hass)
    return entry
