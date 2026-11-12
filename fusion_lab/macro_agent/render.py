"""Lesbare Fassung des Fact Sheets v2 (Markdown): Zustand → Regime → Scorecard → taktische Ebene →
Geopolitik/Realzinsen → Märkte/Gates → Risiko-Budget → Länderprofile → Positionierung → G8 → Kalender → Datenlücken.

Jede Zahl kommt unveraendert aus dem Fact Sheet, nur formatiert (deutsches Komma);
tests/test_macro_agent.py prueft, dass jede Tabellenzahl im Zahlenregister steht.
"""

from __future__ import annotations

from fusion_lab.macro_data.sources import G8

from .analytics.markets import MARKETS
from .factors import FACTORS

MARK = {"PASS": "✓", "FAIL": "✗", "n.v.": "–"}
FACTOR_LABEL = {"carry": "Carry", "zins_momentum": "Zins-Mom.", "preis_momentum": "Preis-Mom.",
                "value": "Value", "ueberraschung": "Überr."}
PROFILE_ROWS = [("Leitzins", "policy_rate", "value", 2), ("1J", "1y", "value", 2), ("2J", "2y", "value", 2),
                ("Δ 2J 1W (bp)", "2y", "chg_5d_bp", 1), ("10J", "10y", "value", 2),
                ("Δ 10J 1W (bp)", "10y", "chg_5d_bp", 1), ("Kurve 10J−2J", "curve_10y_2y", "value", 2),
                ("Pricing kurz−Leitzins", "pricing", "value", 2), ("Δ Pricing 1W (bp)", "pricing", "chg_5d_bp", 1),
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
    lines += ["", "TAIL bei 2 Treffern unter VIX/HY/Brent/OAT-Bund oder Stressindex (STLFSI) > 1.",
              f"DXY {fmt(lv['dxy'])} · S&P 500 {fmt(lv['spx'])} · Gold (Future) {fmt(lv['gold'])} · "
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


def _scorecard(sc: dict) -> list[str]:
    rows = []
    ranked = sorted(sc["waehrungen"].items(), key=lambda kv: (kv[1]["rang"] is None, kv[1]["rang"] or 0))
    for ccy, v in ranked:
        veto = "long gesperrt" if v["veto_long"] else ("short gesperrt" if v["veto_short"] else "–")
        rows.append([ccy, *[fmt(v[f]) for f in FACTORS], f"**{fmt(v['score'])}**",
                     "–" if v["rang"] is None else str(v["rang"]), fmt(v["cot_3y"], 1), veto])
    lines = [f"## 3. Scorecard (strategisch, 1–3 Monate, Stand {sc['tag']})", "",
             *_table(["Währung", *[FACTOR_LABEL[f] for f in FACTORS], "Score", "Rang", "COT 3J", "Veto"], rows), "",
             "Faktoren als Querschnitts-z-Werte, gleich gewichtet; Veto = Positionierung überlaufen (COT ≥ 90 / ≤ 10).",
             "COT 3J hier = Legacy Non-Commercials (wie im Backtest, Historie ab 2000). Abschnitt 8 zeigt nur "
             "Leveraged Funds; beide können stark abweichen (andere Gruppen, z. B. Asset Manager)."]
    t = sc.get("test")
    if t:
        key = t["kandidat"]
        is_, oos = t["is"][key], t.get("oos", {}).get(key)
        line = (f"**Backtest ({t['lock']}, {t['versuche']} Versuche):** IS 2007–2016 Sharpe {fmt(is_['sharpe'])}, "
                f"t {fmt(is_['t'])}")
        if oos:
            line += f"; OOS 2017–05/2026 Sharpe {fmt(oos['sharpe'])}, t {fmt(oos['t'])}"
        lines += ["", line + f". Einsatz: {sc['einsatz']}."]
    return lines + [""]


def _tactical(tk: dict) -> list[str]:
    fed = tk["fed"]
    rows = [[s["sitzung"], fmt(s["bp"], 1), fmt(s["pct"], 1), fmt(s.get("pct_vor_1w"), 1),
             "ja" if s["bezahlt"] else "nein"] for s in fed["sitzungen"]]
    lines = [f"## 4. Taktische Ebene", "", f"**Fed je Sitzung** (Futures, effektiv {fmt(fed['effektiv'])}; "
             "100 % = ein Schritt von 25 bp)", "",
             *_table(["Sitzung", "Δ bp", "Wahrsch. %", "vor 1W %", "≥ 75 % bezahlt"], rows), ""]
    rows = [[land, fmt(v["leitzins"]), v["leitzins_datum"], fmt(v["1y"]), fmt(v["gepreist_12m_bp"], 1),
             fmt(v["chg_1w_bp"], 1)] for land, v in tk["notenbanken"].items() if v]
    lines += ["**Andere Notenbanken** (Näherung 1J − Leitzins, kein OIS)", "",
              *_table(["", "Leitzins", "seit/Stand", "1J", "gepreist 12M (bp)", "Δ 1W (bp)"], rows), ""]
    rows = [[ccy, v["rohstoff"], fmt(v["kurs"]), fmt(v["ret_20d_pct"]), fmt(v["ret_60d_pct"]), v["trend"],
             "–" if "schwelle" not in v else f"{fmt(v['schwelle'], 0)} ({fmt(v['abstand_pct'])} %)"]
            for ccy, v in tk["rohstoffe"].items() if v]
    lines += ["**Rohstoff-Schalter**", "",
              *_table(["Währung", "Rohstoff", "Kurs", "20T %", "60T %", "Trend", "Schwelle (Abstand)"], rows), ""]
    return lines


def _gate_cell(g: dict | None) -> str:
    if not g:
        return "–"
    return " ".join(f"{k}{MARK[g[k]]}" for k in ("R", "P", "F")) + f" ({g['pass']}/{g['verfuegbar']})"


def _markets(mk: dict) -> list[str]:
    rows = []
    for m in MARKETS:
        st, g, sc = mk[m]["kurs"], mk[m]["gates"], mk[m].get("scorecard")
        diff = "–" if not sc else fmt(sc["diff"])
        if st is None:
            rows.append([m, "–", "–", fmt(mk[m]["vol_20d_pct"]), diff, _gate_cell(g and g["long"]),
                         _gate_cell(g and g["short"])])
            continue
        digits = 5 if st["close"] < 20 else 2
        rows.append([m, fmt(st["close"], digits), fmt(st["ret_5d_pct"]), fmt(mk[m]["vol_20d_pct"]), diff,
                     _gate_cell(g and g["long"]), _gate_cell(g and g["short"])])
    return ["## 6. Märkte und Gates (Ansicht der Scorecard; M bewertet der Agent)", "",
            *_table(["Markt", "Kurs", "1W %", "Vol 20T %", "Score Basis−Quote", "long", "short"], rows), "",
            "R = Carry + Zins-Momentum, P = Preis-Momentum, F = COT-Veto. Gold: R = US-Realzins, "
            "P = Kurs/SMA20, F = Managed Money.", ""]


def _risk(rk: dict) -> list[str]:
    rows = [[i["markt"], i["seite"], fmt(i["diff"]), fmt(i["vol_pct"]), fmt(i["groesse_rel"])] for i in rk["ideen"]]
    b = rk["buendel"]
    net = ", ".join(f"{c} {fmt(v, 2)}" for c, v in b["netto"].items()) or "–"
    over = ", ".join(f"{c} {fmt(v, 2)}" for c, v in b["ueber_deckel"].items()) or "keine"
    return [f"## 7. Risiko-Budget (Ideen ab Score-Differenz {fmt(rk['schwelle_diff'])}, ohne Veto)", "",
            *(_table(["Markt", "Seite", "Score-Diff", "Vol 20T %", "Größe rel."], rows) if rows else ["keine"]), "",
            f"Netto-Exposure je Währung (Einheiten): {net}",
            f"Über dem Deckel {fmt(b['deckel'], 1)}: {over} · Haupttreiber: {b['haupttreiber'] or '–'}", ""]


def _profiles(laender: dict) -> list[str]:
    rows = []
    for label, q, field, digits in PROFILE_ROWS:
        cells = [label]
        for land in G8:
            node = laender[land].get(q)
            v = None if not node else node.get(field)
            cells.append(fmt(v, digits) + ("*" if node and node.get("stale") else ""))
        rows.append(cells)
    return ["## 8. Länderprofile", "", *_table(["", *G8], rows), "",
            "\\* = älter als erlaubt (siehe Datenlücken). Leitzins/Kern-Inflation teils aus Kalender bzw. SNB.", ""]


def _positioning(pos: dict) -> list[str]:
    rows = [[k, fmt(v["net"], 0), fmt(v["chg_1w"], 0), fmt(v["cot_26w"], 1), fmt(v["cot_3y"], 1), v["date"]]
            for k, v in pos.items() if v]
    return ["## 9. Positionierung (CFTC TFF, Leveraged Funds; Gold Managed Money)", "",
            *_table(["", "Netto", "Δ 1W", "COT 26W", "COT 3J", "veröffentlicht"], rows), ""]


def _g8(sheet: dict) -> list[str]:
    if not sheet["g8"]:
        return ["## 10. G8-Stärke (Vergleich mit SMT)", "", f"n.v. ({sheet['g8_stand']})", ""]
    ranked = sorted(sheet["g8"].items(), key=lambda kv: -kv[1])
    return [f"## 10. G8-Stärke (Nachbau, Vergleich mit SMT, Stand {sheet['g8_stand']})", "",
            *_table(["Rang", "Währung", "Score"], [[str(i + 1), c, fmt(v)] for i, (c, v) in enumerate(ranked)]), ""]


def _calendar(k: dict) -> list[str]:
    up = [[e["zeit_utc"], e["waehrung"], e["titel"], e["konsens"] or "–", e["vorwert"] or "–"]
          for e in k["naechste_7t"]]
    su = [[e["zeit_utc"], e["waehrung"], e["titel"], fmt(e["konsens"]), fmt(e["ist"]), fmt(e["ueberraschung"])]
          for e in k["ueberraschungen_14t"]]
    return [f"## 11. Kalender (Referenz {k.get('referenz_utc', '–')} UTC)", "", "**Nächste 7 Tage (High)**", "",
            *(_table(["Zeit UTC", "Währung", "Termin", "Konsens", "Vorwert"], up) if up else ["keine"]), "",
            "**Überraschungen letzte 14 Tage (High, Ist − Konsens)**", "",
            *(_table(["Zeit UTC", "Währung", "Termin", "Konsens", "Ist", "Überraschung"], su) if su else ["keine"]), ""]


STATUS = {"belegt": "belegt", "gekippt": "gekippt", "regime": "nur heute", "schwach": "–"}


def _pct(v) -> str:
    return "–" if v is None else ("+" if v > 0 else "") + fmt(v)


def _geo(geo: dict | None) -> list[str]:
    head = ["## 5. Geopolitik, News und Realzinsen", ""]
    if not geo or "fehler" in geo:
        return head + [f"n.v. ({(geo or {}).get('fehler', 'kein Block')})", ""]
    us = geo["realzins"]["us"]
    rows = []
    for name, k in (("Realzins 10J (TIPS)", "real_10y"), ("Realzins 5J", "real_5y"),
                    ("Inflationserwartung 10J", "breakeven_10y"), ("Inflationserwartung 5J", "breakeven_5y"),
                    ("5J in 5J (Glaubwürdigkeit Fed-Ziel)", "fwd_5y5y")):
        x = us.get(k) or {}
        rows.append([name, fmt(x.get("wert")), fmt(x.get("chg_5d_bp"), 1), x.get("datum", "–")])
    lines = head + ["**US-Realzinsen**", "", *_table(["", "%", "Δ 1W (bp)", "Datum"], rows), ""]
    prox = geo["realzins"]["naeherung_2j_minus_kern"]
    lines += ["Näherung je Land (2J minus Kern-Inflation, ex post): "
              + " · ".join(f"{k} {fmt(v)}" for k, v in prox.items()), ""]

    od = geo["oel_durchgriff"]
    rows = [[n, *[f"{_pct(od[k][s]['bp'])} (t {fmt(od[k][s]['t'], 1)})" for s in ("is", "oos", "heute")]]
            for n, k in (("US-2J", "us_2y"), ("US-Realzins", "realzins"), ("Inflationserwartung", "breakeven"))]
    gor = geo["gold_oel_regime"]
    lines += [f"**Öl-Durchgriff** (Brent +10 % → bp; Markt preist zurzeit: {geo['zinsregime']})", "",
              *_table(["", "2007–16", "2017–05/26", "letzte 26 Wochen"], rows), "",
              f"→ **{od['kanal']}**. Gold je Brent +10 %: letzte 26 Wochen {_pct(od['gold_heute_pct'])} %; "
              f"2007–05/26 in Anhebungsphasen {_pct(gor['anhebungen']['wirkung'])} %, in Senkungsphasen "
              f"{_pct(gor['senkungen']['wirkung'])} %. Öl drückt Gold nur, wenn es die Fed-Erwartung hebt.", ""]

    gpr, ev = geo.get("gpr"), geo.get("ereignisstudie")
    if gpr:
        lines += [f"**Geopolitik-Index (GPR)** {fmt(gpr['wert'], 0)} am {gpr['datum']} (30-Tage-Mittel "
                  f"{fmt(gpr['mittel_30t'], 0)}, {fmt(gpr['perzentil_1j'], 0)}. Perzentil im Jahr).", ""]
    if ev:
        lines += ["Ereignisstudie Geopolitik-Spitzen: " + "; ".join(
            f"{s.upper()} {e['ereignisse']} Spitzen, {e['signifikant']} signifikante Reaktionen "
            f"(max. |t| {fmt(e['max_abs_t'])}, {e['bei']})" for s, e in ev.items())
            + ". Geopolitik wirkt nur über Kanäle (Öl, Zinsen), nicht als Angst an sich.", ""]

    lines += [f"**Themen** (Einordnung durch Claude aus den Schlagzeilen vom {geo.get('news_stand') or 'n.v.'}; "
              "Wirkung je Schock aus der Exposure-Matrix, nur belastbare Einträge)", ""]
    for c in geo["themen"]:
        n = f" ({c['treffer_24h']} Meldungen/24 h)" if c.get("treffer_24h") else ""
        lines += [f"*{c['name']}*: **{c['lage']}**{n}"]
        if c["kernaussage"]:
            lines += [c["kernaussage"]]
        lines += [f"Weg (Annahme): {c['weg']}. Treiber: {c['treiber']}.", ""]
        eff = [e for e in c["einfluss"] if e["status"] != "schwach" or e["asset"] == "Gold"]  # Gold immer zeigen
        if eff:
            lines += _table(["Asset", "Wirkung heute %", "2017–26 %", "Status"],
                            [[e["asset"], _pct(e["wirkung_heute"]), _pct(e["wirkung_oos"]), STATUS[e["status"]]]
                             for e in eff]) + [""]

    lines += ["**Exposure-Matrix** (Wirkung in % je Schock: letzte 26 Wochen / 2017–26; ohne Zusatz = belegt, "
              "also gleiches Vorzeichen 2007–16, 2017–26 und heute)", ""]
    drivers = list(geo["exposure"])
    assets = list(next(iter(geo["exposure"].values()))["assets"])
    rows = []
    for a in assets:
        row = [a]
        for d in drivers:
            x = geo["exposure"][d]["assets"].get(a)
            if not x:
                row.append("–")
                continue
            extra = "" if x["status"] == "belegt" else f" ({STATUS[x['status']]})"
            row.append(f"{_pct(x['heute'])} / {_pct(x['oos'])}{extra}")
        rows.append(row)
    lines += _table(["Asset", *[geo["exposure"][d]["schock"] for d in drivers]], rows) + [""]

    er = geo.get("earnings") or {}
    mc = [m for m in er.get("megacaps", []) if "fehler" not in m]
    if mc:
        lines += ["**S&P-Megacaps (Earnings, Yahoo; Überraschung auf Yahoo-EPS, Sondereffekte wie Steuern "
                  "können große Abweichungen erzeugen)**", "",
                  *_table(["Wert", "Nächster Termin", "EPS erwartet", "Letzte Überraschung %", "Beats letzte 4"],
                          [[m["symbol"], m["naechster_termin"] or "–", fmt(m["erwartung_eps"]),
                            _pct(m["letzte_ueberraschung_pct"]), str(m["beats_letzte_4"])] for m in mc]), ""]
    if er.get("saison"):
        s = er["saison"]
        lines += [f"Saison {s.get('quartal')}: Gewinnwachstum {fmt(s.get('wachstum_pct'), 1)} %, "
                  f"Beat-Quote {fmt(s.get('beat_quote_pct'), 0)} %, berichtet {fmt(s.get('berichtet_pct'), 0)} % "
                  f"(FactSet, Stand {s.get('stand')}). {s.get('hinweis', '')}", ""]
    return lines


def markdown(sheet: dict) -> str:
    lines = [f"# Makro Fact Sheet – Stand {sheet['stand']}", "",
             f"Erzeugt {sheet['erzeugt']} · {len(sheet['register'])} Zahlen im Register · "
             "Quelle: fusion_lab/macro_data + Dukascopy", ""]
    lines += _state(sheet["zustand"]) + _regime(sheet) + _scorecard(sheet["scorecard"])
    lines += _tactical(sheet["taktisch"]) + _geo(sheet.get("geopolitik")) + _markets(sheet["maerkte"])
    lines += _risk(sheet["risiko"])
    lines += _profiles(sheet["laender"]) + _positioning(sheet["positionierung"]) + _g8(sheet)
    lines += _calendar(sheet["kalender"])
    lines += ["## 12. Datenlücken", "", *[f"- {g}" for g in sheet["datenluecken"]], ""]
    return "\n".join(lines)
