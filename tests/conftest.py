"""Shared fixtures: a stand-in for the wp9529 printer integration.

Homebox Labels only talks to the printer through its public action,
wp9529.print_label, so the tests don't need the real integration: a fake one
with a printer device and an action that records each call is enough.
"""
from types import SimpleNamespace

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, MockModule, mock_integration

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.setup import async_setup_component

pytest_plugins = "pytest_homeassistant_custom_component"

ADDRESS = "95:29:12:C2:09:0C"
LABEL_FIELDS = {"title": "", "text": "", "qr": "", "icon": "", "copies": 1}
UNKNOWN_ICONS = {"mdi:no-such-icon"}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let Home Assistant load integrations from custom_components/."""
    yield


@pytest.fixture
async def printer(hass: HomeAssistant) -> SimpleNamespace:
    """A fake wp9529 integration with one printer; `.labels` are the print_label calls."""
    labels: list[SimpleNamespace] = []

    async def print_label(call: ServiceCall) -> None:
        # The real integration checks icons against its MDI font and fails like this.
        if call.data.get("icon") in UNKNOWN_ICONS:
            raise ServiceValidationError(f"unknown MDI icon: {call.data['icon']}")
        labels.append(SimpleNamespace(**{**LABEL_FIELDS, **call.data}))

    async def async_setup(hass: HomeAssistant, config) -> bool:
        hass.services.async_register("wp9529", "print_label", print_label)
        return True

    mock_integration(hass, MockModule("wp9529", async_setup=async_setup))
    assert await async_setup_component(hass, "wp9529", {})
    entry = MockConfigEntry(domain="wp9529", unique_id=ADDRESS, title="WP9529 090C")
    entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={("wp9529", ADDRESS)}, name="WP9529 090C")
    return SimpleNamespace(device_id=device.id, labels=labels)
