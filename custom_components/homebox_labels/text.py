"""Text inputs: asset IDs to print and an icon override."""
from __future__ import annotations

from homeassistant.components.text import TextEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import HomeboxLabelsConfigEntry
from .entity import HomeboxLabelsEntity


async def async_setup_entry(hass: HomeAssistant, entry: HomeboxLabelsConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities([
        FormText(entry, "asset_ids", "form_asset_ids", "mdi:barcode"),
        FormText(entry, "icon", "form_icon", "mdi:emoticon-outline"),
    ])


class FormText(HomeboxLabelsEntity, TextEntity):
    """A field of the print form; read by the Print tags button."""

    _attr_native_max = 255

    def __init__(self, entry: HomeboxLabelsConfigEntry, key: str, attr: str, icon: str) -> None:
        super().__init__(entry, key)
        self._data_attr = attr
        self._attr_icon = icon

    @property
    def native_value(self) -> str:
        return getattr(self.data, self._data_attr)

    async def async_set_value(self, value: str) -> None:
        setattr(self.data, self._data_attr, value.strip())
        self.async_write_ha_state()
