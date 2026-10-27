"""Minimal Homebox API client for looking up items to label.

Configuration comes from environment variables or a `.env` file next to this
script:

    HOMEBOX_URL=http://homebox.local:7745
    HOMEBOX_TOKEN=...            # API key (Settings -> API keys), or:
    HOMEBOX_USERNAME=you@example.com
    HOMEBOX_PASSWORD=...
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


class HomeboxError(Exception):
    pass


@dataclass
class Item:
    id: str
    asset_id: str
    name: str
    location: str

    def tag_url(self, base_url: str) -> str:
        return f"{base_url.rstrip('/')}/a/{self.asset_id}"


def load_env(path: Path = Path(__file__).with_name(".env")):
    """Load KEY=VALUE lines into os.environ without overriding real env vars."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def format_asset_id(value: str | int) -> str:
    """Normalise 1, "1", "000001" or "000-001" to Homebox's "000-001" form."""
    digits = str(value).replace("-", "").strip()
    if not digits.isdigit():
        raise ValueError(f"not an asset ID: {value!r}")
    digits = digits.zfill(6)
    return f"{digits[:-3]}-{digits[-3:]}"


class Homebox:
    def __init__(self, url: str, token: str | None = None,
                 username: str | None = None, password: str | None = None):
        self.url = url.rstrip("/")
        self.token = token
        self.username = username
        self.password = password
        self._items_path = None

    @classmethod
    def from_env(cls) -> "Homebox":
        load_env()
        url = os.environ.get("HOMEBOX_URL")
        if not url:
            raise HomeboxError("HOMEBOX_URL is not set (put it in .env)")
        return cls(url, os.environ.get("HOMEBOX_TOKEN"),
                   os.environ.get("HOMEBOX_USERNAME"), os.environ.get("HOMEBOX_PASSWORD"))

    def _call(self, method: str, path: str, body=None, auth=True, query=None):
        url = f"{self.url}/api{path}"
        if query:
            url += "?" + urllib.parse.urlencode(query, doseq=True)
        headers = {"Accept": "application/json"}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        if auth:
            headers["Authorization"] = self._auth_header()
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as e:
            raise HomeboxError(f"{method} {path} -> HTTP {e.code}: {e.read()[:200]!r}") from None
        except urllib.error.URLError as e:
            raise HomeboxError(f"cannot reach {self.url}: {e.reason}") from None
        return json.loads(raw) if raw else None

    def _auth_header(self) -> str:
        if not self.token:
            if not (self.username and self.password):
                raise HomeboxError("set HOMEBOX_TOKEN, or HOMEBOX_USERNAME and HOMEBOX_PASSWORD")
            resp = self._call("POST", "/v1/users/login", auth=False, body={
                "username": self.username, "password": self.password, "stayLoggedIn": False})
            self.token = resp["token"]
        return self.token if self.token.lower().startswith("bearer ") else f"Bearer {self.token}"

    def status(self) -> dict:
        return self._call("GET", "/v1/status", auth=False)

    def whoami(self) -> dict:
        """The logged-in user; a cheap way to check the credentials."""
        return self._call("GET", "/v1/users/self")

    def _item_from(self, data: dict) -> Item:
        where = data.get("location") or data.get("parent") or {}
        return Item(id=data["id"], asset_id=format_asset_id(data.get("assetId") or 0),
                    name=data.get("name", ""), location=where.get("name", ""))

    def by_asset_id(self, asset_id: str | int) -> Item:
        aid = format_asset_id(asset_id)
        page = self._call("GET", f"/v1/assets/{aid}")
        items = page.get("items") or []
        if not items:
            raise HomeboxError(f"no item with asset ID {aid}")
        return self._item_from(items[0])

    def search(self, query: str = "", page_size: int = 100) -> list[Item]:
        """Items, boxes and locations matching `query` (all when empty), by asset ID."""
        items, page = [], 1
        while True:
            resp = self._list({"q": query, "page": page, "pageSize": page_size,
                               "orderBy": "assetId", "orderDirection": "asc"})
            items += [self._item_from(i) for i in resp.get("items") or []]
            if len(items) >= resp.get("total", 0) or not resp.get("items"):
                break
            page += 1
        if self._items_path == "/v1/entities":
            # v0.26+ leaves location-like entities (rooms, boxes, cabinets) out
            # of the normal listing; they come back only with isLocation=true.
            locs = self._call("GET", "/v1/entities", query={"isLocation": "true"})
            items += [self._item_from(i) for i in locs.get("items") or []
                      if query.lower() in i.get("name", "").lower()]
        seen = set()
        unique = [i for i in items if not (i.id in seen or seen.add(i.id))]
        return sorted(unique, key=lambda i: i.asset_id)

    def _list(self, query):
        # Newer Homebox calls items "entities"; fall back to the old path.
        paths = [self._items_path] if self._items_path else ["/v1/entities", "/v1/items"]
        for i, path in enumerate(paths):
            try:
                resp = self._call("GET", path, query=query)
                self._items_path = path
                return resp
            except HomeboxError as e:
                if "HTTP 404" not in str(e) or i == len(paths) - 1:
                    raise
