"""The homebox_labels.print_tags action."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_ASSET_IDS,
    ATTR_CONFIG_ENTRY_ID,
    ATTR_COPIES,
    ATTR_DRY_RUN,
    ATTR_ICON,
    ATTR_LAYOUT,
    ATTR_SEARCH,
    DOMAIN,
    LAYOUTS,
    SERVICE_PRINT_TAGS,
)
from .tags import async_find_items, async_print_items

PRINT_TAGS_SCHEMA = vol.Schema({
    vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
    vol.Optional(ATTR_ASSET_IDS, default=[]): vol.All(cv.ensure_list_csv, [cv.string]),
    vol.Optional(ATTR_SEARCH): vol.Any(None, cv.string),
    # Empty icon = use the configured default; omit the field the same way.
    vol.Optional(ATTR_ICON): vol.Any(None, "", cv.icon),
    vol.Optional(ATTR_COPIES, default=1): vol.All(vol.Coerce(int), vol.Range(min=1, max=50)),
    vol.Optional(ATTR_DRY_RUN, default=False): cv.boolean,
    # Empty = use the Tag layout setting.
    vol.Optional(ATTR_LAYOUT): vol.Any(None, "", vol.In(LAYOUTS)),
})


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    async def print_tags(call: ServiceCall) -> ServiceResponse:
        entries = [e for e in hass.config_entries.async_entries(DOMAIN) if e.state is ConfigEntryState.LOADED]
        if entry_id := call.data.get(ATTR_CONFIG_ENTRY_ID):
            entries = [e for e in entries if e.entry_id == entry_id]
        if len(entries) != 1:
            raise ServiceValidationError("Set up Homebox Labels first" if not entries
                                         else "Several Homebox connections; pass config_entry_id")
        data = entries[0].runtime_data
        asset_ids, search = call.data[ATTR_ASSET_IDS], call.data.get(ATTR_SEARCH)
        if not asset_ids and search is None:
            raise ServiceValidationError("Give asset_ids, a search text, or an empty search for all items")

        items = await async_find_items(data, asset_ids, search)
        if items and not call.data[ATTR_DRY_RUN]:
            await async_print_items(hass, data, items, icon=call.data.get(ATTR_ICON) or None,
                                    copies=call.data[ATTR_COPIES], layout=call.data.get(ATTR_LAYOUT) or None)
        return {"items": [{"asset_id": i.asset_id, "name": i.name, "location": i.location} for i in items]}

    hass.services.async_register(DOMAIN, SERVICE_PRINT_TAGS, print_tags, schema=PRINT_TAGS_SCHEMA,
                                 supports_response=SupportsResponse.OPTIONAL)
