"""Homebox Labels: print Homebox asset tags on a label printer integration.

Talks to the printer only through its public action (wp9529.print_label), so
the printer integration knows nothing about Homebox.
"""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_TOKEN, CONF_URL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .const import CONF_DEFAULT_ICON, CONF_PRINTER, DOMAIN, LAYOUT_FULL
from .coordinator import HomeboxItemsCoordinator
from .homebox import Homebox
from .services import async_setup_services

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS = [Platform.BUTTON, Platform.SELECT, Platform.SENSOR, Platform.TEXT]


@dataclass
class HomeboxLabelsData:
    homebox: Homebox
    items: HomeboxItemsCoordinator
    printer_device_id: str
    default_icon: str
    # UI form, shared by the text, select and button entities.
    form_asset_ids: str = ""
    form_icon: str = ""
    selected_item_id: str | None = None
    layout: str = LAYOUT_FULL  # set by the Tag layout select


type HomeboxLabelsConfigEntry = ConfigEntry[HomeboxLabelsData]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: HomeboxLabelsConfigEntry) -> bool:
    homebox = Homebox(async_get_clientsession(hass), entry.data[CONF_URL], entry.data[CONF_API_TOKEN])
    items = HomeboxItemsCoordinator(hass, entry, homebox)
    await items.async_config_entry_first_refresh()
    entry.runtime_data = HomeboxLabelsData(
        homebox=homebox,
        items=items,
        printer_device_id=entry.options.get(CONF_PRINTER, ""),
        default_icon=entry.options.get(CONF_DEFAULT_ICON) or "",
    )
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_reload(hass: HomeAssistant, entry: HomeboxLabelsConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: HomeboxLabelsConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
