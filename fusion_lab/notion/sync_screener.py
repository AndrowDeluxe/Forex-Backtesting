"""Schreibt den Tagesbericht des Aktien- bzw. Krypto-Screeners auf eine eigene Seite im Trading Fusion Cockpit.
Seite wird beim ersten Lauf unter der Cockpit-Startseite angelegt (ID in cockpit_ids.json), danach jeden Tag
geleert und neu befuellt.

    python -m fusion_lab.screener aktien --notion
"""

from __future__ import annotations

import json

from fusion_lab.notion.client import IDS_FILE, Notion, load_ids, load_notion_config, page_id_from
from fusion_lab.notion.sync_regime import _block, _bullets, _rt, _table
from fusion_lab.screener.report import ICON, SZ_NAME, fmt, price, scenario_line

PAGES = {"aktien": ("screener_aktien", "📈 Aktien-Screener"), "krypto": ("screener_krypto", "🪙 Krypto-Screener")}


def _page(n: Notion, kind: str) -> str:
    key, title_ = PAGES[kind]
    ids = load_ids()
    if ids.get(key):
        return ids[key]
    root = ids.get("root_page") or page_id_from(load_notion_config()["root_page"])
    page = n.req("POST", "/pages", {"parent": {"page_id": root},
                                    "properties": {"title": {"title": [{"text": {"content": title_}}]}}})
    ids[key] = page["id"]
    IDS_FILE.write_text(json.dumps(ids, indent=2, ensure_ascii=False), encoding="utf-8")
    return page["id"]


def blocks(r: dict) -> list[dict]:
    k = r["kontext"]
    out = [_block("heading_2", f"Stand {r['stand']} · {r['status']} · Version {r['version']}")]
    if r["screener"] == "aktien":
        out.append(_block("paragraph", f"SPY {price(k['spy']['kurs'])} ({k['spy']['trend']})"))
    else:
        f = k.get("fear_greed") or {}
        out.append(_block("paragraph", f"BTC {price(k['btc']['kurs'])} ({k['btc']['trend']}) · Fear & Greed "
                                       f"{f.get('wert', '–')} ({f.get('einstufung', '–')})"))
    sig = r["signale"]
    out.append(_block("paragraph", f"🟢 {sig.get('KAUFEN', 0)} KAUFEN · 🟡 {sig.get('HALTEN', 0)} HALTEN · "
                                   f"🔴 {sig.get('VERKAUFEN', 0)} VERKAUFEN (≥ 65 / ≤ 35)"))
    rows = [[[_rt(row["index"])], [_rt(fmt(row["gesamt"], 0))], [_rt(row["signal"])], [_rt(price(row["kurs"]))]]
            for row in r["tabelle"][:15]]
    out.append(_table(["Titel", "Score", "Signal", "Kurs"], rows))
    out.append(_block("heading_2", "Tiefen-Analyse"))
    for c in r["tief"]:
        llm = c.get("llm") or {}
        ok = llm and "fehler" not in llm
        out.append(_block("heading_3", f"{ICON[c['signal']]} {c['objekt']} · Score {fmt(c['gesamt'], 0)} · {c['signal']}"))
        items = [scenario_line("A", c["szenarien"].get("A")), scenario_line("B", c["szenarien"].get("B"))]
        if ok:
            items += [f"Gewählt: {llm['szenario']} {SZ_NAME[llm['szenario']]} ({llm['ueberzeugung']}) – {llm['szenario_grund']}",
                      f"Stimmung {llm['sentiment']:+d}: {llm['sentiment_grund']}",
                      f"Hauptrisiko: {llm['hauptrisiko']}"]
        else:
            items.append("LLM-Einordnung: n.v.")
        out += _bullets(items)
    return out


def sync(r: dict) -> str:
    n = Notion()
    pid = _page(n, r["screener"])
    for ch in n.children(pid):
        n.req("DELETE", f"/blocks/{ch['id']}")
    bl = blocks(r)
    for i in range(0, len(bl), 90):
        n.req("PATCH", f"/blocks/{pid}/children", {"children": bl[i:i + 90]})
    return f"Notion: {PAGES[r['screener']][1]} aktualisiert ({len(bl)} Blöcke)"
