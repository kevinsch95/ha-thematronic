"""Thematronic JBR-1 pellet boiler controller, via the jbr1.thematronic.cz portal."""

from __future__ import annotations

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import ThematronicApi
from .const import CONF_DEVICE_ID
from .coordinator import ThematronicConfigEntry, ThematronicCoordinator

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ThematronicConfigEntry) -> bool:
    """Set up Thematronic from a config entry."""
    # A dedicated session so the portal's cookies don't mix with other integrations.
    session = async_create_clientsession(hass)
    api = ThematronicApi(
        session,
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        device_id=entry.data.get(CONF_DEVICE_ID),
    )
    coordinator = ThematronicCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ThematronicConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_options_updated(hass: HomeAssistant, entry: ThematronicConfigEntry) -> None:
    """Reload when the user changes options (interval, raw signals)."""
    await hass.config_entries.async_reload(entry.entry_id)
