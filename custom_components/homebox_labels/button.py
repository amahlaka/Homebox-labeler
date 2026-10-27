"""Buttons: print the selected item, print typed asset IDs, refresh the item list."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import HomeboxLabelsConfigEntry
from .entity import HomeboxLabelsEntity
from .tags import async_find_items, async_print_items, parse_asset_ids


async def async_setup_entry(hass: HomeAssistant, entry: HomeboxLabelsConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities([PrintSelectedButton(entry), PrintTagsButton(entry), RefreshItemsButton(entry)])


def _form_icon(icon: str) -> str | None:
    if icon and not icon.startswith("mdi:"):
        icon = f"mdi:{icon}"
    return icon or None


class PrintSelectedButton(HomeboxLabelsEntity, ButtonEntity):
    """Print the tag for the item chosen in the Item dropdown."""

    _attr_icon = "mdi:label-outline"

    def __init__(self, entry: HomeboxLabelsConfigEntry) -> None:
        super().__init__(entry, "print_selected")

    async def async_press(self) -> None:
        item = next((i for i in self.data.items.data or [] if i.id == self.data.selected_item_id), None)
        if item is None:
            raise ServiceValidationError("Choose an item in the Item dropdown first")
        await async_print_items(self.hass, self.data, [item], icon=_form_icon(self.data.form_icon))


class PrintTagsButton(HomeboxLabelsEntity, ButtonEntity):
    """Print tags for the asset IDs typed into Asset IDs."""

    _attr_icon = "mdi:label-multiple-outline"

    def __init__(self, entry: HomeboxLabelsConfigEntry) -> None:
        super().__init__(entry, "print_tags")

    async def async_press(self) -> None:
        asset_ids = parse_asset_ids(self.data.form_asset_ids)
        if not asset_ids:
            raise ServiceValidationError("Type one or more asset IDs into Asset IDs first")
        items = await async_find_items(self.data, asset_ids, None)
        await async_print_items(self.hass, self.data, items, icon=_form_icon(self.data.form_icon))


class RefreshItemsButton(HomeboxLabelsEntity, ButtonEntity):
    """Reload the item list from Homebox now instead of waiting for the next refresh."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: HomeboxLabelsConfigEntry) -> None:
        super().__init__(entry, "refresh_items")

    async def async_press(self) -> None:
        await self.data.items.async_refresh()
