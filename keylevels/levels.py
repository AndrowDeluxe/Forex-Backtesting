"""Level-Erzeugung fuer die Key-Level-Edge-Card (knowledge/projects/keylevel-edge-card-final.md).

Alle Kerzen werden aus M1-Bid (UTC) gebildet. Handelstag = 17:00-17:00 New York
(wie MT5-Broker mit GMT+2/+3); H4-Kerzen beginnen 17/21/01/05/09/13 Uhr NY.

Zeitbegrenzte Level kommen als DataFrame mit Spalten
    type, sub, price, t_from, t_to, dir
(dir: erwartete Richtung, nur Engulfing; sonst 0). Runde und halbe Zahlen sind
dauerhaft und werden in events.py direkt als Raster behandelt.
"""

import numpy as np
import pandas as pd

NY = "America/New_York"
SHIFT = pd.Timedelta(hours=7)  # 17:00 NY + 7h = 00:00 -> Handelstag-Grenze


def _trading_key(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Handelstag je Zeitstempel: NY-Zeit + 7 h, auf den Tag abgeschnitten."""
    return (idx.tz_convert(NY) + SHIFT).tz_localize(None).normalize()


def candles(m1: pd.DataFrame, freq: str) -> pd.DataFrame:
    """D (Handelstag), W (Woche), M (Monat) oder 'H4'. Spalten open/high/low/close/t_start/t_end
    (t_end = Zeitstempel NACH der letzten M1-Kerze, UTC)."""
    idx = m1.index
    if freq == "H4":
        key = ((idx.tz_convert(NY) + SHIFT).tz_localize(None)).floor("4h")
    else:
        day = _trading_key(idx)
        if freq == "D":
            key = day
        elif freq == "W":
            key = day.to_period("W-SUN").start_time  # Woche Mo-So nach Handelstag-Datum
        elif freq == "M":
            key = day.to_period("M").start_time
        else:
            raise ValueError(freq)
    g = m1.groupby(key)
    out = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(),
                        "close": g["close"].last(), "n": g.size()})
    ts = pd.Series(idx, index=idx)
    out["t_start"] = ts.groupby(key).first().to_numpy()
    out["t_end"] = (ts.groupby(key).last() + pd.Timedelta(minutes=1)).to_numpy()
    # Sonntags-Stummel (< 2 h Handel) gehoeren zum Montag -- bei D sauber durch die
    # 17:00-Grenze; sehr kurze Kerzen (Feiertage) bleiben drin, sind aber selten.
    return out[out["n"] > 0]


def engulfing_levels(c: pd.DataFrame, tf_name: str, valid_bars: int = 5) -> pd.DataFrame:
    """Koerper umschliesst Koerper: Vorkerze gegenlaeufig, Folgekerze schliesst jenseits
    des Vorkerzen-Opens. Level = Open der Engulfing-Kerze, gueltig ab deren Schluss
    bis zum Ende der `valid_bars`-ten Folgekerze."""
    o, cl = c["open"].to_numpy(), c["close"].to_numpy()
    t_end = c["t_end"].to_numpy()
    rows = []
    for k in range(1, len(c) - 1):
        prev_bear, prev_bull = cl[k - 1] < o[k - 1], cl[k - 1] > o[k - 1]
        if prev_bear and cl[k] > o[k] and cl[k] > o[k - 1]:
            d = +1
        elif prev_bull and cl[k] < o[k] and cl[k] < o[k - 1]:
            d = -1
        else:
            continue
        j = min(k + valid_bars, len(c) - 1)
        rows.append({"type": f"engulf_{tf_name}", "sub": "bull" if d > 0 else "bear", "price": o[k],
                     "t_from": t_end[k], "t_to": t_end[j], "dir": d,
                     "prev_body": abs(cl[k - 1] - o[k - 1]), "body": abs(cl[k] - o[k]),
                     "mid": (o[k] + cl[k]) / 2, "close_px": cl[k]})
    return pd.DataFrame(rows)


def candle_open_control(c: pd.DataFrame, tf_name: str, valid_bars: int = 5) -> pd.DataFrame:
    """Gegenprobe: Open JEDER Kerze ohne Engulfing (gleiche Gueltigkeit), Richtung = Kerzenrichtung."""
    o, cl, t_end = c["open"].to_numpy(), c["close"].to_numpy(), c["t_end"].to_numpy()
    rows = []
    for k in range(1, len(c) - 1):
        engulf = ((cl[k - 1] < o[k - 1]) and cl[k] > o[k - 1] and cl[k] > o[k]) or \
                 ((cl[k - 1] > o[k - 1]) and cl[k] < o[k - 1] and cl[k] < o[k])
        if engulf or cl[k] == o[k]:
            continue
        j = min(k + valid_bars, len(c) - 1)
        rows.append({"type": f"plainopen_{tf_name}", "sub": "bull" if cl[k] > o[k] else "bear",
                     "price": o[k], "t_from": t_end[k], "t_to": t_end[j], "dir": 1 if cl[k] > o[k] else -1})
    return pd.DataFrame(rows)


def prev_period_levels(c: pd.DataFrame, name: str, lag: int = 1) -> pd.DataFrame:
    """Hoch/Tief der Vorperiode (lag=1), gueltig waehrend der ganzen Folgeperiode."""
    rows = []
    for k in range(lag, len(c)):
        src = c.iloc[k - lag]
        for sub, px in (("high", src["high"]), ("low", src["low"])):
            rows.append({"type": name, "sub": sub, "price": px, "t_from": c["t_start"].iloc[k],
                         "t_to": c["t_end"].iloc[k], "dir": 0})
    return pd.DataFrame(rows)


def pivot_levels(c: pd.DataFrame, name: str, lag: int = 1) -> pd.DataFrame:
    """Klassische Floor-Pivots aus der Vorperiode (lag=1) bzw. vorletzten (lag=2, Gegenprobe)."""
    rows = []
    for k in range(lag, len(c)):
        h, l, cl = c["high"].iloc[k - lag], c["low"].iloc[k - lag], c["close"].iloc[k - lag]
        p = (h + l + cl) / 3
        for sub, px in (("P", p), ("R1", 2 * p - l), ("S1", 2 * p - h), ("R2", p + (h - l)), ("S2", p - (h - l))):
            rows.append({"type": name, "sub": sub, "price": px, "t_from": c["t_start"].iloc[k],
                         "t_to": c["t_end"].iloc[k], "dir": 0})
    return pd.DataFrame(rows)


SESSIONS = {"asia": (0, 8), "london": (8, 13), "ny": (13, 21)}  # UTC


def session_levels(m1: pd.DataFrame) -> pd.DataFrame:
    """Hoch/Tief der abgeschlossenen Session, gueltig 24 h ab Sessionende."""
    rows = []
    day = m1.index.normalize()
    hours = m1.index.hour
    for name, (h0, h1) in SESSIONS.items():
        sub = m1[(hours >= h0) & (hours < h1)]
        g = sub.groupby(sub.index.normalize())
        hi, lo, n = g["high"].max(), g["low"].min(), g.size()
        for d in hi.index:
            if n[d] < 0.5 * (h1 - h0) * 60:  # halbe Session fehlt (Wochenende/Feiertag)
                continue
            t_from = d + pd.Timedelta(hours=h1)
            for s, px in (("high", hi[d]), ("low", lo[d])):
                rows.append({"type": "session", "sub": f"{name}_{s}", "price": px, "t_from": t_from,
                             "t_to": t_from + pd.Timedelta(hours=24), "dir": 0})
    return pd.DataFrame(rows)


def all_instance_levels(m1: pd.DataFrame) -> pd.DataFrame:
    """Alle zeitbegrenzten Level inkl. der in der Edge Card vorgesehenen Kontrollgruppen."""
    d, w, mo, h4 = (candles(m1, f) for f in ("D", "W", "M", "H4"))
    parts = [
        engulfing_levels(d, "D1"), engulfing_levels(h4, "H4"),
        candle_open_control(d, "D1"), candle_open_control(h4, "H4"),
        prev_period_levels(w, "week"),
        session_levels(m1),
        pivot_levels(d, "pivot_D"), pivot_levels(w, "pivot_W"), pivot_levels(mo, "pivot_M"),
        pivot_levels(d, "pivot2_D", lag=2), pivot_levels(w, "pivot2_W", lag=2), pivot_levels(mo, "pivot2_M", lag=2),
    ]
    out = pd.concat([p for p in parts if len(p)], ignore_index=True)
    for col in ("t_from", "t_to"):
        out[col] = pd.to_datetime(out[col], utc=True)
    return out


def engulf_variants(eng: pd.DataFrame) -> pd.DataFrame:
    """Gegenproben zum Engulfing: Kerzenmitte und Close statt Open (gleiche Gueltigkeit/Richtung)."""
    mid = eng.assign(type=eng["type"].str.replace("engulf", "engulfmid"), price=eng["mid"])
    cls = eng.assign(type=eng["type"].str.replace("engulf", "engulfclose"), price=eng["close_px"])
    return pd.concat([mid, cls], ignore_index=True)
