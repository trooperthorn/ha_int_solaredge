"""Tests for the config, reauth, reconfigure, and options flows."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import config_entry_oauth2_flow
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.solaredge_v2.api import BASE_URL
from custom_components.solaredge_v2.const import (
    AUTH_TYPE_API_KEY,
    AUTH_TYPE_OAUTH,
    CONF_AUTH_TYPE,
    CONF_DEVICE_TELEMETRY,
    CONF_SCAN_INTERVAL_MINUTES,
    CONF_SITE_ID,
    DOMAIN,
    OAUTH2_AUTHORIZE,
    OAUTH2_TOKEN,
)

from .conftest import CLIENT_ID, CLIENT_SECRET, SITE, SITE_ID, MockApi

REDIRECT = "https://example.com/auth/external/callback"
TOKEN = {"access_token": "new-access", "refresh_token": "new-refresh", "token_type": "Bearer", "expires_in": 7200}


@pytest.fixture(autouse=True)
def no_setup() -> Any:
    """Keep entry creation from setting the integration up."""
    with patch("custom_components.solaredge_v2.async_setup_entry", return_value=True) as mock:
        yield mock


async def _start(hass: HomeAssistant, choice: str) -> dict[str, Any]:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.MENU
    return await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": choice})


async def test_api_key_multiple_sites(hass: HomeAssistant, mock_api: MockApi) -> None:
    """A key that reads two sites asks which one."""
    result = await _start(hass, "api_key")
    assert result["step_id"] == "api_key"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_API_KEY: " test-key "})
    assert result["step_id"] == "select_site"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_SITE_ID: str(SITE_ID)})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Example Home"
    assert result["data"] == {CONF_AUTH_TYPE: AUTH_TYPE_API_KEY, CONF_API_KEY: "test-key", CONF_SITE_ID: SITE_ID}
    assert result["result"].unique_id == str(SITE_ID)


async def test_api_key_single_site(hass: HomeAssistant, mock_api: MockApi) -> None:
    """A key that reads one site creates the entry directly."""
    mock_api(sites={"sites": {"count": 1, "site": [{"siteId": SITE_ID, "name": "Only"}]}})
    result = await _start(hass, "api_key")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_API_KEY: "test-key"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Only"


@pytest.mark.parametrize(
    ("override", "error"),
    [
        ({"sites": 401}, "invalid_auth"),
        ({"sites": 403}, "site_forbidden"),
        ({"sites": 500}, "unknown"),
        ({"sites": {"sites": {"count": 0, "site": []}}}, "no_sites"),
    ],
)
async def test_api_key_errors_recover(
    hass: HomeAssistant, mock_api: MockApi, override: dict[str, Any], error: str
) -> None:
    """Each failure shows an error and the flow still completes afterwards."""
    mock_api(**override)
    result = await _start(hass, "api_key")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_API_KEY: "bad"})
    assert result["errors"] == {"base": error}
    mock_api()
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_API_KEY: "test-key"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_SITE_ID: str(SITE_ID)})
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_api_key_credit_and_connection_errors(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Credit exhaustion and transport failures have their own messages."""
    aioclient_mock.get(f"{BASE_URL}/sites", status=429, headers={"x-ratelimit-remaining-minute": "5"}, json={})
    result = await _start(hass, "api_key")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_API_KEY: "k"})
    assert result["errors"] == {"base": "credit_limit"}
    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{BASE_URL}/sites", exc=TimeoutError)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_API_KEY: "k"})
    assert result["errors"] == {"base": "cannot_connect"}


