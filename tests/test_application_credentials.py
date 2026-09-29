"""Tests for the application credentials platform."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from custom_components.solaredge_v2.application_credentials import (
    async_get_description_placeholders,
)


async def test_description_placeholders(hass: HomeAssistant) -> None:
    """The credentials dialog links the developer console and the redirect URL."""
    placeholders = await async_get_description_placeholders(hass)
    assert placeholders["developer_console"] == "https://developer.solaredge.com"
    assert placeholders["redirect_url"] == "https://my.home-assistant.io/redirect/oauth"
