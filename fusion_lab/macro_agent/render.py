"""Lesbare Fassung des Fact Sheets (Markdown), Reihenfolge wie ein SMT-Report.

Jede Zahl kommt unveraendert aus dem Fact Sheet, nur formatiert (deutsches Komma);
tests/test_macro_agent.py prueft, dass jede Tabellenzahl im Zahlenregister steht.
"""

from __future__ import annotations

from fusion_lab.macro_data.sources import G8

from .analytics.markets import MARKETS

MARK = {"PASS": "✓", "FAIL": "✗", "n.v.": "–"}
SIDE_LABEL = {"long": "long", "short": "short"}
PROFILE_ROWS = [("Leitzins", "policy_rate", "value", 2), ("2J", "2y", "value", 2),
                ("Δ 2J 1W (bp)", "2y", "chg_5d_bp", 1), ("10J", "10y", "value", 2),
                ("Δ 10J 1W (bp)", "10y", "chg_5d_bp", 1), ("Kurve 10J−2J", "curve_10y_2y", "value", 2),
                ("Pricing 2J−Leitzins", "pricing_2y_minus_policy", "value", 2),
                ("Δ Pricing 1W (bp)", "pricing_2y_minus_policy", "chg_5d_bp", 1),
                ("Inflation j/j", "cpi_yoy", "value", 1), ("Kern j/j", "core_yoy", "value", 1),
                ("Dienste j/j", "services_yoy", "value", 1), ("Arbeitslosigkeit", "unemployment", "value", 1),
                ("BIP q/q", "gdp_qoq", "value", 2)]


def fmt(v, digits: int = 2) -> str:
    if v is None:
        return "–"
    return f"{v:,.{digits}f}".replace(",", " ").replace(".", ",").replace(" ", ".")


def _table(header: list[str], rows: list[list[str]]) -> list[str]:
    return ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)] + ["| " + " | ".join(r) + " |" for r in rows]


def _state(z: dict) -> list[str]:
    lines = [f"## 1. Zustand: **{z['state']}** (vor einer Woche: {z['state_week_ago']})", ""]
    rows = []
    for kind, conds in (("TAIL", z["tail"]), ("ALT", z["alt"])):
        for c in conds:
            hit = "–" if c["hit"] is None else ("ja" if c["hit"] else "nein")
            rows.append([kind, c["name"], fmt(c["value"]), f"{c['op']} {fmt(c['threshold'])}", hit])
    lines += _table(["Zustand", "Bedingung", "Ist", "Schwelle", "erfüllt"], rows)
    lv = z["levels"]
    lines += ["", f"DXY {fmt(lv['dxy'])} · S&P 500 {fmt(lv['spx'])} · Gold (Future) {fmt(lv['gold'])} · "
                  f"Brent {fmt(lv['brent'])}",
              f"Dollar als Hafen (letzte 5 Tage): {', '.join(z['dollar_haven_days']) or 'kein Tag'}", ""]
    return lines


def _regime(sheet: dict) -> list[str]:
    r, f = sheet["regime"], sheet["filter"]
    lines = ["## 2. Regime und Filter", ""]
    if "labels" in r:
        g, i = r["growth"], r["inflation"]
        lines.append(f"Regimekarte: **{r['labels']['joint']}** · Wachstum {fmt(g['yoy'])} % "
                     f"(Vorperiode {fmt(g['yoy_prev_period'])}), Inflation {fmt(i['yoy'])} % "
                     f"(Vorperiode {fmt(i['yoy_prev_period'])})")
    else:
        lines.append(f"Regimekarte: n.v. ({r.get('fehler')})")
    gz = f.get("gold_zinskurve", {})
    if "regime" in gz:
        richtung = {1: "nur long", -1: "nur short", 0: "beide"}[gz["richtung"]]
        lines.append(f"Gold-Zinskurven-Filter: {gz['regime']} → {richtung}")
    zf = f.get("zins_fx", {})
    if zf and "fehler" not in zf:
        word = {1: "long", -1: "short", 0: "–", None: "n.v."}
        lines += ["", *_table(["Markt", "Zins-Momentum", "Carry"],
                              [[m, word[v["momentum"]], word[v["carry"]]] for m, v in zf.items()])]
    return lines + [""]


def _profiles(laender: dict) -> list[str]:
    rows = []
    for label, q, field, digits in PROFILE_ROWS:
        cells = [label]
        for land in G8:
            node = laender[land].get(q)
            v = None if not node else node.get(field)
            cells.append(fmt(v, digits) + ("*" if node and node.get("stale") else ""))
        rows.append(cells)
    return ["## 3. Länderprofile", "", *_table(["", *G8], rows), "", "\\* = älter als erlaubt (siehe Datenlücken)", ""]


