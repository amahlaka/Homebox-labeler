# Homebox labels on a WP9529

Print [Homebox](https://homebox.software) asset tags on a VSON **WP9529**
Bluetooth label printer, from a PC or from Home Assistant.

Each tag shows:
- a QR code that opens the item in Homebox (`<your homebox>/a/<asset-id>`)
- the asset ID, e.g. `000-042`, in large text
- the item's name, wrapped onto two lines and shortened with "…" if needed

Items, boxes and locations (rooms) can all be tagged, optionally with a
[Material Design Icon](https://pictogrammers.com/library/mdi/).

Two ways to use it:
- the **command-line tool** `print_tags.py` on a PC near the printer
- **Home Assistant**: the **Homebox Labels** integration
  (`custom_components/homebox_labels`), which prints through the WP9529
  printer integration

This builds on the **WP9529** project: its Python package (driver and label
renderer) for the command line, and its Home Assistant integration for
printing from Home Assistant.

## Requirements

- Windows, macOS or Linux with Bluetooth LE
- Python 3.12+
- The WP9529 project, checked out next to this one (`../WP9529`)
- A WP9529 with 30 × 12 mm die-cut labels (other sizes work with `--length`/`--gap`)
- A Homebox instance (tested with v0.26.2)

## Setup

1. Create a virtual environment and install the dependencies (this installs
   the WP9529 package from `../WP9529`):

   ```bash
   python -m venv .venv
   ```
   ```bash
   .venv\Scripts\python -m pip install -r requirements.txt
   ```

   On macOS/Linux use `.venv/bin/python` instead of `.venv\Scripts\python`.

2. Copy `.env.example` to `.env` and fill it in:

   ```ini
   HOMEBOX_URL=https://homebox.example.com

   # Either an API key (Homebox: profile/settings -> API keys)...
   HOMEBOX_TOKEN=...

   # ...or your login
   HOMEBOX_USERNAME=
   HOMEBOX_PASSWORD=
   ```

   `.env` holds credentials, so keep it out of git and anything you share.

3. Turn the printer on. **Close the phone app or disconnect it from the
   printer**, because the printer only accepts one connection at a time.

4. Check that everything is reachable:

   ```bash
   .venv\Scripts\python print_tags.py --info
   ```

   ```
   Homebox https://homebox.example.com: version v0.26.2, login OK
   printer 95:29:12:C2:09:0C: firmware V50
   auto power-off after 96 minutes
   ```

## Printing tags

The examples below omit the `.venv\Scripts\python` prefix for brevity.

### By asset ID

```bash
python print_tags.py 000-042
```
```bash
python print_tags.py 42 43 44
```

Short IDs are expanded: `42` → `000-042`, `1234` → `001-234`. The item name and
QR link are looked up in Homebox.

### By search

```bash
python print_tags.py --search drill
```

This prints a tag for every item, box or location whose name matches. Use
`--search` with no text to match **everything**:

```bash
python print_tags.py --search --dry-run
```

### Check before printing

`--dry-run` lists what would be printed and stops:

```
  000-009  Junk Box                                 Office
  000-010  Classic Soft Sleeves - Clear (100) New   Junk Box
2 item(s), nothing printed (--dry-run)
```

`--preview DIR` renders each tag to `DIR/<asset-id>.png` instead of printing:

```bash
python print_tags.py 9 10 --preview previews
```

### Without Homebox

```bash
python print_tags.py 000-099 --offline --name "Spare cables" --base-url https://homebox.example.com
```

`--offline` skips the Homebox lookup and uses `--name`. Leave out `--base-url`
to print a tag without a QR code.

### Icons

```bash
python print_tags.py 9 --icon mdi:package-variant
```

For labels that aren't Homebox items (Wi-Fi details, any QR code, free text),
use the WP9529 package's `wp9529-label` command.

## Options

| Option | Default | Meaning |
|---|---|---|
| `ASSET_ID ...` | | asset IDs to print |
| `--search [TEXT]` | | print everything matching TEXT (no TEXT = all) |
| `--dry-run` | | list the items, don't print |
| `--preview DIR` | | save PNGs to DIR instead of printing |
| `--offline` | | don't contact Homebox; use `--name` |
| `--name TEXT` | item name | override the name on the tag |
| `--base-url URL` | `HOMEBOX_URL` | base of the QR link |
| `--icon mdi:NAME` | | add an MDI icon |
| `--copies N` | 1 | copies of each tag |
| `--length MM` | 30 | label length |
| `--gap MM` | 8.5 | gap between labels |
| `--continuous` | | continuous tape instead of die-cut labels |
| `--density` | normal | `light`, `normal` or `dark` |
| `--rotate` | 90 | use `270` if the text comes out upside down |
| `--feed N` | 0 | extra blank lines after each tag |
| `--address MAC` | scan | printer Bluetooth address (skips the scan) |
| `--info` | | show Homebox and printer status |
| `-v` | | verbose: log every Bluetooth packet |

## Home Assistant

The **Homebox Labels** integration looks items up in Homebox and prints asset
tags by calling the printer integration's `wp9529.print_label` action, so it
needs the WP9529 integration (from the WP9529 project) set up first.

### Install

1. Install the WP9529 integration and add the printer (see the WP9529 project).
2. Copy `custom_components/homebox_labels` into `/config/custom_components/` on
   Home Assistant. Restart Home Assistant.
3. *Add integration* → **Homebox Labels**. Enter the Homebox URL, an API key
   (Homebox: profile → API keys) and pick the printer. The key is checked before
   saving. *Configure* changes the printer or sets a default tag icon;
   *Reconfigure* changes the URL or key.

### Action

**`homebox_labels.print_tags`**: Homebox asset tags (QR link, asset ID, name).

| Field | Meaning |
|---|---|
| `asset_ids` | list or comma-separated text: `"000-042, 43"` |
| `search` | name search; empty text matches everything |
| `icon` | icon for these tags; overrides the item's own Icon field and the default tag icon |
| `copies` | copies of each tag |
| `dry_run` | only return the matching items |
| `layout` | `full`, `qr`, `qr_icon`, `qr_name`, `qr_name_icon` or `qr_id`; defaults to the Tag layout setting |
| `config_entry_id` | which Homebox, if you connected several |

It returns the matched items:

```yaml
action: homebox_labels.print_tags
data:
  asset_ids: "000-009, 10"
response_variable: printed   # {"items": [{"asset_id", "name", "location"}, ...]}
```

**Per-item icons:** give an item, box or location a custom text field named
**Icon** in Homebox with an MDI name (`mdi:book-open-variant`, or just
`book-open-variant`). Its tags then show that icon. The icon used is, in order:
1. one given when printing (action `icon`, the script's icon, or the Tag icon field)
2. the item's Icon field
3. the default tag icon from the options

Only the *QR + ID + name*, *QR + icon* and *QR + name + icon* layouts show an
icon, and only those fetch the field (one extra request per tag). A misspelled
Icon field stops that tag with an error naming the item.

### The Homebox Labels device

| Entity | Purpose |
|---|---|
| **Item** (select) | dropdown of every item, box and location, shown as `000-009 · Junk Box (Office)`. Refreshed from Homebox every 15 minutes |
| **Print selected item** (button) | prints the tag for the item chosen in the dropdown |
| **Asset IDs** (text) + **Print tags** (button) | print several at once by typing IDs: `42, 43` |
| **Tag icon** (text) | optional icon for tags printed with these buttons |
| **Tag layout** (select, config) | what goes on a tag besides the QR code: *QR + ID + name* (default, plus the icon if set), *QR only*, *QR + icon*, *QR + name*, *QR + name + icon* or *QR + ID*. Used by the buttons and as the action's default |
| **Items** (sensor) | how many items the dropdown lists |
| **Refresh item list** (button, diagnostic) | reload the list right away, e.g. after adding items in Homebox |

If Homebox can't be reached when Home Assistant starts, the integration retries
in the background until it can.

### Examples

Ready-made YAML is in [examples/homeassistant](examples/homeassistant). Entity
IDs assume the Homebox connection is named "Homebox":

- [`scripts.yaml`](examples/homeassistant/scripts.yaml):
  - `script.print_homebox_item`: choose one or more items from a dropdown (the Item entity's list), an icon from Home Assistant's icon picker, and the layout
  - `script.print_asset_tag`: type asset IDs; prints tags and shows a notification listing them
- [`automations.yaml`](examples/homeassistant/automations.yaml): printing tags
  as soon as IDs are typed into the Asset IDs field
- [`dashboard-card.yaml`](examples/homeassistant/dashboard-card.yaml): a
  Homebox tags card

## Development

The tests cover the config flow, every entity, the action, layouts and icons,
and the example scripts. Homebox is mocked, and so is the printer: a stand-in
`wp9529` integration records each `wp9529.print_label` call, so the tests don't
need the WP9529 project. They need Linux (or WSL) with Python 3.14:

```bash
pip install pytest-homeassistant-custom-component
```
```bash
pytest
```

## Troubleshooting

**"No WP9529 found"**: the printer is off, asleep, or connected to the phone
app. Turn it on, close the app and try again.

**`HTTP 401` / login errors**: check `HOMEBOX_TOKEN`, or the username and
password, in `.env`.

**Only some items appear in `--search`**: Homebox lists locations, boxes and
cabinets separately from items. The tool fetches both, but the name filter for
locations is applied locally and is a plain case-insensitive substring match.

**`--search ""` gives "expected one argument"**: Windows PowerShell 5.1 drops
empty arguments. Use plain `--search` instead.

**Homebox Labels: "No printer selected"**: open Homebox Labels → *Configure*
and pick the printer.

For printer problems (alignment, darkness, Bluetooth), see the WP9529 project.

## Files

| Path | What it is |
|---|---|
| `print_tags.py` | the command-line tool |
| `homebox.py` | minimal Homebox API client (standard library only) |
| `custom_components/homebox_labels/` | the Home Assistant integration |
| `examples/homeassistant/` | example scripts, automation and dashboard card |
| `tests/` | integration tests (Linux/WSL) |
| `requirements.txt` | installs the WP9529 package from `../WP9529` |
| `.env.example` | settings template |
