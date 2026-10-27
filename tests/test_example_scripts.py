"""Run the example scripts from examples/homeassistant/scripts.yaml for real."""
from pathlib import Path

import pytest
import yaml

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from .test_homebox_labels import homebox_entry  # noqa: F401  (fixture)

SCRIPTS = Path(__file__).parent.parent / "examples" / "homeassistant" / "scripts.yaml"


@pytest.fixture
async def scripts(hass: HomeAssistant, homebox_entry):  # noqa: F811
    config = yaml.safe_load(SCRIPTS.read_text(encoding="utf-8"))
    assert await async_setup_component(hass, "script", {"script": config})
    await hass.async_block_till_done()


async def test_print_homebox_item_from_dropdown(hass: HomeAssistant, scripts, printer) -> None:
    await hass.services.async_call("script", "print_homebox_item",
                                   {"items": ["000-010 · Sleeves (Junk Box)"], "icon": "mdi:tools", "copies": 2},
                                   blocking=True)
    assert [label.copies for label in printer.labels] == [2]


async def test_print_homebox_item_with_layout(hass: HomeAssistant, scripts, printer) -> None:
    await hass.services.async_call("script", "print_homebox_item",
                                   {"items": ["000-010 · Sleeves (Junk Box)"], "layout": "qr"}, blocking=True)
    assert len(printer.labels) == 1


async def test_print_homebox_item_single_value(hass: HomeAssistant, scripts, printer) -> None:
    await hass.services.async_call("script", "print_homebox_item",
                                   {"items": "000-010 · Sleeves (Junk Box)"}, blocking=True)
    assert len(printer.labels) == 1

