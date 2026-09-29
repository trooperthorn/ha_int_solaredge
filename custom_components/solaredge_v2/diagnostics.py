"""Diagnostics for the SolarEdge Monitoring API v2 integration."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_API_KEY, CONF_TOKEN
from homeassistant.core import HomeAssistant

from . import SolarEdgeConfigEntry

TO_REDACT = {CONF_API_KEY, CONF_TOKEN, "access_token", "refresh_token"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SolarEdgeConfigEntry
) -> dict[str, Any]:
    """Return the entry settings and the last fetched data, without secrets."""
    coordinator = entry.runtime_data
    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "device_telemetry_denied": coordinator.scope_denied,
        "last_update_success": coordinator.last_update_success,
        "data": asdict(coordinator.data),
    }
