"""Faelle fuer die Fruehwarn-Untersuchung.

Jeder Fall: DataFrame mit entry_time, exit_time (naiv, NY- bzw. Broker-Zeit
je Quelle einheitlich), r (R oder netto bps -- die Signale sind
standardisiert, die Einheit ist egal) plus Kalibrierfenster (Ende) und, wo
bekannt, Bruch-Typ. Das Kalibrierfenster liegt bei allen Faellen VOR dem
jeweiligen Bruch und wird nicht am Bruch ausgerichtet:
  ORB/Zarattini: deren IS 2016-07..2022-12 | Live-Beine: 2019..2022
  EU-Open: 2018-07..2020-12 (so haette jemand mit Livegang 2021 kalibriert)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))

PC = ROOT / "portfolio_construction" / "results"


def _frame(entry, exit_, r) -> pd.DataFrame:
    df = pd.DataFrame({"entry_time": pd.DatetimeIndex(entry), "exit_time": pd.DatetimeIndex(exit_), "r": np.asarray(r, float)})
    for c in ("entry_time", "exit_time"):
        if df[c].dt.tz is not None:
            df[c] = df[c].dt.tz_localize(None)
    return df.sort_values("entry_time").reset_index(drop=True)


def live_legs(broker: str = "tickmill") -> dict:
    d = pd.read_csv(PC / f"live_trades_{broker}_2019_2026.csv", parse_dates=["entry_time", "exit_time"])
    return {f"live:{leg}": {"trades": _frame(g.entry_time, g.exit_time, g.r), "cal_end": "2022-12-31", "gruppe": "Live-Bein"}
            for leg, g in d.groupby("leg")}


def orb_is_only() -> dict:
    import research_orb_oel_filter as f
    data = f.load("2026-09-30")
    out = {}
    for inst in f.INSTRUMENTS:
        t = data[inst]["trades"]
        t = t[t["mode"] == "neutral"]
        ex = pd.DatetimeIndex(t.session) + pd.Timedelta(hours=16)
        out[f"orb_is_only:{inst}"] = {"trades": _frame(t.entry_time, ex, t.r), "cal_end": "2022-12-31", "gruppe": "Bruch"}
        # Schatten fuer das Regime-Signal (Ribbon-Spread): Trend-Modus mitgeben
        tt = data[inst]["trades"]
        tt = tt[tt["mode"] == "mit_trend"]
        out[f"orb_is_only:{inst}"]["shadow_trend"] = _frame(tt.entry_time, pd.DatetimeIndex(tt.session) + pd.Timedelta(hours=16), tt.r)
    return out


def zarattini() -> dict:
    from research_noise_area_momentum import COST_RT
    out = {}
    for inst in ("SP500", "NASDAQ"):
        d = pd.read_csv(ROOT / "noise_area_momentum" / "results" / f"diagnose_trades_{inst}.csv", parse_dates=["date"])
        d = d.dropna(subset=["gross_bps"])
        ex = d.date + pd.Timedelta(hours=16)
        out[f"zarattini:{inst}"] = {"trades": _frame(d.date + pd.Timedelta(hours=10), ex, d.gross_bps - COST_RT[inst]),
                                    "cal_end": "2022-12-31", "gruppe": "Bruch"}
    return out


def eu_open() -> dict:
    from research_eu_open_window import INSTRUMENTS, load_berlin, price_at
    from research_orb_cancel_at_sl_and_hold import ENTRY_SLIPPAGE_BPS, EXIT_SLIPPAGE_BPS, SPREAD_BPS
    out = {}
    for inst in INSTRUMENTS:
        if inst not in SPREAD_BPS:
            continue
        df = load_berlin(inst, "2018-07-01", "2026-09-30")
        a, b = price_at(df, "05:30"), price_at(df, "09:30")
        common = a.index.intersection(b.index)
        r = np.log(b.loc[common] / a.loc[common]).dropna()
        r = r[np.isfinite(r) & (r.abs() <= 0.20)] * 1e4 - (SPREAD_BPS[inst] + ENTRY_SLIPPAGE_BPS + EXIT_SLIPPAGE_BPS)
        idx = pd.DatetimeIndex(r.index).tz_localize(None).normalize()
        out[f"eu_open:{inst}"] = {"trades": _frame(idx + pd.Timedelta(hours=5, minutes=30), idx + pd.Timedelta(hours=9, minutes=30), r.values),
                                  "cal_end": "2020-12-31", "gruppe": "Bruch"}
    return out


def all_cases() -> dict:
    out = {}
    for fn in (orb_is_only, zarattini, eu_open, live_legs):
        out.update(fn())
    return out
