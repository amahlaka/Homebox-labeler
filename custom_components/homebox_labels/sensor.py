"""Sensor: number of items in the item list."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HomeboxLabelsConfigEntry
from .coordinator import HomeboxItemsCoordinator
from .entity import HomeboxLabelsEntity


async def async_setup_entry(hass: HomeAssistant, entry: HomeboxLabelsConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities([ItemCountSensor(entry)])


class ItemCountSensor(CoordinatorEntity[HomeboxItemsCoordinator], HomeboxLabelsEntity, SensorEntity):
    """Items, boxes and locations with an asset ID, as of the last refresh."""

    _attr_icon = "mdi:package-variant-closed"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "items"

    def __init__(self, entry: HomeboxLabelsConfigEntry) -> None:
        CoordinatorEntity.__init__(self, entry.runtime_data.items)
        HomeboxLabelsEntity.__init__(self, entry, "items")

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data or [])
