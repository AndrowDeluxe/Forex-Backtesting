"""Fortschritt der Teamaufgabe auf die Notion-Seite in "ELITE 3" schreiben.

Die Seite ist ein Eintrag (Art = Aufgabe) in der ELITE-3-Datenbank des
Trading Fusion Cockpits; ihre ID liegt in notion_page.json. Alles wird nur
ANGEHAENGT (Protokoll), nichts ueberschrieben.
"""

import json
from datetime import datetime
from pathlib import Path

from fusion_lab.notion.client import Notion, date, load_ids, multi, rich, select, title

PAGE_FILE = Path(__file__).resolve().parent / "notion_page.json"
TITLE = "Gruppenaufgabe: profitable Strategie (Mikrostruktur & Liquidität)"


def _rt(text: str, bold: bool = False) -> list:
    return [{"type": "text", "text": {"content": text[:2000]}, "annotations": {"bold": bold}}]


def block(kind: str, text: str = "", **extra) -> dict:
    body = {"rich_text": _rt(text)} if kind != "divider" else {}
    body.update(extra)
    return {"object": "block", "type": kind, kind: body}


def h2(t): return block("heading_2", t)
def h3(t): return block("heading_3", t)
def p(t): return block("paragraph", t)
def li(t): return block("bulleted_list_item", t)
def todo(t, done=False): return block("to_do", t, checked=done)
def callout(t, emoji="💡"): return block("callout", t, icon={"type": "emoji", "emoji": emoji})
def divider(): return {"object": "block", "type": "divider", "divider": {}}


def table(rows: list[list[str]], header: bool = True) -> dict:
    width = max(len(r) for r in rows)
    return {"object": "block", "type": "table", "table": {
        "table_width": width, "has_column_header": header, "has_row_header": False,
        "children": [{"object": "block", "type": "table_row", "table_row": {
            "cells": [_rt(str(c)) for c in r + [""] * (width - len(r))]}} for r in rows]}}


def page_id(page_file: Path = PAGE_FILE) -> str:
    return json.loads(page_file.read_text(encoding="utf-8"))["page_id"]


def create_page(n: Notion | None = None, page_file: Path = PAGE_FILE, page_title: str = TITLE,
                art: str = "Aufgabe", thema=("Struktur/Liquidität", "Strategie", "Execution"),
                assets=("EUR", "GBP", "JPY", "AUD", "USD", "Indizes"),
                beitrag: str = "Claude rechnet Backtests nach Briefing, protokolliert hier laufend.") -> str:
    if page_file.exists():
        return page_id(page_file)
    n = n or Notion()
    db = load_ids()["elite3"]
    page = n.add_row(db, {
        "Titel": title(page_title),
        "Art": select(art),
        "Datum": date(datetime.now().date().isoformat()),
        "Thema": multi(*thema),
        "Assets": multi(*assets),
        "Status": select("in Arbeit"),
        "Bot-Beitrag": rich(beitrag),
    })
    page_file.write_text(json.dumps({"page_id": page["id"], "url": page.get("url")}, indent=2),
                         encoding="utf-8")
    return page["id"]


def append(blocks: list[dict], n: Notion | None = None, page_file: Path = PAGE_FILE) -> None:
    n = n or Notion()
    pid = page_id(page_file)
    for i in range(0, len(blocks), 90):
        n.req("PATCH", f"/blocks/{pid}/children", {"children": blocks[i:i + 90]})


def log(text: str, emoji: str = "🕒", page_file: Path = PAGE_FILE) -> None:
    """Ein Protokolleintrag mit Zeitstempel."""
    append([callout(f"{datetime.now():%d.%m. %H:%M} — {text}", emoji)], page_file=page_file)


def set_props(page_file: Path = PAGE_FILE, **props) -> None:
    Notion().req("PATCH", f"/pages/{page_id(page_file)}", {"properties": props})
