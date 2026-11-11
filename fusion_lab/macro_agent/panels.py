"""Tagespanels (Datum x Land) fuer die Scorecard -- dieselben fuer Backtest und Fact Sheet.

Historie aus den Remy-Caches (`data_cache/remy/`: Zinsen ab 2002, COT Legacy ab 2000, FF-Kalender
ab 2007, FX D1 ab 2003), verlaengert um die Datenschicht (`fusion_lab/macro_data`, mit Ersatzwerten
aus `calendar_values.extend`) und frische Dukascopy-Kurse. Bei Ueberschneidung gewinnt die
Datenschicht. Zeitpunkt jedes Werts = wann er bekannt war (COT: Freitag, REER: Monat + 45 Tage).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from fusion_lab.macro_data import calendar, calendar_values, store

ROOT = Path(__file__).resolve().parents[2]
LANDS = ["US", "EA", "GB", "JP", "CH", "AU", "CA", "NZ"]
LAND_CCY = {"US": "USD", "EA": "EUR", "GB": "GBP", "JP": "JPY", "CH": "CHF", "AU": "AUD", "CA": "CAD", "NZ": "NZD"}
CCY_LAND = {v: k for k, v in LAND_CCY.items()}
PAIR_OF = {"EA": ("EURUSD", 1), "GB": ("GBPUSD", 1), "AU": ("AUDUSD", 1), "NZ": ("NZDUSD", 1),
           "JP": ("USDJPY", -1), "CH": ("USDCHF", -1), "CA": ("USDCAD", -1)}
RATES_HISTORY = ROOT / "data_cache" / "remy" / "rates_history.parquet"
COT_HISTORY = ROOT / "data_cache" / "remy" / "cot_legacy.parquet"
FF_HISTORY = calendar_values.FF_HISTORY
COT_CODES = {"099741": "EA", "096742": "GB", "097741": "JP", "092741": "CH", "232741": "AU", "090741": "CA",
             "112741": "NZ"}
REER_LAG = pd.Timedelta(days=45)        # BIS veroeffentlicht Monat M etwa Mitte M+1
COT_LAG = pd.Timedelta(days=3)          # Stichtag Dienstag, veroeffentlicht Freitag
SURPRISE_MIN_OBS = 8                    # Streuung je Indikator erst ab 8 frueheren Ueberraschungen
SURPRISE_CLIP = 3.0
# Hoeher = schlechter fuer die Waehrung (Vorzeichen der Ueberraschung drehen)
INVERSE = ("Unemployment Rate", "Unemployment Claims", "Jobless Claims", "Claimant Count", "Unemployment Change")


@dataclass
class Panels:
    value: pd.DataFrame      # log-Wert je Waehrung in USD (USD = 0)
    policy: pd.DataFrame     # Leitzins %
    y2: pd.DataFrame         # 2J-Rendite %
    reer: pd.DataFrame       # log REER, ab Bekanntwerden
    surprise: pd.DataFrame   # normierte Ueberraschungen je Termintag (Summe des Tages)
    cot: pd.DataFrame        # Netto Non-Commercials, ab Veroeffentlichung (ohne USD, siehe Docstring scorecard)


def _wide(long: pd.DataFrame, suffix: str) -> pd.DataFrame:
    part = long[long["key"].str.endswith("." + suffix)]
    w = part.assign(land=part["key"].str.split(".").str[0]).pivot_table(index="date", columns="land",
                                                                        values="value", aggfunc="last")
    return w.reindex(columns=[l for l in LANDS if l in w.columns]).sort_index()


def _combine(history: pd.DataFrame, recent: pd.DataFrame) -> pd.DataFrame:
    return recent.combine_first(history).sort_index()


def _on_days(w: pd.DataFrame, days: pd.DatetimeIndex) -> pd.DataFrame:
    """Letzter bekannter Wert je Handelstag (nur Werte mit Datum <= Tag)."""
    return w.reindex(w.index.union(days)).ffill().reindex(days)


def fx_values(days_end: pd.Timestamp) -> pd.DataFrame:
    """log-Wert je Waehrung in USD. Remy-Historie + Dukascopy der letzten 150 Tage."""
    from combined_strategy.data import fetch_timeframe
    closes = {}
    try:
        import sys
        sys.path.insert(0, str(ROOT))
        from scripts.remy_common import fx_closes
        hist = fx_closes()
    except Exception:  # Historie fehlt -> nur juengste Kurse
        hist = pd.DataFrame()
    start = (days_end - pd.Timedelta(days=150)).strftime("%Y-%m-%d")
    end = (days_end + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    for land, (pair, _) in PAIR_OF.items():
        c = fetch_timeframe(pair, "D1", start, end)["Close"]
        c.index = c.index.tz_convert(None).normalize()
        c = c[c.index.dayofweek < 5]
        old = hist[pair] if pair in hist else pd.Series(dtype=float)
        closes[pair] = c.combine_first(old)
    out = {}
    for land, (pair, orient) in PAIR_OF.items():
        out[land] = orient * np.log(closes[pair])
    df = pd.DataFrame(out)
    df.insert(0, "US", 0.0)
    return df[LANDS].sort_index()


def surprise_events(ff: pd.DataFrame) -> pd.DataFrame:
    """High-Impact-Ueberraschungen (Ist - Konsens), je Indikator durch die Streuung der FRUEHEREN
    Ueberraschungen geteilt (kein Vorgriff), Vorzeichen fuer Arbeitslosigkeit gedreht."""
    ff = ff[(ff["impact"] == "high") & ff["currency"].isin(CCY_LAND)].copy()
    a = ff["actual"].map(calendar.parse_number)
    f = ff["forecast"].map(calendar.parse_number)
    ff["actual_v"], ff["forecast_v"] = a.str[0], f.str[0]
    ff = ff[ff["actual_v"].notna() & ff["forecast_v"].notna() & (a.str[1] == f.str[1])]
    ff["s"] = ff["actual_v"] - ff["forecast_v"]
    ff.loc[ff["name"].str.contains("|".join(INVERSE)), "s"] *= -1
    ff = ff.sort_values("time")
    sd = ff.groupby(["currency", "name"])["s"].transform(
        lambda x: x.expanding().std().shift(1).where(x.expanding().count().shift(1) >= SURPRISE_MIN_OBS))
    ff["z"] = (ff["s"] / sd).clip(-SURPRISE_CLIP, SURPRISE_CLIP)
    ff = ff[ff["z"].notna() & np.isfinite(ff["z"])]
    t = pd.to_datetime(ff["time"], utc=True).dt.tz_localize(None).dt.normalize()
    return pd.DataFrame({"date": t, "land": ff["currency"].map(CCY_LAND), "z": ff["z"]})


def build(as_of: pd.Timestamp | None = None, with_fx: bool = True, point_in_time: bool = True) -> Panels:
    """point_in_time: nur Werte, die bis Ende as_of abgerufen waren (Fact Sheet fuer einen
    vergangenen Tag). Der Backtest setzt False: echte Abrufzeiten gibt es erst ab 30.10.2026,
    den Vorgriffsschutz liefern dort die Bekanntgabe-Verschiebungen (REER, COT) und Werte bis Vortag."""
    as_of = (as_of or pd.Timestamp.now()).normalize()
    known = as_of + pd.Timedelta(days=1) if point_in_time else None
    macro = store.latest("macro", as_of=known)
    macro = calendar_values.extend(macro[macro["date"] <= as_of])
    hist = pd.read_parquet(RATES_HISTORY) if RATES_HISTORY.exists() else pd.DataFrame(columns=["key", "date", "value"])
    hist = hist[hist["date"] <= as_of]

    policy = _combine(_wide(hist, "policy_rate"), _wide(macro, "policy_rate"))
    y2 = _combine(_wide(hist, "2y"), _wide(macro, "2y"))
    tvc_au = macro[macro["key"] == "AU.2y_tvc"].set_index("date")["value"]
    if len(tvc_au):  # RBA-2J erst ab 2013, davor TradingView (wie fusion_lab/filters/zins_fx.py)
        y2["AU"] = y2.get("AU", pd.Series(dtype=float)).combine_first(tvc_au)
    reer = np.log(_wide(macro, "reer"))
    reer.index = reer.index + pd.offsets.MonthBegin(1) + REER_LAG - pd.Timedelta(days=1)

    cot_parts = []
    if COT_HISTORY.exists():
        d = pd.read_parquet(COT_HISTORY)
        d = d[d["cftc_contract_market_code"].isin(COT_CODES)]
        cot_parts.append(pd.DataFrame({
            "key": d["cftc_contract_market_code"].map(COT_CODES) + ".noncomm_net",
            "date": pd.to_datetime(d["report_date_as_yyyy_mm_dd"]) + COT_LAG,
            "value": pd.to_numeric(d["noncomm_positions_long_all"]) - pd.to_numeric(d["noncomm_positions_short_all"])}))
    pos = store.latest("positioning", as_of=known)
    pos = pos[pos["key"].str.endswith(".noncomm_net") & ~pos["key"].str.startswith("USD")]
    cot_parts.append(pos.assign(key=pos["key"].str[:3].map(CCY_LAND) + ".noncomm_net")[["key", "date", "value"]])
    cot_long = pd.concat(cot_parts, ignore_index=True)
    cot = _wide(cot_long[cot_long["date"] <= as_of], "noncomm_net")

    sur = pd.DataFrame(columns=["date", "land", "z"])
    if FF_HISTORY.exists():
        sur = surprise_events(pd.read_parquet(FF_HISTORY))
    surprise = sur[sur["date"] <= as_of].pivot_table(index="date", columns="land", values="z", aggfunc="sum")

    value = fx_values(as_of) if with_fx else pd.DataFrame(columns=LANDS, index=pd.DatetimeIndex([]))
    value = value[value.index <= as_of]
    return Panels(value=value, policy=policy, y2=y2, reer=reer, surprise=surprise.reindex(columns=LANDS), cot=cot)
