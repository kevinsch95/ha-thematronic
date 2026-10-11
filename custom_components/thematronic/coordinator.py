"""Polling coordinator for the Thematronic portal."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ThematronicApi, ThematronicAuthError, ThematronicConnectionError
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN, MIN_SCAN_INTERVAL
from .parser import Signal

_LOGGER = logging.getLogger(__name__)

type ThematronicConfigEntry = ConfigEntry[ThematronicCoordinator]


class ThematronicCoordinator(DataUpdateCoordinator[dict[str, Signal]]):
    """Fetch all signals from the portal on an interval."""

    config_entry: ThematronicConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ThematronicConfigEntry, api: ThematronicApi
    ) -> None:
        """Set up the coordinator."""
        interval = max(
            MIN_SCAN_INTERVAL,
            int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
        )
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )
        self.api = api

    @property
    def device_id(self) -> int:
        """Controller id on the portal."""
        assert self.api.device_id is not None
        return self.api.device_id

    async def _async_update_data(self) -> dict[str, Signal]:
        try:
            return await self.api.fetch_signals()
        except ThematronicAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except ThematronicConnectionError as err:
            raise UpdateFailed(str(err)) from err
