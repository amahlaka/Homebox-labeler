"""Tests for the homebox_labels integration, printing through a fake wp9529 (see conftest)."""
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant import config_entries
from homeassistant.const import CONF_API_TOKEN, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er

from custom_components.homebox_labels.homebox import Item
from custom_components.homebox_labels.tags import tag_fields

DOMAIN = "homebox_labels"
HB = "https://homebox.test"


def mock_homebox(aioclient_mock, auth_status=200):
    aioclient_mock.get(f"{HB}/api/v1/status", json={"build": {"version": "v0.26.2"}})
    aioclient_mock.get(f"{HB}/api/v1/users/self", status=auth_status, json={})
    aioclient_mock.get(f"{HB}/api/v1/assets/000-009", json={"items": [
        {"id": "a", "assetId": "000-009", "name": "Junk Box", "location": {"name": "Office"}}]})
    aioclient_mock.get(f"{HB}/api/v1/assets/000-010", json={"items": [
        {"id": "b", "assetId": "000-010", "name": "Sleeves", "parent": {"name": "Junk Box"}}]})
    aioclient_mock.get(f"{HB}/api/v1/entities", json={"total": 1, "items": [
        {"id": "b", "assetId": "000-010", "name": "Sleeves", "parent": {"name": "Junk Box"}}]})
    # Full items: only these carry custom fields.
    aioclient_mock.get(f"{HB}/api/v1/entities/a", json={"id": "a", "fields": []})
    mock_icon_field(aioclient_mock, "b", "Icon", "mdi:cards-playing-outline")


def mock_icon_field(aioclient_mock, item_id, name, value):
    aioclient_mock.get(f"{HB}/api/v1/entities/{item_id}", json={"id": item_id, "fields": [
        {"type": "text", "name": "Author", "textValue": "x"},
        {"type": "text", "name": name, "textValue": value}]})


@pytest.fixture
async def homebox_entry(hass: HomeAssistant, printer, aioclient_mock) -> MockConfigEntry:
    mock_homebox(aioclient_mock)
    entry = MockConfigEntry(domain=DOMAIN, unique_id=HB, title="Homebox (homebox.test)",
                            data={CONF_URL: HB, CONF_API_TOKEN: "tok"},
                            options={"printer": printer.device_id, "default_icon": "mdi:package-variant"})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def eid(hass, entry, platform, key):
    return er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"{entry.entry_id}_{key}")


@pytest.mark.parametrize(("status", "outcome"), [(200, "created"), (401, "invalid_auth")])
async def test_user_flow(hass: HomeAssistant, printer, aioclient_mock, status, outcome) -> None:
    mock_homebox(aioclient_mock, auth_status=status)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: HB + "/", CONF_API_TOKEN: "tok", "printer": printer.device_id})
    if outcome == "created":
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"] == {CONF_URL: HB, CONF_API_TOKEN: "tok"}
        assert result["options"] == {"printer": printer.device_id}
    else:
        assert result["errors"] == {"base": outcome}


async def test_print_tags_prints_via_printer(hass: HomeAssistant, homebox_entry, printer) -> None:
    resp = await hass.services.async_call(DOMAIN, "print_tags", {"asset_ids": "9", "copies": 2},
                                          blocking=True, return_response=True)
    assert resp == {"items": [{"asset_id": "000-009", "name": "Junk Box", "location": "Office"}]}
    (label,) = printer.labels
    assert (label.device_id, label.copies, label.title) == (printer.device_id, 2, "000-009")


async def test_print_tags_search_and_dry_run(hass: HomeAssistant, homebox_entry, printer) -> None:
    resp = await hass.services.async_call(DOMAIN, "print_tags", {"search": "", "dry_run": True},
                                          blocking=True, return_response=True)
    assert [i["asset_id"] for i in resp["items"]] == ["000-010"]
    assert printer.labels == []


async def test_print_tags_needs_input(hass: HomeAssistant, homebox_entry) -> None:
    with pytest.raises(ServiceValidationError, match="Give asset_ids"):
        await hass.services.async_call(DOMAIN, "print_tags", {}, blocking=True)


async def test_ui_form_button(hass: HomeAssistant, homebox_entry, printer) -> None:
    await hass.services.async_call("text", "set_value",
                                   {"entity_id": eid(hass, homebox_entry, "text", "asset_ids"), "value": "9"},
                                   blocking=True)
    await hass.services.async_call("button", "press",
                                   {"entity_id": eid(hass, homebox_entry, "button", "print_tags")}, blocking=True)
    assert len(printer.labels) == 1


