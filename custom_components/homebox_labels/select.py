"""Selects: pick a Homebox item to print; choose the tag layout."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HomeboxLabelsConfigEntry
from .const import LAYOUTS
from .coordinator import HomeboxItemsCoordinator, item_label
from .entity import HomeboxLabelsEntity

NO_ITEM = "—"


async def async_setup_entry(hass: HomeAssistant, entry: HomeboxLabelsConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities([ItemSelect(entry), LayoutSelect(entry)])


class ItemSelect(CoordinatorEntity[HomeboxItemsCoordinator], HomeboxLabelsEntity, SelectEntity):
    """Items, boxes and locations as "000-009 · Junk Box (Office)"; "—" means none.

    SelectEntity keeps its options out of the recorder, so a long list does not
    bloat the history database.
    """

    _attr_icon = "mdi:format-list-bulleted"

    def __init__(self, entry: HomeboxLabelsConfigEntry) -> None:
        CoordinatorEntity.__init__(self, entry.runtime_data.items)
        HomeboxLabelsEntity.__init__(self, entry, "item")

    @property
    def options(self) -> list[str]:
        return [NO_ITEM, *(item_label(i) for i in self.coordinator.data or [])]

    @property
    def current_option(self) -> str:
        selected = next((i for i in self.coordinator.data or [] if i.id == self.data.selected_item_id), None)
        return item_label(selected) if selected else NO_ITEM

    async def async_select_option(self, option: str) -> None:
        item = self.coordinator.by_label(option)
        self.data.selected_item_id = item.id if item else None
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        # Shows "—" again if the selected item was deleted in Homebox.
        self.async_write_ha_state()


class LayoutSelect(HomeboxLabelsEntity, SelectEntity, RestoreEntity):
    """What goes on a tag besides the QR code; the default for buttons and the action."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = LAYOUTS
    _attr_icon = "mdi:page-layout-body"

    def __init__(self, entry: HomeboxLabelsConfigEntry) -> None:
        super().__init__(entry, "layout")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) and last.state in LAYOUTS:
            self.data.layout = last.state

    @property
    def current_option(self) -> str:
        return self.data.layout

    async def async_select_option(self, option: str) -> None:
        self.data.layout = option
        self.async_write_ha_state()
