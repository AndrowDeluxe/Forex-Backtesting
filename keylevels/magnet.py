"""Magnet-Trade: Einstieg in Richtung Level, BEVOR es beruehrt wird (Edge Card Regeln 31-34, Plan 19.10.2026).

Ausloeser: Kurs war seit Gueltigkeitsbeginn bzw. letzter Levelberuehrung mindestens 2*D vom
Level entfernt (Anlaufseite) und erreicht dann erstmals die Linie Level-D (von unten) bzw.
Level+D (von oben). Einstieg Stop-Order an dieser Linie in Richtung Level (Gap -> Eroeffnung).
Stop D gegen uns. Ziel 1 = Level (1:1), Ziel 2 = Level + D (2:1). Fenster 1 Tag.
Fuell-Minute: nur der Schlusskurs entscheidet (Stop/Ziel sicher nach der Fuellung), sonst ab Folgeminute.
"""

import numpy as np
import pandas as pd

from keylevels.events import GRID_PIPS, Series
from smh_microstructure.costs import PIP, RT_PIPS

D_LIST = (10, 20)
WINDOW_MIN = 1440


def outcome2(s: Series, i0: int, p0: float, d: int, tgt: float, stop: float, unit: float):
    """(res, pnl in D, ambig): wer zuerst, Ziel oder Stop. Gleiche Minute -> fail."""
    n = len(s.t)
    end_t = s.t[min(i0, n - 1)] + WINDOW_MIN * 60_000_000_000
    i_last = int(np.searchsorted(s.t, end_t, side="right")) - 1
    if i0 > i_last or i0 >= n:
        return "open", 0.0, False
    lo_b = i0
    for span in (60, 1440, 10 ** 9):
        hi_b = min(i0 + span, i_last + 1)
        h, l = s.hi[lo_b:hi_b], s.lo[lo_b:hi_b]
        th = (h >= tgt) if d > 0 else (l <= tgt)
        ts = (l <= stop) if d > 0 else (h >= stop)
        ih, is_ = np.flatnonzero(th), np.flatnonzero(ts)
        fh = ih[0] if len(ih) else None
        fs = is_[0] if len(is_) else None
        if fh is not None or fs is not None:
            if fs is not None and (fh is None or fs <= fh):
                j = lo_b + fs
                o = s.op[j]
                gap = (o <= stop) if d > 0 else (o >= stop)
                px = o if gap else stop
                return "fail", d * (px - p0) / unit, fh is not None and fs == fh
            j = lo_b + fh
            o = s.op[j]
            gap = (o >= tgt) if d > 0 else (o <= tgt)
            px = o if gap else tgt
            return "hit", d * (px - p0) / unit, False
        if hi_b > i_last:
            break
        lo_b = hi_b
    return "open", d * (s.cl[i_last] - p0) / unit, False


def _measure(s: Series, k: int, line: float, L: float, d: int, D: float, base: dict) -> dict:
    o = s.op[k]
    p0 = max(o, line) if d > 0 else min(o, line)          # Stop-Order: Gap -> schlechterer Fill
    stop = p0 - d * D
    rec = {**base, "t": s.t[k], "price": p0, "dir": d}
    # Fuell-Minute: Stop-Order wird von der Anlaufseite her gefuellt, das Minuten-Extrem auf der
    # Stop-Seite liegt fast immer VOR der Fuellung. Entschieden wird dort nur ueber den Schluss
    # (sicher nach der Fuellung); sonst ab der Folgeminute (Aenderung 19.10., vor dem vollen Lauf).
    c = s.cl[k]
    stop_now = (c <= stop) if d > 0 else (c >= stop)
    for name, tgt in (("lvl", L), ("thru", L + d * D)):
        tgt_now = (c >= tgt) if d > 0 else (c <= tgt)
        if stop_now:
            res, pnl, amb = "fail", d * (c - p0) / D, False
        elif tgt_now:
            res, pnl, amb = "hit", d * (tgt - p0) / D, False
        else:
            res, pnl, amb = outcome2(s, k + 1, p0, d, tgt, stop, D)
        rec[f"res_{name}"], rec[f"pnl_{name}"], rec[f"amb_{name}"] = res, pnl, amb
    return rec


