"""Schreibt das Makro Fact Sheet als Eintrag in die Notion-DB "🌍 Makro-Übersicht".
Idempotent ueber den Titel (wie sync_regime): Eigenschaften aktualisieren, Inhalt neu aufbauen.

    python -m fusion_lab.macro_agent --notion
"""

from __future__ import annotations

from fusion_lab.macro_agent.analytics.markets import MARKETS
from fusion_lab.macro_agent.factors import FACTORS
from fusion_lab.macro_agent.render import FACTOR_LABEL, MARK, PROFILE_ROWS, fmt
from fusion_lab.macro_data.sources import G8
from fusion_lab.notion.client import Notion, date, load_ids, multi, rich, select, title
from fusion_lab.notion.sync_regime import _block, _bullets, _rt, _table

PAGE_TITLE = "Makro Fact Sheet"
STATE_COLOR = {"BASE": "default", "ALT": "green", "TAIL": "red"}


def _cells(values: list[str]) -> list[list[dict]]:
    return [[_rt(v)] for v in values]


def _gate_text(g: dict | None) -> str:
    if not g:
        return "–"
    return " ".join(f"{k}{MARK[g[k]]}" for k in ("R", "P", "F")) + f" {g['pass']}/{g['verfuegbar']}"


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

    sc = sheet["scorecard"]
    ranked = sorted(sc["waehrungen"].items(), key=lambda kv: (kv[1]["rang"] is None, kv[1]["rang"] or 0))
    rows = [_cells([c, *[fmt(v[f]) for f in FACTORS], fmt(v["score"]), fmt(v["cot_3y"], 1),
                    "long gesperrt" if v["veto_long"] else ("short gesperrt" if v["veto_short"] else "–")])
            for c, v in ranked]
    blocks += [_block("heading_2", f"Scorecard (strategisch, 1–3 Monate) – {sc['einsatz']}"),
               _table(["", *[FACTOR_LABEL[f] for f in FACTORS], "Score", "COT 3J", "Veto"], rows)]

    tk = sheet["taktisch"]
    blocks += [_block("heading_2", f"Fed je Sitzung (effektiv {fmt(tk['fed']['effektiv'])})"),
               _table(["Sitzung", "Δ bp", "Wahrsch. %", "vor 1W %", "bezahlt"],
                      [_cells([s["sitzung"], fmt(s["bp"], 1), fmt(s["pct"], 1), fmt(s.get("pct_vor_1w"), 1),
                               "ja" if s["bezahlt"] else "nein"]) for s in tk["fed"]["sitzungen"]]),
               _block("heading_2", "Andere Notenbanken (1J − Leitzins)"),
               _table(["", "Leitzins", "1J", "gepreist 12M bp", "Δ 1W bp"],
                      [_cells([l, fmt(v["leitzins"]), fmt(v["1y"]), fmt(v["gepreist_12m_bp"], 1), fmt(v["chg_1w_bp"], 1)])
                       for l, v in tk["notenbanken"].items() if v]),
               _block("heading_2", "Rohstoff-Schalter"),
               *_bullets([f"{c}: {v['rohstoff']} {fmt(v['kurs'])}, 60T {fmt(v['ret_60d_pct'])} % ({v['trend']})"
                          + (f", Schwelle {fmt(v['schwelle'], 0)} ({fmt(v['abstand_pct'])} %)" if "schwelle" in v else "")
                          for c, v in tk["rohstoffe"].items() if v])]

    rows = []
    for m in MARKETS:
        node = sheet["maerkte"][m]
        st, g, view = node["kurs"], node["gates"], node.get("scorecard")
        close = "–" if st is None else fmt(st["close"], 5 if st["close"] < 20 else 2)
        rows.append(_cells([m, close, "–" if not view else fmt(view["diff"]),
                            _gate_text(g and g["long"]), _gate_text(g and g["short"])]))
    blocks += [_block("heading_2", "Märkte und Gates (R/P/F aus der Scorecard, M bewertet der Agent)"),
               _table(["Markt", "Kurs", "Score Basis−Quote", "long", "short"], rows)]

    rk = sheet["risiko"]
    b = rk["buendel"]
    blocks += [_block("heading_2", "Risiko-Budget"),
               *_bullets([f"{i['markt']} {i['seite']} (Score-Diff {fmt(i['diff'])}, Größe rel. {fmt(i['groesse_rel'])})"
                          for i in rk["ideen"]] or ["keine Idee über der Schwelle"]),
               _block("paragraph", "Netto je Währung: " + (", ".join(f"{c} {fmt(v)}" for c, v in b["netto"].items()) or "–")
                      + f" · über Deckel {fmt(b['deckel'], 1)}: " + (", ".join(b["ueber_deckel"]) or "keine"))]

    rows = []
    for label, q, field, digits in PROFILE_ROWS:
        rows.append(_cells([label] + [fmt((sheet["laender"][l].get(q) or {}).get(field), digits) for l in G8]))
    blocks += [_block("heading_2", "Länderprofile"), _table(["", *G8], rows)]

    k = sheet["kalender"]
    blocks += [_block("heading_2", "Kalender nächste 7 Tage (High)"),
               *_bullets([f"{e['zeit_utc']} UTC {e['waehrung']} {e['titel']} (Konsens {e['konsens'] or '–'})"
                          for e in k["naechste_7t"]] or ["keine"]),
               _block("heading_2", "Datenlücken"), *_bullets(sheet["datenluecken"])]
    return blocks


def props(sheet: dict) -> dict:
    z, rk = sheet["zustand"], sheet["risiko"]
    ideas = ", ".join(f"{i['markt']} {i['seite']}" for i in rk["ideen"]) or "keine"
    summary = (f"Zustand {z['state']}. Scorecard-Ideen: {ideas}. Bündel-Haupttreiber: "
               f"{rk['buendel']['haupttreiber'] or '–'}. Scorecard: {sheet['scorecard']['einsatz']}.")
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