def _fed(fp: dict) -> list[str]:
    rows = [[m, fmt(v["implied"], 3), fmt(v["priced_bp"], 1), fmt(v["chg_5d_bp"], 1)] for m, v in fp["months"].items()]
    return [f"## 4. Fed-Pfad (Fed-Funds-Futures, effektiv {fmt(fp['effective'])})", "",
            *_table(["Liefermonat", "impliziert", "gepreist (bp)", "Δ 1W (bp)"], rows), ""]


def _gate_cell(g: dict) -> str:
    return " ".join(f"{k}{MARK[g[k]]}" for k in ("R", "P", "B", "F")) + f" ({g['pass']}/{g['verfuegbar']})"


def _markets(mk: dict) -> list[str]:
    rows, inputs = [], []
    for m in MARKETS:
        st, g = mk[m]["kurs"], mk[m]["gates"]
        if st is None:
            rows.append([m, "–", "–", "–", "–", "–", _gate_cell(g["long"]), _gate_cell(g["short"])])
            continue
        digits = 5 if st["close"] < 20 else 2
        rows.append([m, fmt(st["close"], digits), fmt(st["ret_5d_pct"]), fmt(st["ret_20d_pct"]),
                     fmt(st["dist_sma20_pct"]), fmt(st["atr14"], digits), _gate_cell(g["long"]), _gate_cell(g["short"])])
        i = g["inputs"]
        inputs.append([m, i["R"]["basis"], fmt(i["R"]["chg_bp"], 1), fmt(i["B"].get("diff")),
                       fmt(i["F"]["base"], 1), fmt(i["F"]["quote"], 1)])
    return ["## 5. Märkte und Daten-Gates (R/P/B/F; M bewertet der Agent)", "",
            *_table(["Markt", "Kurs", "1W %", "20T %", "zu SMA20 %", "ATR14", "long", "short"], rows), "",
            "Gate-Grundlagen:", "",
            *_table(["Markt", "R-Basis", "Δ 1W (bp)", "G8 Basis−Quote", "COT 3J Basis", "COT 3J Quote"], inputs), ""]


def _positioning(pos: dict) -> list[str]:
    rows = [[k, fmt(v["net"], 0), fmt(v["chg_1w"], 0), fmt(v["cot_26w"], 1), fmt(v["cot_3y"], 1), v["date"]]
            for k, v in pos.items() if v]
    return ["## 6. Positionierung (CFTC, Leveraged Funds; Gold Managed Money)", "",
            *_table(["", "Netto", "Δ 1W", "COT 26W", "COT 3J", "veröffentlicht"], rows), ""]


def _g8(sheet: dict) -> list[str]:
    if not sheet["g8"]:
        return ["## 7. G8-Stärke", "", f"n.v. ({sheet['g8_stand']})", ""]
    ranked = sorted(sheet["g8"].items(), key=lambda kv: -kv[1])
    return [f"## 7. G8-Stärke (Nachbau, Stand {sheet['g8_stand']})", "",
            *_table(["Rang", "Währung", "Score"], [[str(i + 1), c, fmt(v)] for i, (c, v) in enumerate(ranked)]), ""]


def _calendar(k: dict) -> list[str]:
    up = [[e["zeit_utc"], e["waehrung"], e["titel"], e["impact"], e["konsens"] or "–", e["vorwert"] or "–"]
          for e in k["naechste_72h"]]
    su = [[e["zeit_utc"], e["waehrung"], e["titel"], fmt(e["konsens"]), fmt(e["ist"]), fmt(e["ueberraschung"])]
          for e in k["ueberraschungen_7t"]]
    return [f"## 8. Kalender (Referenz {k.get('referenz_utc', '–')} UTC)", "", "**Nächste 72 h (High/Medium)**", "",
            *(_table(["Zeit UTC", "Währung", "Termin", "Impact", "Konsens", "Vorwert"], up) if up else ["keine"]), "",
            "**Überraschungen letzte 7 Tage (Ist − Konsens)**", "",
            *(_table(["Zeit UTC", "Währung", "Termin", "Konsens", "Ist", "Überraschung"], su) if su else ["keine"]), ""]


def markdown(sheet: dict) -> str:
    lines = [f"# Makro Fact Sheet – Stand {sheet['stand']}", "",
             f"Erzeugt {sheet['erzeugt']} · {len(sheet['register'])} Zahlen im Register · "
             "Quelle: fusion_lab/macro_data + Dukascopy", ""]
    lines += _state(sheet["zustand"]) + _regime(sheet) + _profiles(sheet["laender"]) + _fed(sheet["fed_pfad"])
    lines += _markets(sheet["maerkte"]) + _positioning(sheet["positionierung"]) + _g8(sheet)
    lines += _calendar(sheet["kalender"])
    lines += ["## 9. Datenlücken", "", *[f"- {g}" for g in sheet["datenluecken"]], ""]
    return "\n".join(lines)
