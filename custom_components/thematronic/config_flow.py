"""Config flow for Thematronic: e-mail + password of the jbr1.thematronic.cz account."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import ThematronicApi, ThematronicAuthError, ThematronicConnectionError
from .const import (
    CONF_DEVICE_ID,
    CONF_RAW_SIGNALS,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)
from .coordinator import ThematronicConfigEntry

_LOGGER = logging.getLogger(__name__)

CREDENTIALS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): TextSelector(
            TextSelectorConfig(type=TextSelectorType.EMAIL, autocomplete="username")
        ),
        vol.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.PASSWORD, autocomplete="current-password"
            )
        ),
    }
)


async def _validate(hass: HomeAssistant, username: str, password: str) -> int:
    """Sign in once; return the controller id. Raises on failure."""
    api = ThematronicApi(async_create_clientsession(hass), username, password)
    await api.login()
    await api.fetch_signals()
    assert api.device_id is not None
    return api.device_id


class ThematronicConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for portal credentials."""
        errors: dict[str, str] = {}
        if user_input is not None:
            username = user_input[CONF_USERNAME].strip()
            try:
                device_id = await _validate(
                    self.hass, username, user_input[CONF_PASSWORD]
                )
            except ThematronicAuthError:
                errors["base"] = "invalid_auth"
            except ThematronicConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during Thematronic login")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(str(device_id))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Thematronic JBR-1 ({device_id})",
                    data={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_DEVICE_ID: device_id,
                    },
                )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                CREDENTIALS_SCHEMA, user_input
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start re-authentication after the password changed."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for new credentials."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            username = user_input[CONF_USERNAME].strip()
            try:
                device_id = await _validate(
                    self.hass, username, user_input[CONF_PASSWORD]
                )
            except ThematronicAuthError:
                errors["base"] = "invalid_auth"
            except ThematronicConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during Thematronic login")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(str(device_id))
                self._abort_if_unique_id_mismatch(reason="wrong_account")
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=self.add_suggested_values_to_schema(
                CREDENTIALS_SCHEMA, {CONF_USERNAME: entry.data[CONF_USERNAME]}
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ThematronicConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return ThematronicOptionsFlow()


class ThematronicOptionsFlow(OptionsFlow):
    """Polling interval and raw-signal sensors."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the options form."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=3600)),
                vol.Required(
                    CONF_RAW_SIGNALS, default=options.get(CONF_RAW_SIGNALS, False)
                ): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
