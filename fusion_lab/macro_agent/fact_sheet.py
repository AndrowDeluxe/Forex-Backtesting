"""Fact Sheet: buendelt Datenschicht, Profile, Kurse, Gates, Zustand, Regime und Kalender.

Point-in-time: Stand = as_of (Tag). Makrowerte zaehlen, wenn sie bis Ende des Tages abgerufen
waren (store.latest as_of) und ihr Datum <= as_of ist; Kurse bis einschliesslich as_of.
Das flache Zahlenregister (Pfad -> Wert) ist die Liste der Zahlen, die der Agent nennen darf.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from fusion_lab.macro_data import calendar, store
from fusion_lab.macro_data.__main__ import coverage
from fusion_lab.macro_data.sources import G8

from .analytics import gates, markets, profiles, state_machine

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "macro_agent"
CALENDAR_HOURS = 72
SURPRISE_DAYS = 7
G8_CCY = set(gates.CCY_COUNTRY)
ZINS_FX_MARKETS = ["EURUSD", "GBPUSD", "AUDUSD", "USDJPY", "XAUUSD"]


def _stored(area: str, as_of: pd.Timestamp) -> pd.DataFrame:
    df = store.latest(area, as_of=as_of + pd.Timedelta(days=1))
    return df[df["date"] <= as_of]


def _last(s: pd.Series):
    return None if s.empty else round(float(s.iloc[-1]), 4)


def state_block(macro_w: pd.DataFrame, mkt_w: pd.DataFrame, as_of: pd.Timestamp) -> dict:
    def values(day):
        cut = lambda s: s[s.index <= day]
        return {"vix": _last(cut(profiles.series(macro_w, "MKT.vix"))),
                "hy_spread": _last(cut(profiles.series(macro_w, "MKT.hy_spread"))),
                "brent": _last(cut(profiles.series(mkt_w, "MKT.brent"))), "oat_bund_bp": None}
    now = state_machine.evaluate(values(as_of))
    week_ago = state_machine.evaluate(values(as_of - pd.Timedelta(days=7)))
    haven = state_machine.safe_haven_days(profiles.series(mkt_w, "MKT.dxy"), profiles.series(mkt_w, "MKT.spx"),
                                          profiles.series(macro_w, "MKT.vix"))
    return {**now, "state_week_ago": week_ago["state"], "dollar_haven_days": haven,
            "levels": {k: _last(profiles.series(mkt_w, f"MKT.{k}")) for k in ("dxy", "spx", "gold", "brent")}}


def g8_scores(as_of: pd.Timestamp) -> tuple[pd.Series | None, str]:
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
    except Exception as e:  # G8 fehlt -> Gate B n.v., steht unter Datenluecken
        return None, f"Fehler: {type(e).__name__}: {e}"[:200]


def regime_block() -> dict:
    try:
        from fusion_lab.macro_regime.__main__ import current_state
        return current_state(refresh=False)
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
        return {"referenz_utc": ref.strftime("%Y-%m-%d %H:%M"), "naechste_72h": [], "ueberraschungen_7t": []}
    ev = pd.read_parquet(path)
    ev = ev[(ev["fetched_at"] <= ref) & ev["currency"].isin(G8_CCY)]
    last = ev.sort_values("fetched_at").drop_duplicates(calendar.KEY, keep="last")
    nxt = last[(last["event_time"] > ref) & (last["event_time"] <= ref + pd.Timedelta(hours=CALENDAR_HOURS))
               & last["impact"].isin(["High", "Medium"])]
    nxt = nxt.sort_values("event_time").drop_duplicates(["currency", "title", "event_time"])
    upcoming = [{"zeit_utc": r.event_time.strftime("%Y-%m-%d %H:%M"), "waehrung": r.currency, "titel": r.title,
                 "impact": r.impact, "konsens": r.forecast, "vorwert": r.previous} for r in nxt.itertuples()]
    sur = calendar.surprises(ev)
    sur = sur[(sur["event_time"] > ref - pd.Timedelta(days=SURPRISE_DAYS)) & (sur["event_time"] <= ref)
              & (sur["impact"] == "High")].sort_values("event_time")
    surprises = [{"zeit_utc": r.event_time.strftime("%Y-%m-%d %H:%M"), "waehrung": r.currency, "titel": r.title,
                  "konsens": round(r.forecast, 4), "ist": round(r.actual, 4), "ueberraschung": round(r.surprise, 4)}
                 for r in sur.itertuples()]
    return {"referenz_utc": ref.strftime("%Y-%m-%d %H:%M"), "naechste_72h": upcoming, "ueberraschungen_7t": surprises}


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
    out.append("OAT-Bund-Spread fehlt (TAIL-Bedingung n.v.)")
    out.append("Zinspricing ausser Fed nur als Naeherung 2J minus Leitzins (kein OIS)")
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
    macro = _stored("macro", as_of)
    macro_w, mkt_w = profiles.wide(macro), profiles.wide(_stored("markets", as_of))
    pos = profiles.positioning(profiles.wide(_stored("positioning", as_of)))
    prices = markets.load(as_of)
    g8, g8_stand = g8_scores(as_of)
    mk = {}
    for m in markets.MARKETS:
        st = markets.stats(prices[m])
        mk[m] = {"kurs": st, "gates": gates.evaluate(m, st, macro_w, g8, pos)}
    sheet = {
        "stand": as_of.date().isoformat(),
        "erzeugt": pd.Timestamp.now().isoformat(timespec="seconds"),
        "zustand": state_block(macro_w, mkt_w, as_of),
        "regime": regime_block(),
        "filter": filter_block(macro, as_of) if with_filters else {},
        "laender": profiles.profiles(macro_w, as_of),
        "fed_pfad": profiles.fed_path(mkt_w, macro_w, as_of),
        "positionierung": pos,
        "g8": None if g8 is None else g8.to_dict(),
        "g8_stand": g8_stand,
        "maerkte": mk,
        "kalender": calendar_block(as_of),
    }
    sheet["datenluecken"] = gaps(sheet, as_of)
    sheet["register"] = flatten({k: v for k, v in sheet.items() if k != "register"})
    return sheet


def write(sheet: dict, md: str, out_dir: Path = OUT_DIR) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"fact_sheet_{sheet['stand']}"
    j, m = out_dir / f"{stem}.json", out_dir / f"{stem}.md"
    j.write_text(json.dumps(sheet, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    m.write_text(md, encoding="utf-8")
    return j, m
