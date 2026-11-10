"""Schreibt das Makro Fact Sheet als Eintrag in die Notion-DB "🌍 Makro-Übersicht".
Idempotent ueber den Titel (wie sync_regime): Eigenschaften aktualisieren, Inhalt neu aufbauen.

    python -m fusion_lab.macro_agent --notion
"""

from __future__ import annotations

from fusion_lab.macro_agent.analytics.markets import MARKETS
from fusion_lab.macro_agent.render import MARK, PROFILE_ROWS, fmt
from fusion_lab.macro_data.sources import G8
from fusion_lab.notion.client import Notion, date, load_ids, multi, rich, select, title
from fusion_lab.notion.sync_regime import _block, _bullets, _rt, _table

PAGE_TITLE = "Makro Fact Sheet"
STATE_COLOR = {"BASE": "default", "ALT": "green", "TAIL": "red"}


def _cells(values: list[str]) -> list[list[dict]]:
    return [[_rt(v)] for v in values]


def _gate_text(g: dict) -> str:
    return " ".join(f"{k}{MARK[g[k]]}" for k in ("R", "P", "B", "F")) + f" {g['pass']}/{g['verfuegbar']}"


def build_blocks(sheet: dict) -> list[dict]:
    z = sheet["zustand"]
    blocks = [_block("callout", f"Zustand {z['state']} (vor einer Woche {z['state_week_ago']}) · Stand {sheet['stand']} "
                                f"· {len(sheet['register'])} Zahlen im Register", icon={"emoji": "🧭"}),
              _block("heading_2", "Zustand BASE / ALT / TAIL")]
    blocks.append(_table(["Bedingung", "Ist", "Schwelle", "erfüllt"],
                         [_cells([f"{k} {c['name']}", fmt(c["value"]), f"{c['op']} {fmt(c['threshold'])}",
                                  "–" if c["hit"] is None else ("ja" if c["hit"] else "nein")])
                          for k, conds in (("TAIL", z["tail"]), ("ALT", z["alt"])) for c in conds]))

    r = sheet["regime"]
    items = [f"Regimekarte: {r['labels']['joint']}" if "labels" in r else f"Regimekarte n.v. ({r.get('fehler')})"]
    gz = sheet["filter"].get("gold_zinskurve", {})
    if "regime" in gz:
        items.append(f"Gold-Zinskurven-Filter: {gz['regime']} (Richtung {gz['richtung']:+d})")
    blocks += [_block("heading_2", "Regime und Filter"), *_bullets(items)]

    rows = []
    for label, q, field, digits in PROFILE_ROWS:
        rows.append(_cells([label] + [fmt((sheet["laender"][l].get(q) or {}).get(field), digits) for l in G8]))
    blocks += [_block("heading_2", "Länderprofile"), _table(["", *G8], rows)]

    fp = sheet["fed_pfad"]
    blocks += [_block("heading_2", f"Fed-Pfad (effektiv {fmt(fp['effective'])})"),
               _table(["Liefermonat", "impliziert", "gepreist bp", "Δ 1W bp"],
                      [_cells([m, fmt(v["implied"], 3), fmt(v["priced_bp"], 1), fmt(v["chg_5d_bp"], 1)])
                       for m, v in fp["months"].items()])]

    rows = []
    for m in MARKETS:
        st, g = sheet["maerkte"][m]["kurs"], sheet["maerkte"][m]["gates"]
        close = "–" if st is None else fmt(st["close"], 5 if st["close"] < 20 else 2)
        week = "–" if st is None else fmt(st["ret_5d_pct"])
        rows.append(_cells([m, close, week, _gate_text(g["long"]), _gate_text(g["short"])]))
    blocks += [_block("heading_2", "Märkte und Daten-Gates (M bewertet der Agent)"),
               _table(["Markt", "Kurs", "1W %", "long", "short"], rows)]

    pos = sheet["positionierung"]
    blocks += [_block("heading_2", "Positionierung (COT-Index)"),
               _table(["", "Netto", "COT 26W", "COT 3J"],
                      [_cells([k, fmt(v["net"], 0), fmt(v["cot_26w"], 1), fmt(v["cot_3y"], 1)])
                       for k, v in pos.items() if v])]

    k = sheet["kalender"]
    blocks += [_block("heading_2", "Kalender nächste 72 h"),
               *_bullets([f"{e['zeit_utc']} UTC {e['waehrung']} {e['titel']} ({e['impact']}, Konsens {e['konsens'] or '–'})"
                          for e in k["naechste_72h"]] or ["keine"]),
               _block("heading_2", "Datenlücken"), *_bullets(sheet["datenluecken"])]
    return blocks


def props(sheet: dict) -> dict:
    z = sheet["zustand"]
    long_ok = [m for m, v in sheet["maerkte"].items() if v["gates"]["long"]["pass"] == 4]
    short_ok = [m for m, v in sheet["maerkte"].items() if v["gates"]["short"]["pass"] == 4]
    summary = (f"Zustand {z['state']}. 4/4 Daten-Gates long: {', '.join(long_ok) or 'keiner'}; "
               f"short: {', '.join(short_ok) or 'keiner'}.")
    return {"Thema": title(PAGE_TITLE), "Datum": date(sheet["stand"]),
            "Assets": multi("USD", "Gold", "Indizes", "Anleihen"), "Treiber": multi("Zinsen", "Inflation", "Wachstum"),
            "Zusammenfassung": rich(summary), "Quelle": select("Bot")}


def find_row(n: Notion, db: str) -> str | None:
    data = n.req("POST", f"/databases/{db}/query", {
        "filter": {"property": "Thema", "title": {"equals": PAGE_TITLE}}, "page_size": 5})
    return data["results"][0]["id"] if data["results"] else None


def sync(sheet: dict) -> str:
    ids = load_ids()
    n = Notion()
    blocks = build_blocks(sheet)
    page = find_row(n, ids["makro"])
    if page:
        n.req("PATCH", f"/pages/{page}", {"properties": props(sheet)})
        for b in n.children(page):
            n.req("DELETE", f"/blocks/{b['id']}")
    else:
        page = n.add_row(ids["makro"], props(sheet))["id"]
    for k in range(0, len(blocks), 50):
        n.req("PATCH", f"/blocks/{page}/children", {"children": blocks[k:k + 50]})
    return f"Makro Fact Sheet: https://www.notion.so/{page.replace('-', '')}"
