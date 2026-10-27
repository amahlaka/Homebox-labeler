"""Config flow for Homebox Labels: Homebox connection plus which printer to use."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_API_TOKEN, CONF_URL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    DeviceSelector,
    DeviceSelectorConfig,
    IconSelector,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import CONF_DEFAULT_ICON, CONF_PRINTER, DOMAIN, PRINTER_DOMAIN
from .homebox import Homebox, HomeboxAuthError, HomeboxError

PRINTER_SELECTOR = DeviceSelector(DeviceSelectorConfig(integration=PRINTER_DOMAIN))

USER_SCHEMA = vol.Schema({
    vol.Required(CONF_URL): TextSelector(TextSelectorConfig(type=TextSelectorType.URL)),
    vol.Required(CONF_API_TOKEN): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
    vol.Required(CONF_PRINTER): PRINTER_SELECTOR,
})

OPTIONS_SCHEMA = vol.Schema({
    vol.Required(CONF_PRINTER): PRINTER_SELECTOR,
    vol.Optional(CONF_DEFAULT_ICON): IconSelector(),
})


async def _check_homebox(hass: HomeAssistant, url: str, token: str) -> str | None:
    """Error key, or None when the URL and token work."""
    hb = Homebox(async_get_clientsession(hass), url, token)
    try:
        await hb.status()
        await hb.whoami()
    except HomeboxAuthError:
        return "invalid_auth"
    except HomeboxError:
        return "cannot_connect"
    return None


class HomeboxLabelsConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            url = user_input[CONF_URL].rstrip("/")
            await self.async_set_unique_id(url)
            self._abort_if_unique_id_configured()
            if not (error := await _check_homebox(self.hass, url, user_input[CONF_API_TOKEN])):
                # Plain "Homebox" keeps entity IDs short (text.homebox_asset_ids);
                # a second connection gets HA's automatic _2 suffix.
                return self.async_create_entry(
                    title="Homebox",
                    data={CONF_URL: url, CONF_API_TOKEN: user_input[CONF_API_TOKEN]},
                    options={CONF_PRINTER: user_input[CONF_PRINTER]})
            errors["base"] = error
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input or {}),
            errors=errors,
            description_placeholders={"example_url": "https://homebox.example.com"})

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Change the Homebox URL or token."""
        entry = self._get_reconfigure_entry()
        schema = vol.Schema({k: v for k, v in USER_SCHEMA.schema.items() if k != CONF_PRINTER})
        errors: dict[str, str] = {}
        if user_input is not None:
            url = user_input[CONF_URL].rstrip("/")
            if not (error := await _check_homebox(self.hass, url, user_input[CONF_API_TOKEN])):
                return self.async_update_reload_and_abort(
                    entry, unique_id=url, data={CONF_URL: url, CONF_API_TOKEN: user_input[CONF_API_TOKEN]})
            errors["base"] = error
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or {CONF_URL: entry.data[CONF_URL]}),
            errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return HomeboxLabelsOptionsFlow()


class HomeboxLabelsOptionsFlow(OptionsFlow):
    """Which printer to use and the default tag icon."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(OPTIONS_SCHEMA, self.config_entry.options))
