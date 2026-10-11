"""Diagnostics download for Thematronic (credentials redacted)."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .coordinator import ThematronicConfigEntry

TO_REDACT = {CONF_USERNAME, CONF_PASSWORD}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ThematronicConfigEntry
) -> dict[str, Any]:
    """Return the raw portal signals for troubleshooting."""
    coordinator = entry.runtime_data
    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "signals": {
            name: asdict(signal) for name, signal in (coordinator.data or {}).items()
        },
    }
