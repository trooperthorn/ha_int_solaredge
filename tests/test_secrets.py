"""Tests that no credential reaches a log line, an error message, or a request URL.

The core ``solaredge`` integration (V1 API) wrote its site API key to the Home
Assistant log on 2026-10-09: the key travels in the query string, aiohttp's
``ClientResponseError`` prints the full URL, and the generic coordinator logs
``str(err)``. These tests pin the properties that keep this integration clear
of that path for both access types, under the failures the coordinator maps.
"""

from __future__ import annotations

from datetime import timedelta
import logging
import time

from aiohttp import ClientConnectionError
from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import CONF_API_KEY, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.solaredge_v2.const import (
    AUTH_TYPE_API_KEY,
    AUTH_TYPE_OAUTH,
    CONF_AUTH_TYPE,
    CONF_SITE_ID,
    DOMAIN,
    OAUTH2_TOKEN,
)

from .conftest import CLIENT_SECRET, SITE_ID, MockApi

POWER = "sensor.example_home_current_power"
COORDINATOR_LOGGER = "custom_components.solaredge_v2"

# Sentinels that cannot occur in any log line by accident.
API_KEY = "fleet-key-3f9c1a7e5b2d"
ACCESS_TOKEN = "site-access-token-8e4d2c6a1f"
REFRESH_TOKEN = "site-refresh-token-5a7b9c3d1e"
OAUTH_SECRETS = (ACCESS_TOKEN, REFRESH_TOKEN, CLIENT_SECRET)


def _api_key_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Example Home",
        unique_id=str(SITE_ID),
        data={CONF_AUTH_TYPE: AUTH_TYPE_API_KEY, CONF_API_KEY: API_KEY, CONF_SITE_ID: SITE_ID},
    )
    entry.add_to_hass(hass)
    return entry


def _oauth_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Example Home",
        unique_id=str(SITE_ID),
        data={
            CONF_AUTH_TYPE: AUTH_TYPE_OAUTH,
            CONF_SITE_ID: SITE_ID,
            "auth_implementation": DOMAIN,
            "token": {
                "access_token": ACCESS_TOKEN,
                "refresh_token": REFRESH_TOKEN,
                "token_type": "Bearer",
                "expires_in": 86400,
                "expires_at": time.time() + 86400,
            },
        },
    )
    entry.add_to_hass(hass)
    return entry


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def _tick(hass: HomeAssistant, freezer: FrozenDateTimeFactory, minutes: int = 60) -> None:
    freezer.tick(timedelta(minutes=minutes))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


def _assert_absent(secrets: tuple[str, ...], *texts: str) -> None:
    for text in texts:
        for secret in secrets:
            assert secret not in text


def _coordinator_errors(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [
        r
        for r in caplog.records
        if r.levelno >= logging.ERROR and r.name.startswith(COORDINATOR_LOGGER)
    ]


def _fail_overview(mock_api: MockApi, kind: str) -> None:
    """Make the overview call fail with the 503 the core integration logged, or at the transport."""
    if kind == "503":
        mock_api(overview=503)
    else:
        mock_api(overview=ClientConnectionError("Cannot connect"))


@pytest.mark.parametrize("kind", ["503", "connection"])
async def test_api_key_never_logged(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
    mock_api: MockApi,
    aioclient_mock: AiohttpClientMocker,
    kind: str,
) -> None:
    """A Fleet Access key stays out of every log line, error string, and URL on failure."""
    caplog.set_level(logging.DEBUG)
    entry = _api_key_entry(hass)
    await _setup(hass, entry)
    coordinator = entry.runtime_data
    assert coordinator.name == f"{DOMAIN} {SITE_ID}"

    _fail_overview(mock_api, kind)
    await _tick(hass, freezer)
    await _tick(hass, freezer)
    assert hass.states.get(POWER).state == STATE_UNAVAILABLE
    assert coordinator.last_exception is not None

    _assert_absent((API_KEY,), caplog.text, str(coordinator.last_exception))
    for _method, url, _data, headers in aioclient_mock.mock_calls:
        assert API_KEY not in str(url)
        assert headers["X-API-Key"] == API_KEY

    errors = _coordinator_errors(caplog)
    assert len(errors) == 1
    assert f"{DOMAIN} {SITE_ID}" in errors[0].getMessage()


@pytest.mark.parametrize("kind", ["503", "connection"])
async def test_oauth_token_never_logged(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
    mock_api: MockApi,
    aioclient_mock: AiohttpClientMocker,
    credentials: None,
    kind: str,
) -> None:
    """A Site Access token stays out of every log line, error string, and URL on failure."""
    caplog.set_level(logging.DEBUG)
    entry = _oauth_entry(hass)
    await _setup(hass, entry)
    coordinator = entry.runtime_data

    _fail_overview(mock_api, kind)
    await _tick(hass, freezer)
    await _tick(hass, freezer)
    assert hass.states.get(POWER).state == STATE_UNAVAILABLE
    assert coordinator.last_exception is not None

    _assert_absent(OAUTH_SECRETS, caplog.text, str(coordinator.last_exception))
    for _method, url, _data, headers in aioclient_mock.mock_calls:
        assert ACCESS_TOKEN not in str(url)
        assert headers["Authorization"] == f"Bearer {ACCESS_TOKEN}"
    assert len(_coordinator_errors(caplog)) == 1


@pytest.mark.parametrize("kind", ["503", "connection"])
async def test_oauth_refresh_failure_never_logged(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
    mock_api: MockApi,
    aioclient_mock: AiohttpClientMocker,
    credentials: None,
    kind: str,
) -> None:
    """A failed token refresh logs neither the refresh token nor the client secret.

    The refresh request carries both in its JSON body; the error that comes back
    is an aiohttp ``ClientResponseError`` whose string names only the token URL.
    """
    caplog.set_level(logging.DEBUG)
    entry = _oauth_entry(hass)
    await _setup(hass, entry)
    coordinator = entry.runtime_data

    hass.config_entries.async_update_entry(
        entry, data={**entry.data, "token": {**entry.data["token"], "expires_at": time.time() - 10}}
    )
    if kind == "503":
        aioclient_mock.post(OAUTH2_TOKEN, status=503, json={"error": "temporarily_unavailable"})
    else:
        aioclient_mock.post(OAUTH2_TOKEN, exc=ClientConnectionError("Cannot connect"))
    await _tick(hass, freezer)
    await _tick(hass, freezer)
    assert hass.states.get(POWER).state == STATE_UNAVAILABLE
    assert coordinator.last_exception is not None

    refresh = [c for c in aioclient_mock.mock_calls if c[0] == "POST"]
    assert refresh and refresh[0][2]["refresh_token"] == REFRESH_TOKEN
    _assert_absent(OAUTH_SECRETS, caplog.text, str(coordinator.last_exception))
    assert len(_coordinator_errors(caplog)) == 1
