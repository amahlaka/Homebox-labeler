"""Keeps the list of Homebox items for the item dropdown up to date."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .homebox import Homebox, HomeboxError, Item

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)
UPDATE_INTERVAL = timedelta(minutes=15)


def item_label(item: Item) -> str:
    """Dropdown text, e.g. "000-009 · Junk Box (Office)"; unique because of the asset ID."""
    label = f"{item.asset_id} · {item.name}"
    return f"{label} ({item.location})" if item.location else label


class HomeboxItemsCoordinator(DataUpdateCoordinator[list[Item]]):
    """All items, boxes and locations, sorted by asset ID."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, homebox: Homebox) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=f"{DOMAIN} items",
                         update_interval=UPDATE_INTERVAL)
        self.homebox = homebox

    async def _async_update_data(self) -> list[Item]:
        try:
            return await self.homebox.search()
        except HomeboxError as err:
            raise UpdateFailed(f"Could not load items from Homebox: {err}") from err

    def by_label(self, label: str) -> Item | None:
        return next((i for i in self.data or [] if item_label(i) == label), None)