async def test_item_dropdown_and_count(hass: HomeAssistant, homebox_entry) -> None:
    state = hass.states.get(eid(hass, homebox_entry, "select", "item"))
    assert state.state == "—"
    assert state.attributes["options"] == ["—", "000-010 · Sleeves (Junk Box)"]
    assert hass.states.get(eid(hass, homebox_entry, "sensor", "items")).state == "1"


async def test_print_selected_item(hass: HomeAssistant, homebox_entry, printer) -> None:
    select_id = eid(hass, homebox_entry, "select", "item")
    button_id = eid(hass, homebox_entry, "button", "print_selected")
    with pytest.raises(ServiceValidationError, match="Choose an item"):
        await hass.services.async_call("button", "press", {"entity_id": button_id}, blocking=True)

    await hass.services.async_call("select", "select_option",
                                   {"entity_id": select_id, "option": "000-010 · Sleeves (Junk Box)"},
                                   blocking=True)
    assert hass.states.get(select_id).state == "000-010 · Sleeves (Junk Box)"
    await hass.services.async_call("button", "press", {"entity_id": button_id}, blocking=True)
    assert len(printer.labels) == 1


async def test_refresh_item_list(hass: HomeAssistant, homebox_entry, aioclient_mock) -> None:
    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{HB}/api/v1/entities", json={"total": 2, "items": [
        {"id": "b", "assetId": "000-010", "name": "Sleeves", "parent": {"name": "Junk Box"}},
        {"id": "c", "assetId": "000-011", "name": "Fridge", "location": {"name": "Kitchen"}}]})
    await hass.services.async_call("button", "press",
                                   {"entity_id": eid(hass, homebox_entry, "button", "refresh_items")}, blocking=True)
    assert hass.states.get(eid(hass, homebox_entry, "sensor", "items")).state == "2"
    assert "000-011 · Fridge (Kitchen)" in hass.states.get(
        eid(hass, homebox_entry, "select", "item")).attributes["options"]


async def test_setup_retries_when_homebox_down(hass: HomeAssistant, printer, aioclient_mock) -> None:
    aioclient_mock.get(f"{HB}/api/v1/entities", status=500, text="down")
    entry = MockConfigEntry(domain=DOMAIN, unique_id=HB, data={CONF_URL: HB, CONF_API_TOKEN: "tok"},
                            options={"printer": printer.device_id})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is config_entries.ConfigEntryState.SETUP_RETRY


ITEM = Item(id="b", asset_id="000-010", name="Sleeves", location="Junk Box")
URL = f"{HB}/a/000-010"


@pytest.mark.parametrize(("layout", "icon", "expected"), [
    ("full", "mdi:tools", {"title": "000-010", "text": "Sleeves", "qr": URL, "icon": "mdi:tools"}),
    ("full", "", {"title": "000-010", "text": "Sleeves", "qr": URL, "icon": ""}),
    ("qr", "mdi:tools", {"title": "", "text": "", "qr": URL, "icon": ""}),
    ("qr_icon", "mdi:tools", {"title": "", "text": "", "qr": URL, "icon": "mdi:tools"}),
    ("qr_name", "mdi:tools", {"title": "", "text": "Sleeves", "qr": URL, "icon": ""}),
    ("qr_name_icon", "mdi:tools", {"title": "", "text": "Sleeves", "qr": URL, "icon": "mdi:tools"}),
    ("qr_name_icon", "", {"title": "", "text": "Sleeves", "qr": URL, "icon": ""}),
    ("qr_id", "mdi:tools", {"title": "000-010", "text": "", "qr": URL, "icon": ""}),
])
def test_tag_fields(layout, icon, expected) -> None:
    assert tag_fields(ITEM, URL, layout, icon) == expected


def test_qr_icon_layout_needs_icon() -> None:
    with pytest.raises(ServiceValidationError, match="needs an icon"):
        tag_fields(ITEM, URL, "qr_icon", "")


@pytest.fixture
def printed(printer):
    """The label content the printer integration was asked to print."""
    return printer.labels


