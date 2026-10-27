"""Look up Homebox items and print their tags through the printer integration."""
from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .const import (
    ICON_LAYOUTS,
    LAYOUT_FULL,
    LAYOUT_QR,
    LAYOUT_QR_ICON,
    LAYOUT_QR_ID,
    LAYOUT_QR_NAME,
    LAYOUT_QR_NAME_ICON,
    PRINTER_DOMAIN,
    PRINTER_SERVICE,
)
from .homebox import HomeboxError, Item

if TYPE_CHECKING:
    from . import HomeboxLabelsData


def parse_asset_ids(text: str) -> list[str]:
    """Split "000-042, 43 44" into ["000-042", "43", "44"]."""
    return [part for part in text.replace(";", ",").replace(" ", ",").split(",") if part]


async def async_find_items(data: HomeboxLabelsData, asset_ids: list[str], search: str | None) -> list[Item]:
    try:
        items = [await data.homebox.by_asset_id(a) for a in asset_ids]
        if search is not None:
            items += await data.homebox.search(search)
    except (HomeboxError, ValueError) as err:
        raise HomeAssistantError(f"Homebox lookup failed: {err}") from err
    return items


def tag_fields(item: Item, url: str, layout: str, icon: str) -> dict[str, str]:
    """title / text / qr / icon for the printer's print_label action, per layout."""
    fields = {"title": "", "text": "", "qr": url, "icon": ""}
    if layout == LAYOUT_FULL:
        fields.update(title=item.asset_id, text=item.name, icon=icon)
    elif layout == LAYOUT_QR_ICON:
        if not icon:
            raise ServiceValidationError("The QR + icon layout needs an icon: pick one, or set a default tag icon")
        fields["icon"] = icon
    elif layout == LAYOUT_QR_NAME:
        fields["text"] = item.name  # text wraps onto up to 3 lines, unlike the title
    elif layout == LAYOUT_QR_NAME_ICON:
        fields.update(text=item.name, icon=icon)  # without an icon this is just QR + name
    elif layout == LAYOUT_QR_ID:
        fields["title"] = item.asset_id
    elif layout != LAYOUT_QR:
        raise ServiceValidationError(f"Unknown tag layout {layout!r}")
    return fields


async def async_item_icon(data: HomeboxLabelsData, item: Item, icon: str | None, layout: str) -> str:
    """The icon for an item's tag: the one given when printing, else the item's
    "Icon" custom field in Homebox, else the default tag icon."""
    if icon is not None:
        return icon
    if layout not in ICON_LAYOUTS:
        return ""  # these layouts never show an icon; skip the extra request
    try:
        item_icon = await data.homebox.item_icon(item.id)
    except HomeboxError as err:
        raise HomeAssistantError(f"Homebox lookup failed for {item.asset_id}: {err}") from err
    return item_icon or data.default_icon


async def async_print_items(hass: HomeAssistant, data: HomeboxLabelsData, items: list[Item],
                            icon: str | None = None, copies: int = 1, layout: str | None = None) -> None:
    """Print one asset tag per item via the printer's public action."""
    if not data.printer_device_id:
        raise ServiceValidationError("No printer selected; choose one in Homebox Labels' options")
    layout = layout or data.layout
    for item in items:
        item_icon = await async_item_icon(data, item, icon, layout)
        fields = tag_fields(item, item.tag_url(data.homebox.url), layout, item_icon)
        try:
            await hass.services.async_call(PRINTER_DOMAIN, PRINTER_SERVICE, {
                "device_id": data.printer_device_id, **fields, "copies": copies,
            }, blocking=True)
        except ServiceValidationError as err:
            if icon is None and item_icon != data.default_icon and "unknown MDI icon" in str(err):
                raise ServiceValidationError(
                    f"{item.asset_id} {item.name}: its Icon field in Homebox ({item_icon}) "
                    "is not an MDI icon name") from err
            raise
