"""Duenner Notion-API-Client (Integration-Token, kein MCP) -- damit auch
geplante Bot-Laeufe ohne offene Claude-Session ins Cockpit schreiben koennen."""

import json
import re
import time
from pathlib import Path

import requests

from fusion_lab._secrets import _section

API = "https://api.notion.com/v1"
# Bewusst die stabile 2022er Version: Datenbanken direkt mit "properties"
# (ab 2025-09-03 laufen sie ueber "data sources" -- fuer uns kein Vorteil).
VERSION = "2022-06-28"
IDS_FILE = Path(__file__).resolve().parent / "cockpit_ids.json"


def load_notion_config() -> dict:
    return _section("notion", ("token", "root_page"))


def page_id_from(url_or_id: str) -> str:
    """Notion-Link oder ID -> 32-stellige ID (letzter Hex-Block im Link)."""
    hexes = re.findall(r"[0-9a-f]{32}", url_or_id.replace("-", "").lower())
    if not hexes:
        raise ValueError(f"Keine Notion-Seiten-ID in {url_or_id!r} gefunden.")
    return hexes[-1]


class Notion:
    def __init__(self, token: str | None = None):
        token = token or load_notion_config()["token"]
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {token}",
                               "Notion-Version": VERSION,
                               "Content-Type": "application/json"})

    def req(self, method: str, path: str, body: dict | None = None) -> dict:
        for attempt in range(6):
            r = self.s.request(method, API + path, data=json.dumps(body) if body else None, timeout=60)
            if r.status_code in (429, 502, 503, 504):
                time.sleep(float(r.headers.get("Retry-After", 2 ** attempt)))
                continue
            if not r.ok:
                raise RuntimeError(f"Notion {method} {path}: {r.status_code} {r.text[:400]}")
            return r.json()
        r.raise_for_status()
        return r.json()

    def children(self, block_id: str) -> list[dict]:
        out, cursor = [], None
        while True:
            q = "?page_size=100" + (f"&start_cursor={cursor}" if cursor else "")
            data = self.req("GET", f"/blocks/{block_id}/children{q}")
            out += data["results"]
            if not data.get("has_more"):
                return out
            cursor = data["next_cursor"]

    def add_row(self, database_id: str, properties: dict, children: list | None = None) -> dict:
        body = {"parent": {"database_id": database_id}, "properties": properties}
        if children:
            body["children"] = children[:100]
        return self.req("POST", "/pages", body)


def load_ids() -> dict:
    return json.loads(IDS_FILE.read_text(encoding="utf-8")) if IDS_FILE.exists() else {}


# --- kleine Helfer fuer Property-Werte -------------------------------------

def title(text: str) -> dict:
    return {"title": [{"text": {"content": text[:2000]}}]}


def rich(text: str) -> dict:
    return {"rich_text": [{"text": {"content": text[:2000]}}]}


def select(name: str) -> dict:
    return {"select": {"name": name}}


def multi(*names: str) -> dict:
    return {"multi_select": [{"name": n} for n in names]}


def date(iso: str) -> dict:
    return {"date": {"start": iso}}


def para(text: str) -> dict:
    return {"object": "block", "type": "paragraph", "paragraph": rich(text)}
