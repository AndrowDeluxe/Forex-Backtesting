"""Markdown-Notizen aus knowledge/ als Unterseiten des Ordners "📁 Optimierte Edges und Tests"
im Notion-Cockpit veroeffentlichen (Nutzerwunsch 2026-10-16). Quelle der Wahrheit bleibt die
Datei im Repo; ein erneuter Lauf ersetzt die Notion-Seite gleichen Titels.

    python -m fusion_lab.notion.optimierte_edges knowledge/projects/optimierte-edges-uebersicht.md ...
"""

import json
import re
import sys
from pathlib import Path

from fusion_lab.notion.client import IDS_FILE, Notion, load_ids

FOLDER_TITLE = "📁 Optimierte Edges und Tests"
ICONS = {"uebersicht": "🧭", "oel": "🛢️", "zarattini": "📈", "orb": "🔔"}


def _clean(text: str) -> str:
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    return text.replace("**", "").replace("`", "")


def _rt(text: str) -> list:
    text = _clean(text)
    return [{"type": "text", "text": {"content": text[i:i + 2000]}} for i in range(0, len(text), 2000)] or \
        [{"type": "text", "text": {"content": ""}}]


def _block(kind: str, text: str) -> dict:
    return {"object": "block", "type": kind, kind: {"rich_text": _rt(text)}}


def _table(rows: list[list[str]]) -> dict:
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    return {"object": "block", "type": "table", "table": {
        "table_width": width, "has_column_header": True, "has_row_header": False,
        "children": [{"object": "block", "type": "table_row",
                      "table_row": {"cells": [_rt(c.strip()) for c in r]}} for r in rows[:100]]}}


def md_to_blocks(text: str) -> tuple[str, list[dict]]:
    lines = text.splitlines()
    page_title, blocks, para, table = None, [], [], []

    def flush():
        nonlocal para, table
        if para:
            blocks.append(_block("paragraph", " ".join(para)))
            para = []
        if table:
            blocks.append(_table(table))
            table = []

    for raw in lines:
        line = raw.strip()
        if line.startswith("|"):
            if para:
                blocks.append(_block("paragraph", " ".join(para))); para = []
            cells = [c for c in line.strip("|").split("|")]
            if not all(re.fullmatch(r"\s*:?-{2,}:?\s*", c) for c in cells):
                table.append(cells)
            continue
        if table:
            flush()
        if not line:
            flush(); continue
        if line.startswith("# ") and page_title is None:
            page_title = _clean(line[2:]); continue
        m = re.match(r"^(#{1,3}) (.*)", line)
        if m:
            flush()
            blocks.append(_block({1: "heading_1", 2: "heading_2", 3: "heading_3"}[len(m.group(1))], m.group(2)))
        elif line.startswith(("- ", "* ")):
            flush(); blocks.append(_block("bulleted_list_item", line[2:]))
        elif re.match(r"^\d+\. ", line):
            flush(); blocks.append(_block("paragraph", line))   # Originalnummer behalten
        elif raw.startswith("  ") and blocks and blocks[-1]["type"] in ("bulleted_list_item", "paragraph") and not para:
            blk = blocks[-1][blocks[-1]["type"]]["rich_text"]
            blk[-1]["text"]["content"] += " " + _clean(line)
        else:
            para.append(line)
    flush()
    return page_title or "Notiz", blocks


def ensure_folder(n: Notion) -> str:
    ids = load_ids()
    if ids.get("optimierte_edges_folder"):
        return ids["optimierte_edges_folder"]
    page = n.req("POST", "/pages", {
        "parent": {"page_id": ids["root_page"]},
        "icon": {"type": "emoji", "emoji": "📁"},
        "properties": {"title": [{"text": {"content": FOLDER_TITLE}}]},
        "children": [_block("paragraph", "Optimierte Edges, Öl-Mechanismus und laufende Forward-Tests. "
                                         "Quelle der Wahrheit: knowledge/ im Repo; Seiten werden per "
                                         "fusion_lab/notion/optimierte_edges.py ersetzt, nicht von Hand gepflegt.")]})
    ids["optimierte_edges_folder"] = page["id"]
    IDS_FILE.write_text(json.dumps(ids, indent=2, ensure_ascii=False), encoding="utf-8")
    return page["id"]


def publish(md_path: str) -> str:
    n = Notion()
    folder = ensure_folder(n)
    page_title, blocks = md_to_blocks(Path(md_path).read_text(encoding="utf-8"))
    for b in n.children(folder):
        if b["type"] == "child_page" and b["child_page"]["title"] == page_title:
            n.req("PATCH", f"/pages/{b['id']}", {"archived": True})
    icon = next((v for k, v in ICONS.items() if k in md_path.lower()), "📄")
    page = n.req("POST", "/pages", {"parent": {"page_id": folder}, "icon": {"type": "emoji", "emoji": icon},
                                    "properties": {"title": [{"text": {"content": page_title}}]},
                                    "children": blocks[:100]})
    for i in range(100, len(blocks), 100):
        n.req("PATCH", f"/blocks/{page['id']}/children", {"children": blocks[i:i + 100]})
    return page.get("url", page["id"])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    for p in sys.argv[1:]:
        print(p, "->", publish(p))
