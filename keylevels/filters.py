"""Ausschluss-Markierungen nach Edge Card Regel 21-23 (markiert, nicht geloescht).

  rollover  Ereignis 21:00-23:00 UTC
  news      -30 Min/+2 h um High-Impact-Termine einer der beiden Waehrungen;
            Termine ohne bekannte Uhrzeit und alle H4-Signale: ganzer UTC-Tag
  highvol   20-Tage-Vola ueber dem 90. Perzentil des Vorjahres (Stand Vortag)

Uhrzeiten: US-Daten (CPI, NFP, Retail, GDP) 08:30 New York, FOMC 14:00 New
York. Eurostat und die uebrigen Notenbanken nur mit Datum -> ganzer Tag.
NZD hat keinen Termin im Repo-Kalender (Luecke, im Report ausgewiesen).
"""

import numpy as np
import pandas as pd

from keylevels.levels import candles

CB_FOR_CCY = {"EUR": "ECB", "GBP": "BOE", "JPY": "BOJ", "AUD": "RBA", "CAD": "BOC", "CHF": "SNB"}


def _news_tables():
    from bond_yield_indicator.calendar import get_meetings
    from news_calendar.eurostat_calendar import fetch_eur_release_dates_filtered
    from news_calendar.fred_releases import fetch_all_us_release_dates
    ny = "America/New_York"
    timed = {"USD": []}
    for d in fetch_all_us_release_dates("2016-01-01", "2026-10-16"):
        timed["USD"].append(pd.Timestamp(d.date()).tz_localize(ny) + pd.Timedelta(hours=8, minutes=30))
    for d in get_meetings("FOMC"):
        timed["USD"].append(pd.Timestamp(d.date()).tz_localize(ny) + pd.Timedelta(hours=14))
    untimed = {c: set() for c in ("USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD")}
    untimed["EUR"] |= set(pd.DatetimeIndex(fetch_eur_release_dates_filtered()).date)
    for ccy, bank in CB_FOR_CCY.items():
        untimed[ccy] |= set(get_meetings(bank).date)
    timed_utc = {c: pd.DatetimeIndex(v).tz_convert("UTC").sort_values() for c, v in timed.items()}
    return timed_utc, untimed


_CACHE = {}


def flag_events(ev: pd.DataFrame, sym: str, m1: pd.DataFrame) -> pd.DataFrame:
    if ev.empty:
        return ev
    if "news" not in _CACHE:
        _CACHE["news"] = _news_tables()
    timed, untimed = _CACHE["news"]
    ccys = (sym[:3], sym[3:])
    t = pd.to_datetime(ev["t"], utc=True)
    ev = ev.copy()
    ev["rollover"] = t.dt.hour.isin([21, 22]).to_numpy()
    day = t.dt.date
    untimed_day = day.isin(set().union(*(untimed[c] for c in ccys))).to_numpy()
    timed_days = set().union(*(set(timed[c].date) for c in ccys if c in timed))
    any_day = untimed_day | day.isin(timed_days).to_numpy()
    near = np.zeros(len(ev), bool)
    for c in ccys:
        ts = timed.get(c)
        if ts is None or not len(ts):
            continue
        tv = pd.DatetimeIndex(t).as_unit("ns").asi8
        tsv = ts.as_unit("ns").asi8
        j = np.searchsorted(tsv, tv + 30 * 60 * 10 ** 9)          # Termin <= t+30min
        prev = np.where(j > 0, tsv[np.maximum(j - 1, 0)], np.iinfo(np.int64).min // 2)
        near |= (prev >= tv - 2 * 3600 * 10 ** 9) & (j > 0)     # Termin >= t-2h
    # mit Uhrzeit: Fenster; ohne Uhrzeit: ganzer Tag; H4-Signale: jeder Termintag ganz
    ev["news"] = near | untimed_day | ((ev["tf"] == "H4").to_numpy() & any_day)
    # Hochvola-Regime je Handelstag (Vortageswert)
    if ("vol", sym) not in _CACHE:
        d = candles(m1, "D")
        r = np.log(d["close"]).diff()
        v20 = r.rolling(20).std()
        thr = v20.rolling(250, min_periods=120).quantile(0.9)
        _CACHE[("vol", sym)] = (v20 > thr).shift(1).fillna(False)
    hv = _CACHE[("vol", sym)]
    tday = (t.dt.tz_convert("America/New_York") + pd.Timedelta(hours=7)).dt.tz_localize(None).dt.normalize()
    ev["highvol"] = tday.map(hv).fillna(False).astype(bool).to_numpy()
    ev["excluded"] = ev["rollover"] | ev["news"] | ev["highvol"]
    return ev
