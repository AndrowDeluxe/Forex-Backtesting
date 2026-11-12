"""Fact Sheet v2: Scorecard (strategisch), taktische Ebene, Risiko-Budget, Zustand, Profile, Kalender.

Point-in-time: Stand = as_of (Tag). Makrowerte zaehlen, wenn sie bis Ende des Tages abgerufen
waren (store.latest as_of) und ihr Datum <= as_of ist; Kurse bis einschliesslich as_of. Ersatzwerte
(Kalender-Leitzins, TradingView-2J usw.) haengt calendar_values.extend an die Hauptreihen.
Das flache Zahlenregister (Pfad -> Wert) ist die Liste der Zahlen, die der Agent nennen darf.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from fusion_lab.macro_data import calendar, calendar_values, store
from fusion_lab.macro_data.__main__ import coverage
from fusion_lab.macro_data.sources import G8

from . import chains, factors, geo_framework, ledger, manifest, panels, risk, tactical
from .analytics import dollar_factor, gates, markets, overlap, profiles, state_machine

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "macro_agent"
TEST_FILE = OUT_DIR / "scorecard_test.json"
CALENDAR_HOURS = 7 * 24
SURPRISE_DAYS = 14
G8_CCY = set(gates.CCY_COUNTRY)
ZINS_FX_MARKETS = ["EURUSD", "GBPUSD", "AUDUSD", "USDJPY", "XAUUSD"]
SCORE_DAYS = 600  # Kalendertage Vorlauf: 12-Monats-Momentum braucht 252 Handelstage


def _stored(area: str, as_of: pd.Timestamp) -> pd.DataFrame:
    df = store.latest(area, as_of=as_of + pd.Timedelta(days=1))
    return df[df["date"] <= as_of]


def _last(s: pd.Series):
    return None if s.empty else round(float(s.iloc[-1]), 4)


def state_block(macro_w: pd.DataFrame, mkt_w: pd.DataFrame, as_of: pd.Timestamp) -> dict:
    def values(day):
        cut = lambda s: s[s.index <= day]
        fr, de = cut(profiles.series(macro_w, "FR.10y")), cut(profiles.series(macro_w, "DE.10y"))
        oat = (fr - de).dropna()
        return {"vix": _last(cut(profiles.series(macro_w, "MKT.vix"))),
                "hy_spread": _last(cut(profiles.series(macro_w, "MKT.hy_spread"))),
                "brent": _last(cut(profiles.series(mkt_w, "MKT.brent"))),
                "oat_bund_bp": None if oat.empty else round(float(oat.iloc[-1]) * 100, 1),
                "stlfsi": _last(cut(profiles.series(macro_w, "MKT.stlfsi")))}
    now = state_machine.evaluate(values(as_of))
    week_ago = state_machine.evaluate(values(as_of - pd.Timedelta(days=7)))
    haven = state_machine.safe_haven_days(profiles.series(mkt_w, "MKT.dxy"), profiles.series(mkt_w, "MKT.spx"),
                                          profiles.series(macro_w, "MKT.vix"))
    return {**now, "state_week_ago": week_ago["state"], "dollar_haven_days": haven,
            "levels": {k: _last(profiles.series(mkt_w, f"MKT.{k}")) for k in ("dxy", "spx", "gold", "brent")}}


def g8_scores(as_of: pd.Timestamp) -> tuple[pd.Series | None, str]:
    """Dennis' G8-Staerke (Nachbau) nur noch als Vergleich, kein Gate mehr (steckt in Preis-Momentum)."""
    from fusion_lab.g8.data import log_values, usd_value_panel
    from fusion_lab.g8.model import DEFAULT_NORM, score
    try:
        start = (as_of - pd.Timedelta(days=200)).strftime("%Y-%m-%d")
        end = (as_of + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        panel = usd_value_panel("duka", start=start, end=end)
        panel = panel[(panel.index <= as_of) & (panel.index.dayofweek < 5)]
        s, _ = score(log_values(panel), DEFAULT_NORM)
        s = s.dropna()
        return s.iloc[-1].round(2), s.index[-1].date().isoformat()
    except Exception as e:
        return None, f"Fehler: {type(e).__name__}: {e}"[:200]


def regime_block(as_of: pd.Timestamp | None = None) -> dict:
    try:
        from fusion_lab.macro_regime.__main__ import current_state
        return current_state(refresh=False, as_of=as_of)
    except Exception as e:
        return {"fehler": f"{type(e).__name__}: {e}"[:200]}


def filter_block(macro: pd.DataFrame, as_of: pd.Timestamp) -> dict:
    """Vorhandene Filter als Info; beide nutzen nur Werte VOR dem abgefragten Tag."""
    day = as_of + pd.Timedelta(days=1)
    out = {}
    try:
        from fusion_lab.filters.zinskurve_regime import GoldZinskurvenFilter
        f = GoldZinskurvenFilter(refresh=True)
        out["gold_zinskurve"] = {"regime": f.regime_at(day), "richtung": f.direction(day)}
    except Exception as e:
        out["gold_zinskurve"] = {"fehler": f"{type(e).__name__}: {e}"[:200]}
    try:
        from fusion_lab.filters.zins_fx import ZinsFxFilter
        z = ZinsFxFilter(data=macro)
    except Exception as e:
        out["zins_fx"] = {"fehler": f"{type(e).__name__}: {e}"[:200]}
        return out
    out["zins_fx"] = {}
    for m in ZINS_FX_MARKETS:
        try:
            out["zins_fx"][m] = {"momentum": z.momentum_dir(m, day), "carry": z.carry_dir(m, day)}
        except TypeError:  # Reihe fehlt zum Stand ganz (leerer Index im Filter) -> keine Aussage
            out["zins_fx"][m] = {"momentum": None, "carry": None}
    return out


def calendar_block(as_of: pd.Timestamp) -> dict:
    path = store.DATA_DIR / "calendar.parquet"
    ref = min(pd.Timestamp.now("UTC").tz_localize(None), as_of + pd.Timedelta(days=1))
    if not path.exists():
        return {"referenz_utc": ref.strftime("%Y-%m-%d %H:%M"), "naechste_7t": [], "ueberraschungen_14t": []}
    ev = pd.read_parquet(path)
    ev = ev[(ev["fetched_at"] <= ref) & ev["currency"].isin(G8_CCY)]
    last = ev.sort_values("fetched_at").drop_duplicates(calendar.KEY, keep="last")
    nxt = last[(last["event_time"] > ref) & (last["event_time"] <= ref + pd.Timedelta(hours=CALENDAR_HOURS))
               & (last["impact"] == "High")]
    nxt = nxt.sort_values("event_time").drop_duplicates(["currency", "title", "event_time"])
    upcoming = [{"zeit_utc": r.event_time.strftime("%Y-%m-%d %H:%M"), "waehrung": r.currency, "titel": r.title,
                 "konsens": r.forecast, "vorwert": r.previous} for r in nxt.itertuples()]
    sur = calendar.surprises(ev)
    sur = sur[(sur["event_time"] > ref - pd.Timedelta(days=SURPRISE_DAYS)) & (sur["event_time"] <= ref)
              & (sur["impact"] == "High") & (sur["surprise"] != 0)].sort_values("event_time")
    surprises = [{"zeit_utc": r.event_time.strftime("%Y-%m-%d %H:%M"), "waehrung": r.currency, "titel": r.title,
                  "konsens": round(r.forecast, 4), "ist": round(r.actual, 4), "ueberraschung": round(r.surprise, 4)}
                 for r in sur.itertuples()]
    return {"referenz_utc": ref.strftime("%Y-%m-%d %H:%M"), "naechste_7t": upcoming, "ueberraschungen_14t": surprises}


def scorecard_block(as_of: pd.Timestamp) -> tuple[dict, dict]:
    """Scorecard je Waehrung am letzten Handelstag <= as_of; zweiter Wert = Rohdaten fuer die Paare."""
    p = panels.build(as_of)
    days = pd.bdate_range(as_of - pd.Timedelta(days=SCORE_DAYS), as_of)
    sc = factors.scorecard(p, days)
    day = days[-1]
    score = sc["score"].loc[day]
    rank = score.rank(ascending=False)
    out = {}
    for land in panels.LANDS:
        node = {f: (None if pd.isna(sc[f].loc[day, land]) else round(float(sc[f].loc[day, land]), 2))
                for f in factors.FACTORS}
        node["score"] = None if pd.isna(score[land]) else round(float(score[land]), 2)
        node["rang"] = None if pd.isna(rank[land]) else int(rank[land])
        cot = sc["cot_3y"].loc[day, land]
        node["cot_3y"] = None if pd.isna(cot) else round(float(cot), 1)
        node["veto_long"] = bool(sc["veto_long"].loc[day, land]) if pd.notna(cot) else False
        node["veto_short"] = bool(sc["veto_short"].loc[day, land]) if pd.notna(cot) else False
        out[panels.LAND_CCY[land]] = node
    test = json.loads(TEST_FILE.read_text(encoding="utf-8")) if TEST_FILE.exists() else None
    corr = overlap.factor_corr(sc, factors.FACTORS)
    indep = {"korrelation": {a: {b: (None if pd.isna(corr.at[a, b]) else round(float(corr.at[a, b]), 2))
                                 for b in corr.columns} for a in corr.index},
             "n_eff_faktoren": overlap.score_n_eff(corr), "faktoren": len(factors.FACTORS)}
    return {"tag": day.date().isoformat(), "waehrungen": out, "test": test, "unabhaengigkeit": indep,
            "einsatz": "Kontext, kein Richtungsgeber (Backtest IS/OOS ohne Edge)" if test else "ungetestet"}, out


def pair_block(market: str, cards: dict) -> dict | None:
    base, quote = market[:3], market[3:6]
    if base not in cards or quote not in cards:
        return None
    b, q = cards[base], cards[quote]
    diffs = {f: (None if b[f] is None or q[f] is None else round(b[f] - q[f], 2)) for f in factors.FACTORS}
    diff = None if b["score"] is None or q["score"] is None else round(b["score"] - q["score"], 2)
    vl, vs = b["veto_long"] or q["veto_short"], b["veto_short"] or q["veto_long"]
    return {"diff": diff, "faktoren": diffs, "veto_long": vl, "veto_short": vs,
            "gates": gates.scorecard_view(diffs, vl, vs)}


def chains_block(sheet: dict, macro_w: pd.DataFrame, as_of: pd.Timestamp) -> list | dict:
    try:
        m = chains.measures(geo_framework.history().loc[:as_of], macro_w, sheet)
        return chains.evaluate(m, (sheet.get("geopolitik") or {}).get("exposure"))
    except Exception as e:
        return {"fehler": f"{type(e).__name__}: {e}"[:200]}


def ledger_block(as_of: pd.Timestamp) -> dict:
    """Faellige Aussagen auswerten, dann Trefferquote je Art (Stand vor dem heutigen Anhaengen)."""
    try:
        done = ledger.evaluate(geo_framework.history(), as_of)
        return {"neu_ausgewertet": done, **ledger.summary()}
    except Exception as e:
        return {"fehler": f"{type(e).__name__}: {e}"[:200]}


def geo_block(macro_w: pd.DataFrame, as_of: pd.Timestamp) -> dict:
    try:
        return geo_framework.sheet_block(macro_w, as_of)
    except Exception as e:  # Geopolitik darf das Fact Sheet nicht mitreissen
        return {"fehler": f"{type(e).__name__}: {e}"[:200]}


def gaps(sheet: dict, as_of: pd.Timestamp) -> list[str]:
    out = []
    for q, row in coverage(as_of).iterrows():
        for land, v in row.items():
            if v == "FEHLT" or v.endswith("ALT"):
                out.append(f"{land}.{q}: {v}")
    if sheet["g8"] is None:
        out.append(f"G8-Nachbau: {sheet['g8_stand']}")
    if "fehler" in sheet["regime"]:
        out.append(f"Regimekarte: {sheet['regime']['fehler']}")
    for name, f in sheet["filter"].items():
        if "fehler" in f:
            out.append(f"Filter {name}: {f['fehler']}")
    geo = sheet.get("geopolitik", {})
    if "fehler" in geo:
        out.append(f"Geopolitik: {geo['fehler']}")
    elif geo.get("news_stand") != sheet["stand"]:
        out.append(f"News-Einordnung vom {geo.get('news_stand') or 'n.v.'} (nicht vom Stichtag)")
    out.append("Europa-Gas (TTF) ohne freie Historie: nur Tageswert ab 12.11.2026, kein Exposure")
    out.append("GDELT-Nachrichtenvolumen gesperrt (429); Intensitaet nur als Schlagzeilen-Zahl ab 12.11.2026")
    out.append("Realzins ausser USA nur als Naeherung 2J minus Kern-Inflation (ex post)")
    out.append("Notenbank-Pricing ausser Fed nur als Naeherung 1J minus Leitzins (kein OIS)")
    out.append("COT-Veto ohne USD (Legacy-Historie kennt den Dollar-Index-Kontrakt nicht)")
    return out


def flatten(node, path: str = "") -> dict:
    """Alle Zahlen als Pfad -> Wert (bool und Text zaehlen nicht)."""
    out = {}
    if isinstance(node, dict):
        for k, v in node.items():
            out.update(flatten(v, f"{path}.{k}" if path else str(k)))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out.update(flatten(v, f"{path}[{i}]"))
    elif isinstance(node, (int, float)) and not isinstance(node, bool):
        out[path] = node
    return out


def build(as_of: pd.Timestamp | None = None, with_filters: bool = True) -> dict:
    as_of = (as_of or pd.Timestamp.now()).normalize()
    macro_raw = _stored("macro", as_of)
    macro = calendar_values.extend(macro_raw)
    macro_w, mkt_w = profiles.wide(macro), profiles.wide(_stored("markets", as_of))
    pos = profiles.positioning(profiles.wide(_stored("positioning", as_of)))
    prices = markets.load(as_of)
    g8, g8_stand = g8_scores(as_of)
    score_sheet, cards = scorecard_block(as_of)

    mk, pair_views, vols = {}, {}, {}
    for m in markets.MARKETS:
        st = markets.stats(prices[m])
        node = {"kurs": st}
        vols[m] = risk.realized_vol(prices[m]["Close"])
        node["vol_20d_pct"] = None if vols[m] is None else round(vols[m], 2)
        if m == "XAUUSD":  # Gold ist keine Scorecard-Waehrung: eigene Gates (Realzins, Kurs, Managed Money)
            g = gates.evaluate(m, st, macro_w, None, pos)
            node["gates"] = {"inputs": g["inputs"], **{s: {k: g[s][k] for k in ("R", "P", "F")} | {
                "pass": sum(g[s][k] == "PASS" for k in ("R", "P", "F")),
                "verfuegbar": sum(g[s][k] != "n.v." for k in ("R", "P", "F"))} for s in ("long", "short")}}
        else:
            view = pair_block(m, cards)
            node["scorecard"] = view
            node["gates"] = view["gates"] if view else None
            if view:
                pair_views[m] = view
        mk[m] = node
    idea_list = risk.ideas(pair_views, vols)
    corr = pd.DataFrame(score_sheet["unabhaengigkeit"]["korrelation"]).astype(float)
    for i in idea_list:
        i["gruende"] = overlap.reasons(pair_views[i["markt"]]["faktoren"], i["seite"], corr)
    usd = dollar_factor.usd_factor(prices)
    decomp = dollar_factor.decompose(prices, usd)
    dollar = {"fenster_tage": dollar_factor.WINDOW, "zerlegung": decomp,
              "ideen": dollar_factor.idea_bundle(prices, idea_list, decomp)}

    sheet = {
        "stand": as_of.date().isoformat(),
        "erzeugt": pd.Timestamp.now().isoformat(timespec="seconds"),
        "zustand": state_block(macro_w, mkt_w, as_of),
        "regime": regime_block(as_of),
        "filter": filter_block(macro_raw, as_of) if with_filters else {},
        "scorecard": score_sheet,
        "taktisch": {"fed": tactical.fed(mkt_w, macro_w, as_of), "notenbanken": tactical.other_pricing(macro_w),
                     "rohstoffe": tactical.commodities(mkt_w)},
        "risiko": {"ideen": idea_list, "buendel": risk.bundle(idea_list), "schwelle_diff": risk.IDEA_MIN},
        "laender": profiles.profiles(macro_w, as_of),
        "positionierung": pos,
        "g8": None if g8 is None else g8.to_dict(),
        "g8_stand": g8_stand,
        "maerkte": mk,
        "kalender": calendar_block(as_of),
        "geopolitik": geo_block(macro_w, as_of),
        "dollar": dollar,
        "ledger": ledger_block(as_of),
    }
    sheet["ketten"] = chains_block(sheet, macro_w, as_of)
    sheet["datenluecken"] = gaps(sheet, as_of)
    viol = manifest.asof_violations(sheet, as_of)
    sheet["asof_pruefung"] = {"ok": not viol, "verstoesse": viol[:20]}
    if viol:
        sheet["datenluecken"].append(f"As-of-Prüfung: {len(viol)} Werte nach dem Stichtag, z. B. {viol[0]}")
    sheet["register"] = flatten({k: v for k, v in sheet.items() if k != "register"})
    return sheet


def write(sheet: dict, md: str, out_dir: Path = OUT_DIR) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"fact_sheet_{sheet['stand']}"
    j, m = out_dir / f"{stem}.json", out_dir / f"{stem}.md"
    j.write_text(json.dumps(sheet, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    m.write_text(md, encoding="utf-8")
    return j, m