async def test_layout_setting_used_by_buttons(hass: HomeAssistant, homebox_entry, printed) -> None:
    layout_id = eid(hass, homebox_entry, "select", "layout")
    assert hass.states.get(layout_id).state == "full"
    await hass.services.async_call("select", "select_option", {"entity_id": layout_id, "option": "qr_id"},
                                   blocking=True)
    await hass.services.async_call("select", "select_option",
                                   {"entity_id": eid(hass, homebox_entry, "select", "item"),
                                    "option": "000-010 · Sleeves (Junk Box)"}, blocking=True)
    await hass.services.async_call("button", "press",
                                   {"entity_id": eid(hass, homebox_entry, "button", "print_selected")},
                                   blocking=True)
    assert (printed[0].title, printed[0].text, printed[0].icon) == ("000-010", "", "")
    assert printed[0].qr == URL


async def test_layout_action_override(hass: HomeAssistant, homebox_entry, printed) -> None:
    await hass.services.async_call(DOMAIN, "print_tags", {"asset_ids": "9", "layout": "qr_icon"}, blocking=True)
    # No icon given: the default tag icon from the options is used.
    assert (printed[0].title, printed[0].icon) == ("", "mdi:package-variant")
    await hass.services.async_call(DOMAIN, "print_tags", {"asset_ids": "9", "layout": ""}, blocking=True)
    assert printed[1].title == "000-009"  # empty layout = the Tag layout setting (full)


async def test_icon_from_homebox_field(hass: HomeAssistant, homebox_entry, printed) -> None:
    await hass.services.async_call(DOMAIN, "print_tags", {"asset_ids": "10"}, blocking=True)
    assert printed[0].icon == "mdi:cards-playing-outline"


async def test_item_without_icon_field_uses_default(hass: HomeAssistant, homebox_entry, printed) -> None:
    await hass.services.async_call(DOMAIN, "print_tags", {"asset_ids": "9"}, blocking=True)
    assert printed[0].icon == "mdi:package-variant"


async def test_given_icon_beats_homebox_field(hass: HomeAssistant, homebox_entry, printed) -> None:
    await hass.services.async_call(DOMAIN, "print_tags", {"asset_ids": "10", "icon": "mdi:tools"}, blocking=True)
    assert printed[0].icon == "mdi:tools"


async def test_icon_field_name_and_prefix_are_lenient(hass: HomeAssistant, homebox_entry, aioclient_mock,
                                                      printed) -> None:
    aioclient_mock.clear_requests()
    mock_homebox_without_detail_b(aioclient_mock)
    mock_icon_field(aioclient_mock, "b", "ICON", " tools ")
    await hass.services.async_call(DOMAIN, "print_tags", {"asset_ids": "10"}, blocking=True)
    assert printed[0].icon == "mdi:tools"


async def test_qr_name_icon_uses_icon_field(hass: HomeAssistant, homebox_entry, printed) -> None:
    await hass.services.async_call(DOMAIN, "print_tags", {"asset_ids": "10", "layout": "qr_name_icon"},
                                   blocking=True)
    assert (printed[0].title, printed[0].text, printed[0].icon) == ("", "Sleeves", "mdi:cards-playing-outline")


async def test_layout_without_icon_skips_lookup(hass: HomeAssistant, homebox_entry, aioclient_mock,
                                                printed) -> None:
    await hass.services.async_call(DOMAIN, "print_tags", {"asset_ids": "10", "layout": "qr_id"}, blocking=True)
    assert not any(str(url).endswith("/entities/b") for _, url, _, _ in aioclient_mock.mock_calls)


async def test_bad_icon_field_is_explained(hass: HomeAssistant, homebox_entry, aioclient_mock,
                                           printer) -> None:
    aioclient_mock.clear_requests()
    mock_homebox_without_detail_b(aioclient_mock)
    mock_icon_field(aioclient_mock, "b", "Icon", "mdi:no-such-icon")
    with pytest.raises(ServiceValidationError, match="000-010 Sleeves: its Icon field"):
        await hass.services.async_call(DOMAIN, "print_tags", {"asset_ids": "10"}, blocking=True)


def mock_homebox_without_detail_b(aioclient_mock):
    aioclient_mock.get(f"{HB}/api/v1/assets/000-010", json={"items": [
        {"id": "b", "assetId": "000-010", "name": "Sleeves", "parent": {"name": "Junk Box"}}]})


async def test_no_printer_selected(hass: HomeAssistant, printer, aioclient_mock) -> None:
    mock_homebox(aioclient_mock)
    entry = MockConfigEntry(domain=DOMAIN, unique_id=HB, data={CONF_URL: HB, CONF_API_TOKEN: "tok"})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    with pytest.raises(ServiceValidationError, match="No printer selected"):
        await hass.services.async_call(DOMAIN, "print_tags", {"asset_ids": "9"}, blocking=True)
