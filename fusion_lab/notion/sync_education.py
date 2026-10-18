"""Spiegelt fusion_lab/notion/makro_education.py in die Notion-DB "📚 Makro-Education".

Je Thema eine Zeile (Eigenschaften) plus Seiteninhalt (Kernregeln als Liste).
Idempotent über den Titel: vorhandene Seiten werden aktualisiert, ihr Inhalt
ersetzt.

    python -m fusion_lab.notion.setup_cockpit      # einmalig: DB anlegen
    python -m fusion_lab.notion.sync_education
"""

from __future__ import annotations

import sys

from fusion_lab.notion.client import Notion, load_ids, multi, rich, select, title
from fusion_lab.notion.makro_education import TOPICS


def _bullet(text: str) -> dict:
    return {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": rich(text)}


def _heading(text: str) -> dict:
    return {"object": "block", "type": "heading_3", "heading_3": rich(text)}


def _para(text: str) -> dict:
    return {"object": "block", "type": "paragraph", "paragraph": rich(text)}


def props(t: dict) -> dict:
    p = {
        "Thema": title(t["titel"]), "Nr": {"number": t["nr"]}, "Kurz erklärt": rich(t["kurz"]),
        "Wie es wirkt": rich(t["wirkung"]), "Rolle im Report": multi(*t["rolle"]),
        "Datenquellen": rich(t["daten"]), "Status": select(t["status"]),
        "Quellen (OneNote/Repo)": rich(t["quellen"]),
    }
    p["Widersprüche"] = rich(t["widerspruch"] or "–")
    return p


def body(t: dict) -> list[dict]:
    blocks = [_para(t["kurz"]), _heading("Wie es wirkt"), _para(t["wirkung"]), _heading("Kernregeln")]
    blocks += [_bullet(r) for r in t["regeln"]]
    if t["widerspruch"]:
        blocks += [_heading("Offen / widersprüchlich"), _para(t["widerspruch"])]
    blocks += [_heading("Daten"), _para(t["daten"])]
    return blocks


def existing(n: Notion, db: str) -> dict[str, str]:
    out, cursor = {}, None
    while True:
        data = n.req("POST", f"/databases/{db}/query", {"page_size": 100, **({"start_cursor": cursor} if cursor else {})})
        for p in data["results"]:
            out["".join(x["plain_text"] for x in p["properties"]["Thema"]["title"])] = p["id"]
        if not data.get("has_more"):
            return out
        cursor = data["next_cursor"]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ids = load_ids()
    if "education" not in ids:
        raise SystemExit("DB fehlt -- erst: python -m fusion_lab.notion.setup_cockpit")
    n = Notion()
    have = existing(n, ids["education"])
    new = upd = 0
    for t in TOPICS:
        if t["titel"] in have:
            pid = have[t["titel"]]
            n.req("PATCH", f"/pages/{pid}", {"properties": props(t)})
            for b in n.children(pid):
                n.req("DELETE", f"/blocks/{b['id']}")
            n.req("PATCH", f"/blocks/{pid}/children", {"children": body(t)})
            upd += 1
        else:
            n.add_row(ids["education"], props(t), body(t))
            new += 1
    print(f"Makro-Education: {new} neu, {upd} aktualisiert")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