def instance_triggers(s: Series, levels: pd.DataFrame, d_pips: float, sym: str) -> list[dict]:
    """Zeitbegrenzte Level: je Level hoechstens ein Magnet-Einstieg."""
    D = d_pips * PIP[sym]
    t_from = pd.DatetimeIndex(levels["t_from"]).as_unit("ns").asi8
    t_to = pd.DatetimeIndex(levels["t_to"]).as_unit("ns").asi8
    b0s = np.searchsorted(s.t, t_from, side="left")
    b1s = np.searchsorted(s.t, t_to, side="left")
    out = []
    for r, b0, b1 in zip(levels.itertuples(index=False), b0s, b1s):
        if b1 - b0 < 2:
            continue
        L = r.price
        hi, lo = s.hi[b0:b1], s.lo[b0:b1]
        cand = []
        a = np.flatnonzero(lo <= L - 2 * D)                 # Anlauf von unten
        if len(a):
            k = np.flatnonzero(hi[a[0] + 1:] >= L - D)
            if len(k):
                cand.append((a[0] + 1 + k[0], +1))
        a = np.flatnonzero(hi >= L + 2 * D)                 # Anlauf von oben
        if len(a):
            k = np.flatnonzero(lo[a[0] + 1:] <= L + D)
            if len(k):
                cand.append((a[0] + 1 + k[0], -1))
        if not cand:
            continue
        kk, d = min(cand)
        k = b0 + kk
        base = {"sym": sym, "type": r.type, "sub": r.sub, "placebo": int(getattr(r, "placebo", 0)),
                "D": d_pips, "level": L}
        out.append(_measure(s, k, L - d * D, L, d, D, base))
    return out


def grid_triggers(s: Series, d_pips: float, sym: str, offset_pips: float, level_type: str, placebo: int) -> list[dict]:
    """Dauerhafte Rasterlevel: ein Einstieg je frischem Anlauf; neuer Zyklus nach Levelberuehrung."""
    pip = PIP[sym]
    step, off, D = GRID_PIPS * pip, offset_pips * pip, d_pips * pip
    hi, lo, cl = s.hi, s.lo, s.cl
    n = len(hi)
    lookback = 1440 * 5

    def rng(shift):
        return (np.ceil((lo - shift - off) / step - 1e-9).astype(np.int64),
                np.floor((hi - shift - off) / step + 1e-9).astype(np.int64))

    lv_lo, lv_hi = rng(0.0)          # Level selbst im Kerzenbereich
    up_lo, up_hi = rng(-D)           # Linie L-D (Anlauf von unten): L-D in [lo,hi] <=> L in [lo+D, hi+D]
    dn_lo, dn_hi = rng(+D)           # Linie L+D (Anlauf von oben)
    active = np.nonzero((lv_hi >= lv_lo) | (up_hi >= up_lo) | (dn_hi >= dn_lo))[0]
    last_touch: dict[int, int] = {}
    used: dict[tuple[int, int], int] = {}
    out = []
    for k in active:
        if k == 0:
            continue
        # Ausloeser zuerst pruefen (Levelberuehrung derselben Kerze kommt danach)
        for d, a_lo, a_hi in ((+1, up_lo[k], up_hi[k]), (-1, dn_lo[k], dn_hi[k])):
            for lv in range(a_lo, a_hi + 1):
                L = lv * step + off
                line = L - d * D
                if not ((cl[k - 1] < line) if d > 0 else (cl[k - 1] > line)):
                    continue
                prev = last_touch.get(lv, -1)
                if used.get((lv, d)) == prev:
                    continue                                 # in diesem Zyklus schon ausgeloest
                start = prev + 1 if prev >= 0 else max(k - lookback, 0)
                if start >= k:
                    continue
                far = (lo[start:k].min() <= L - 2 * D) if d > 0 else (hi[start:k].max() >= L + 2 * D)
                if not far:
                    continue
                used[(lv, d)] = prev
                base = {"sym": sym, "type": level_type, "sub": f"off{offset_pips:g}", "placebo": placebo,
                        "D": d_pips, "level": L}
                out.append(_measure(s, k, line, L, d, D, base))
        for lv in range(lv_lo[k], lv_hi[k] + 1):
            last_touch[lv] = k
    return out


def cost_in_d(sym: str, d_pips: float) -> float:
    return RT_PIPS[sym] / d_pips
