"""Print Homebox asset tags on a WP9529 label printer.

Items are looked up in Homebox (configure HOMEBOX_URL etc. in .env), so the tag
shows the item's name and its QR code opens the item.

Examples:
    python print_tags.py --info                      # printer + Homebox status
    python print_tags.py 000-001 42 43               # tags for these asset IDs
    python print_tags.py --search drill --dry-run    # list matches, don't print
    python print_tags.py --search drill              # tag every match
    python print_tags.py --search --dry-run          # list every item
    python print_tags.py 000-001 --preview previews  # render PNGs only
    python print_tags.py 000-099 --name "Spare" --offline   # no Homebox lookup
    python print_tags.py 9 --icon mdi:package-variant        # tag with an icon
"""
import argparse
import asyncio
import logging
import os

from PIL import Image

from homebox import Homebox, HomeboxError, Item, format_asset_id, load_env
from wp9529 import PrinterError, asset_tag
from wp9529.cli import add_print_options, print_jobs, save_previews


def collect_items(args) -> list[Item]:
    if args.offline:
        return [Item(id="", asset_id=format_asset_id(a), name=args.name, location="")
                for a in args.asset_ids]
    hb = Homebox.from_env()
    items = [hb.by_asset_id(a) for a in args.asset_ids]
    if args.search is not None:
        items += hb.search(args.search)
    if args.name:
        for item in items:
            item.name = args.name
    return items


def tag_url(item: Item, args) -> str | None:
    base = args.base_url or os.environ.get("HOMEBOX_URL")
    return item.tag_url(base) if base else None


async def run(args) -> None:
    load_env()
    jobs: list[tuple[str, Image.Image]] = []
    if args.asset_ids or args.search is not None:
        items = collect_items(args)
        if not items:
            print("no matching items")
            return
        for item in items:
            print(f"  {item.asset_id}  {item.name:<40} {item.location}")
            img = asset_tag(item.asset_id, item.name, tag_url(item, args), icon=args.icon,
                            length_mm=args.length, rotate=args.rotate)
            jobs.append((item.asset_id, img))
        if args.dry_run:
            print(f"{len(items)} item(s), nothing printed (--dry-run)")
            return

    if args.preview:
        save_previews(jobs, args.preview)
        return

    if args.info and not args.offline:
        try:
            hb = Homebox.from_env()
            version = hb.status().get("build", {}).get("version", "?")
            hb.whoami()
            print(f"Homebox {hb.url}: version {version}, login OK")
        except HomeboxError as e:
            print(f"Homebox: {e}")

    if not jobs and not args.info:
        raise ValueError("nothing to print: give asset IDs, --search or --info")
    await print_jobs(jobs, args, info=args.info)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("asset_ids", nargs="*", help="Homebox asset IDs, e.g. 000-001 or 42")
    p.add_argument("--search", metavar="TEXT", nargs="?", const="",
                   help="tag every Homebox item matching TEXT (no TEXT = all items)")
    p.add_argument("--dry-run", action="store_true", help="list the items, don't print")
    p.add_argument("--offline", action="store_true", help="don't contact Homebox; use --name")
    p.add_argument("--name", default="", help="override the name printed under the ID")
    p.add_argument("--base-url", help="URL for the QR code (default HOMEBOX_URL)")
    p.add_argument("--icon", help="MDI icon to add, e.g. mdi:tools (https://pictogrammers.com/library/mdi/)")
    p.add_argument("--info", action="store_true", help="show printer and Homebox status")
    add_print_options(p)
    args = p.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING, format="%(message)s")
    try:
        asyncio.run(run(args))
    except (HomeboxError, PrinterError, ValueError) as e:
        raise SystemExit(f"error: {e}") from None


if __name__ == "__main__":
    main()