async def test_api_key_duplicate(hass: HomeAssistant, mock_api: MockApi, api_key_entry: MockConfigEntry) -> None:
    """The same site cannot be added twice."""
    result = await _start(hass, "api_key")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_API_KEY: "test-key"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_SITE_ID: str(SITE_ID)})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_select_site_without_key(hass: HomeAssistant) -> None:
    """Reaching the site picker without a validated key goes back to the key form."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    flow = hass.config_entries.flow._progress[result["flow_id"]]
    result = await flow.async_step_select_site()
    assert result["step_id"] == "api_key"


async def _oauth_to_callback(
    hass: HomeAssistant, hass_client_no_auth: ClientSessionGenerator, result: dict[str, Any]
) -> None:
    state = config_entry_oauth2_flow._encode_jwt(hass, {"flow_id": result["flow_id"], "redirect_uri": REDIRECT})
    assert result["type"] is FlowResultType.EXTERNAL_STEP
    assert result["url"].startswith(f"{OAUTH2_AUTHORIZE}?")
    assert f"client_id={CLIENT_ID}" in result["url"]
    assert "scope=SITE_DATA+DEVICE_DATA" in result["url"]
    assert "access_duration=24" in result["url"]
    client = await hass_client_no_auth()
    resp = await client.get(f"/auth/external/callback?code=abcd&state={state}")
    assert resp.status == 200


@pytest.mark.usefixtures("current_request_with_host", "credentials")
async def test_oauth_full_flow(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
    mock_api: MockApi,
) -> None:
    """OAuth, then the Site ID, creates a Site Access entry."""
    result = await _start(hass, "oauth")
    await _oauth_to_callback(hass, hass_client_no_auth, result)
    aioclient_mock.post(OAUTH2_TOKEN, json=TOKEN)
    result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["step_id"] == "site"

    token_call = next(c for c in aioclient_mock.mock_calls if c[0] == "POST")
    assert token_call[2]["grant_type"] == "authorization_code"
    assert token_call[2]["client_secret"] == CLIENT_SECRET

    mock_api(site=403)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_SITE_ID: SITE_ID})
    assert result["errors"] == {"base": "site_forbidden"}
    mock_api()
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_SITE_ID: SITE_ID})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_AUTH_TYPE] == AUTH_TYPE_OAUTH
    assert result["data"][CONF_SITE_ID] == SITE_ID
    assert result["data"]["token"]["access_token"] == "new-access"
    site_call = [c for c in aioclient_mock.mock_calls if str(c[1]) == SITE][-1]
    assert site_call[3]["Authorization"] == "Bearer new-access"


@pytest.mark.usefixtures("current_request_with_host")
async def test_oauth_reauth(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
    mock_api: MockApi,
    oauth_entry: MockConfigEntry,
) -> None:
    """Reauth for a Site Access entry replaces the token after checking the site."""
    result = await oauth_entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    await _oauth_to_callback(hass, hass_client_no_auth, result)
    aioclient_mock.post(OAUTH2_TOKEN, json=TOKEN)
    result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert oauth_entry.data["token"]["access_token"] == "new-access"


@pytest.mark.usefixtures("current_request_with_host")
async def test_oauth_reconfigure_wrong_site(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
    mock_api: MockApi,
    oauth_entry: MockConfigEntry,
) -> None:
    """A new grant that cannot read the configured site aborts without saving."""
    result = await oauth_entry.start_reconfigure_flow(hass)
    assert result["step_id"] == "reconfigure"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    await _oauth_to_callback(hass, hass_client_no_auth, result)
    aioclient_mock.post(OAUTH2_TOKEN, json=TOKEN)
    mock_api(site=403)
    aioclient_mock.post(OAUTH2_TOKEN, json=TOKEN)
    result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "oauth_site_forbidden"
    assert oauth_entry.data["token"]["access_token"] == "access"


async def test_api_key_reauth(hass: HomeAssistant, mock_api: MockApi, api_key_entry: MockConfigEntry) -> None:
    """Reauth for a Fleet Access entry validates and stores the new key."""
    result = await api_key_entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"
    mock_api(site=401)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_API_KEY: "bad"})
    assert result["errors"] == {"base": "invalid_auth"}
    mock_api()
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_API_KEY: "new-key"})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert api_key_entry.data[CONF_API_KEY] == "new-key"


async def test_api_key_reconfigure(hass: HomeAssistant, mock_api: MockApi, api_key_entry: MockConfigEntry) -> None:
    """Reconfigure replaces the key of a Fleet Access entry."""
    result = await api_key_entry.start_reconfigure_flow(hass)
    assert result["step_id"] == "reconfigure"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_API_KEY: "other-key"})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert api_key_entry.data[CONF_API_KEY] == "other-key"


async def test_options(hass: HomeAssistant, api_key_entry: MockConfigEntry) -> None:
    """Options store the interval and the telemetry switch."""
    result = await hass.config_entries.options.async_init(api_key_entry.entry_id)
    assert result["step_id"] == "init"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL_MINUTES: 30.0, CONF_DEVICE_TELEMETRY: False}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert api_key_entry.options == {CONF_SCAN_INTERVAL_MINUTES: 30, CONF_DEVICE_TELEMETRY: False}


async def test_missing_credentials(hass: HomeAssistant) -> None:
    """Choosing OAuth with no application credentials aborts with guidance."""
    result = await _start(hass, "oauth")
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "missing_credentials"
