"""Constants for Homebox Labels."""

DOMAIN = "homebox_labels"
PRINTER_DOMAIN = "wp9529"
PRINTER_SERVICE = "print_label"

CONF_PRINTER = "printer"
CONF_DEFAULT_ICON = "default_icon"

SERVICE_PRINT_TAGS = "print_tags"

# What goes on a tag besides the QR code.
LAYOUT_FULL = "full"  # QR + asset ID + name (+ icon)
LAYOUT_QR = "qr"
LAYOUT_QR_ICON = "qr_icon"
LAYOUT_QR_NAME = "qr_name"
LAYOUT_QR_NAME_ICON = "qr_name_icon"
LAYOUT_QR_ID = "qr_id"
LAYOUTS = [LAYOUT_FULL, LAYOUT_QR, LAYOUT_QR_ICON, LAYOUT_QR_NAME, LAYOUT_QR_NAME_ICON, LAYOUT_QR_ID]
# Layouts that show an icon (and so look up the item's Icon field).
ICON_LAYOUTS = (LAYOUT_FULL, LAYOUT_QR_ICON, LAYOUT_QR_NAME_ICON)

ATTR_ASSET_IDS = "asset_ids"
ATTR_SEARCH = "search"
ATTR_ICON = "icon"
ATTR_COPIES = "copies"
ATTR_DRY_RUN = "dry_run"
ATTR_LAYOUT = "layout"
ATTR_CONFIG_ENTRY_ID = "config_entry_id"
