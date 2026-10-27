"""Async Homebox API client for looking up items to label."""
from __future__ import annotations

from dataclasses import dataclass

import aiohttp


class HomeboxError(Exception):
    """Homebox could not be reached or refused the request."""


class HomeboxAuthError(HomeboxError):
    """Homebox rejected the API token."""


@dataclass
class Item:
    id: str
    asset_id: str
    name: str
    location: str

    def tag_url(self, base_url: str) -> str:
        return f"{base_url.rstrip('/')}/a/{self.asset_id}"


def format_asset_id(value: str | int) -> str:
    """Normalise 1, "1", "000001" or "000-001" to Homebox's "000-001" form."""
    digits = str(value).replace("-", "").strip()
    if not digits.isdigit():
        raise ValueError(f"not an asset ID: {value!r}")
    digits = digits.zfill(6)
    return f"{digits[:-3]}-{digits[-3:]}"


class Homebox:
    def __init__(self, session: aiohttp.ClientSession, url: str, token: str) -> None:
        self.session = session
        self.url = url.rstrip("/")
        self.token = token if token.lower().startswith("bearer ") else f"Bearer {token}"
        self._items_path: str | None = None

    async def _call(self, method: str, path: str, query=None, auth: bool = True):
        headers = {"Accept": "application/json"}
        if auth:
            headers["Authorization"] = self.token
        try:
            async with self.session.request(method, f"{self.url}/api{path}", params=query,
                                            headers=headers,
                                            timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 401:
                    raise HomeboxAuthError("Homebox rejected the API token")
                if resp.status >= 400:
                    body = (await resp.text())[:200]
                    raise HomeboxError(f"{method} {path} -> HTTP {resp.status}: {body}")
                return await resp.json(content_type=None)
        except aiohttp.ClientError as e:
            raise HomeboxError(f"cannot reach {self.url}: {e}") from e
        except TimeoutError as e:
            raise HomeboxError(f"timed out talking to {self.url}") from e

    async def status(self) -> dict:
        return await self._call("GET", "/v1/status", auth=False)

    async def whoami(self) -> dict:
        """The logged-in user; a cheap way to check the token."""
        return await self._call("GET", "/v1/users/self")

    def _item_from(self, data: dict) -> Item:
        where = data.get("location") or data.get("parent") or {}
        return Item(id=data["id"], asset_id=format_asset_id(data.get("assetId") or 0),
                    name=data.get("name", ""), location=where.get("name", ""))

    async def item_icon(self, item_id: str) -> str:
        """The item's "Icon" custom field as "mdi:name", or "" when it has none.

        Custom fields only come with the full item, not with lookups or lists.
        """
        try:
            detail = await self._call("GET", f"{self._items_path or '/v1/entities'}/{item_id}")
        except HomeboxError as err:
            if "HTTP 404" not in str(err) or self._items_path:
                raise
            detail = await self._call("GET", f"/v1/items/{item_id}")  # Homebox before v0.26
        for field in detail.get("fields") or []:
            if (field.get("name") or "").strip().casefold() == "icon":
                value = (field.get("textValue") or "").strip()
                if value:
                    return value if value.startswith("mdi:") else f"mdi:{value}"
        return ""

    async def by_asset_id(self, asset_id: str | int) -> Item:
        aid = format_asset_id(asset_id)
        page = await self._call("GET", f"/v1/assets/{aid}")
        items = page.get("items") or []
        if not items:
            raise HomeboxError(f"no item with asset ID {aid}")
        return self._item_from(items[0])

    async def search(self, query: str = "", page_size: int = 100) -> list[Item]:
        """Items, boxes and locations matching `query` (all when empty), by asset ID."""
        items, page = [], 1
        while True:
            resp = await self._list({"q": query, "page": page, "pageSize": page_size,
                                     "orderBy": "assetId", "orderDirection": "asc"})
            items += [self._item_from(i) for i in resp.get("items") or []]
            if len(items) >= resp.get("total", 0) or not resp.get("items"):
                break
            page += 1
        if self._items_path == "/v1/entities":
            # v0.26+ leaves location-like entities (rooms, boxes, cabinets) out
            # of the normal listing; they come back only with isLocation=true.
            locs = await self._call("GET", "/v1/entities", query={"isLocation": "true"})
            items += [self._item_from(i) for i in locs.get("items") or []
                      if query.lower() in i.get("name", "").lower()]
        seen = set()
        unique = [i for i in items if not (i.id in seen or seen.add(i.id))]
        return sorted(unique, key=lambda i: i.asset_id)

    async def _list(self, query):
        # Newer Homebox calls items "entities"; fall back to the old path.
        paths = [self._items_path] if self._items_path else ["/v1/entities", "/v1/items"]
        for i, path in enumerate(paths):
            try:
                resp = await self._call("GET", path, query=query)
                self._items_path = path
                return resp
            except HomeboxError as e:
                if "HTTP 404" not in str(e) or i == len(paths) - 1:
                    raise
