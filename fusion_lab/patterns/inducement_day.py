"""Dennis' „Daily Inducement Day“ -- Detektor (Baustein, Plan 24.11.2026).

Quelle: [[smh-dennis-volumen-ltf-inducement-day]], Abschnitt 1. Short beschrieben, Long laeuft ueber
gespiegelte Preise (scan(..., side="long") negiert O/H/L/C, Profile und Ziele werden zurueckgespiegelt).

Je CME-Tag d mit T-1 = Vortag, T-2 = Tag davor (abgeschlossene Profile):
  trend       POC(T-1) < POC(T-2) und VA-Mitte(T-1) < VA-Mitte(T-2)            („POCs traden tiefer“)
  Sweep       Tageshoch > Hoch(T-1); sobald Tageshoch > Hoch(T-2): kein Trade an diesem Tag
  inducement  am Ausloeser: laufender POC > POC(T-1) und laufende VA-Mitte > VA-Mitte(T-1)
  poi_va      Tageshoch bis zum Ausloeser >= VAL(T-2)                              (Nutzer 24.11.)
  poi_fvg     offenes baerisches H1-FVG (vor Tagesbeginn, noch nicht angetestet) mit Oberkante > Hoch(T-1),
              vom Tageshoch erreicht
  poi_ob      Order Block: letzte bullische H1-Kerze vor einem H1-Schluss unter dem letzten bestaetigten
              Swing-Tief (5 Tage Rueckblick, noch nicht angetestet), Oberkante > Hoch(T-1), vom Tageshoch erreicht
Ausloeser (je Tag der erste, Flags werden dort ausgewertet):
  HTF  erster M30-Schluss < Hoch(T-1) nach dem Sweep
  LTF  erster M5-Schluss < Hoch(T-1) und < letztem bestaetigten M5-Swing-Tief vor dem Tageshoch (BOS)
Einstieg = Schluss der Ausloeser-Kerze, Stop = Tageshoch bis dahin.
Zusatzmerkmale (Stufe 3): fib_ok (Tageshoch <= Hoch(T-1) + 0,272 x Range(T-1)); vol_div (Volumen der
zweiten Haelfte des Anlaufs < erste Haelfte) und delta_kipp (Delta-Summe vom Tageshoch bis Einstieg < 0).
Kein Vorgriff: laufendes Profil, Swings (k Kerzen spaeter bestaetigt) und POI nur aus Kerzen bis zum Ausloeser.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from fusion_lab.patterns.volume_profile import VA_PCT, Histogram, cme_day, day_profiles

K = 2            # Fractal-Swing links/rechts (wie keylevels/bos.py)
POI_DAYS = 5     # H1-Rueckblick fuer FVG/OB
FIB_CAP = 0.272


def _mirror(bars: pd.DataFrame) -> pd.DataFrame:
    m = bars.copy()
    m["Open"], m["High"], m["Low"], m["Close"] = -bars["Open"], -bars["Low"], -bars["High"], -bars["Close"]
    return m


def _swing_lows(l: np.ndarray, k: int = K) -> np.ndarray:
    """True an i, wenn l[i] striktes Minimum von l[i-k..i+k]; bekannt erst ab Kerze i+k."""
    out = np.zeros(len(l), bool)
    for i in range(k, len(l) - k):
        w = l[i - k:i + k + 1]
        out[i] = l[i] == w.min() and (w == l[i]).sum() == 1
    return out


def _h1(bars: pd.DataFrame) -> pd.DataFrame:
    return bars.resample("1h").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()


def _poi_zones(h1: pd.DataFrame, t0: pd.Timestamp) -> tuple[list, list]:
    """Offene baerische FVGs und Order Blocks aus H1-Kerzen vor t0 (Zonen als (unten, oben))."""
    x = h1[(h1.index < t0) & (h1.index >= t0 - pd.Timedelta(days=POI_DAYS))]
    o, h, l, c = (x[k].to_numpy() for k in ("Open", "High", "Low", "Close"))
    n = len(x)
    fvg, ob = [], []
    for k in range(2, n):
        if h[k] < l[k - 2]:                                    # baerische Luecke zwischen k-2 und k
            lo_, hi_ = h[k], l[k - 2]
            if k + 1 >= n or (h[k + 1:] < lo_).all():          # seither nicht angetestet
                fvg.append((lo_, hi_))
    sl = _swing_lows(l)
    last_sl = np.nan
    for i in range(n):
        j = i - K                                              # an i bestaetigtes Swing-Tief
        if j >= 0 and sl[j]:
            last_sl = l[j]
        if not np.isnan(last_sl) and c[i] < last_sl:           # H1-Schluss bricht das Swing-Tief
            bull = [m for m in range(max(0, i - 24), i) if c[m] > o[m]]
            if bull:
                m = bull[-1]
                if m + 1 >= n or (h[m + 1:] < l[m]).all():
                    ob.append((l[m], h[m]))
            last_sl = np.nan
    return fvg, ob


def scan(bars: pd.DataFrame, step: float, side: str = "short") -> pd.DataFrame:
    """Alle Tage mit Sweep von Hoch(T-1) und Ausloeser; Flags fuer Varianten und Kontrolle."""
    x = bars if side == "short" else _mirror(bars)
    sg = 1.0 if side == "short" else -1.0
    prof = day_profiles(x, step)
    prof["vam"] = (prof["val"] + prof["vah"]) / 2
    days = cme_day(x.index)
    t = x.index
    o, h, l, c, v = (x[k].to_numpy() for k in ("Open", "High", "Low", "Close", "Volume"))
    delta = np.sign(c - o) * v
    sl = _swing_lows(l)
    h1 = _h1(x)
    bar_len = pd.Series(t[1:] - t[:-1]).median()
    m30_end = ((t + bar_len).minute % 30 == 0)
    starts = np.r_[0, np.flatnonzero(days[1:] != days[:-1]) + 1, len(days)]
    plist = prof.index.to_numpy()
    rows = []
    for di in range(2, len(starts) - 1):
        a, b = starts[di], starts[di + 1]
        d = days[a]
        pi = np.searchsorted(plist, d)
        if pi < 2 or plist[pi] != d:
            continue
        p1, p2 = prof.iloc[pi - 1], prof.iloc[pi - 2]
        H1, L1, H2 = p1["high"], p1["low"], p2["high"]
        trend = p1["poc"] < p2["poc"] and p1["vam"] < p2["vam"]
        fvg, ob = _poi_zones(h1, t[a])
        hist = Histogram(l[a:b].min(), h[a:b].max(), step)
        hi_so_far, hi_idx, swept, dead = -np.inf, a, False, False
        done = {"HTF": False, "LTF": False}
        for i in range(a, b):
            hist.add(l[i], h[i], v[i])
            if h[i] > hi_so_far:
                hi_so_far, hi_idx = h[i], i
            if hi_so_far > H2:
                dead = True
            if dead:
                break
            if hi_so_far > H1:
                swept = True
            if not swept:
                continue
            trig = []
            if not done["HTF"] and m30_end[i] and c[i] < H1:
                trig.append("HTF")
            if not done["LTF"] and c[i] < H1:
                ref = np.nan
                for j in range(min(hi_idx, i - K) - 1, max(a - 50, 0) - 1, -1):   # letztes bestaetigtes Swing-Tief vor dem Hoch
                    if sl[j] and j + K <= i:
                        ref = l[j]
                        break
                if not np.isnan(ref) and c[i] < ref:
                    trig.append("LTF")
            if not trig:
                continue
            val, poc, vah = hist.poc_va(VA_PCT)
            run = v[max(a, hi_idx - 12):hi_idx + 1]
            half = len(run) // 2
            feat = {
                "day": pd.Timestamp(d), "side": side, "t": t[i], "i": i,
                "entry": c[i], "stop": hi_so_far, "H1": H1, "L1": L1, "H2": H2,
                "poc2": p2["poc"], "trend": trend,
                "inducement": poc > p1["poc"] and (val + vah) / 2 > p1["vam"],
                "poi_va": hi_so_far >= p2["val"],
                "poi_fvg": any(hi_so_far >= zl and zh > H1 for zl, zh in fvg),
                "poi_ob": any(hi_so_far >= zl and zh > H1 for zl, zh in ob),
                "fib_ok": hi_so_far <= H1 + FIB_CAP * (H1 - L1),
                "vol_div": half > 0 and run[half:].mean() < run[:half].mean(),
                "delta_kipp": delta[hi_idx:i + 1].sum() < 0,
            }
            for e in trig:
                done[e] = True
                rows.append({**feat, "einstieg": e})
            if all(done.values()):
                break
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    for col in ("entry", "stop", "H1", "L1", "H2", "poc2"):
        out[col] = out[col] * sg                                # zurueck in echte Preise
    return out


def simulate(ctx: dict, ev: pd.Series, target: float, cost: float) -> dict | None:
    """Trade ab Kerze nach dem Ausloeser bis Ende des naechsten CME-Tags; Stop vor Ziel in derselben Kerze."""
    short = ev["side"] == "short"
    entry, stop = ev["entry"], ev["stop"]
    risk = (stop - entry) if short else (entry - stop)
    if risk <= 0 or (short and target >= entry) or (not short and target <= entry):
        return None
    days = ctx["cme_day"]
    i0 = int(ev["i"])
    last_day = days[i0] + np.timedelta64(1, "D")
    while last_day not in ctx["day_set"] and last_day < days[-1]:
        last_day += np.timedelta64(1, "D")                       # Wochenende ueberspringen
    end = int(np.searchsorted(days, last_day, side="right")) - 1
    h, l, c = ctx["hlc"]
    for k in range(i0 + 1, end + 1):
        if (h[k] >= stop) if short else (l[k] <= stop):
            return {"r_gross": -1.0, "r": -1.0 - cost / risk, "exit": "stop", "risk": risk}
        if (l[k] <= target) if short else (h[k] >= target):
            g = abs(target - entry) / risk
            return {"r_gross": g, "r": g - cost / risk, "exit": "ziel", "risk": risk}
    g = ((entry - c[end]) if short else (c[end] - entry)) / risk
    return {"r_gross": g, "r": g - cost / risk, "exit": "zeit", "risk": risk}


def prepare(bars: pd.DataFrame) -> dict:
    """Hilfsdaten fuer simulate()."""
    days = cme_day(bars.index)
    return {"cme_day": days, "day_set": set(days),
            "hlc": (bars["High"].to_numpy(), bars["Low"].to_numpy(), bars["Close"].to_numpy())}
