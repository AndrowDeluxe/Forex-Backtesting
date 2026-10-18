"""Ereignisse und Messung nach Edge Card Regel 8-15 und 24.

Ereignistypen (kind):
  touch      M1-Beruehrung; Treffer = Umkehr (zuerst G gegen den Anlauf)
  respected  Kerzenschluss zurueck auf der Anlaufseite; Signal gegen den Anlauf
  broken     Kerzenschluss jenseits des Levels; Signal mit dem Anlauf
  retest     nach broken: G weg, dann innerhalb 5 Kerzen erste Rueckkehr von der neuen
             Seite mit Schluss auf der Durchbruchseite; Signal in Durchbruchrichtung
Beim Engulfing ist nur der Anlauf von der erwarteten Seite zulaessig; Treffer
= Reaktion in Engulfing-Richtung (kind respected).

Messung: ab Startpreis minutengenau zuerst +G (hit) oder -G (fail); sonst open,
bewertet zum Schlusskurs am Fensterende. Beide in derselben M1-Kerze -> fail.
Oeffnet eine Kerze schon jenseits der Schwelle (Wochenend-Gap), zaehlt der
Eroeffnungskurs (Regel 24).
"""

import numpy as np
import pandas as pd

from smh_microstructure.costs import PIP, RT_PIPS

COMBOS = [("M1", 10, 1), ("M1", 20, 1), ("M15", 20, 2), ("M15", 30, 2),
          ("H1", 30, 5), ("H1", 50, 5), ("H4", 50, 10), ("H4", 100, 10)]  # (TF, G Pips, Fenster Tage)
RETEST_BARS = 5
GRID_PIPS = 100
PLACEBO_GRID = (13, 37, 63, 87)   # Pips-Versatz im 100er-Raster (weder 00 noch 50 noch 25/75)


class Series:
    """M1-Arrays + daraus gebildete Kerzen eines Timeframes, mit M1-Indexzuordnung."""

    def __init__(self, m1: pd.DataFrame):
        self.m1 = m1
        self.t = m1.index.as_unit("ns").asi8   # pandas 3: M1-Index liegt in ms vor -> einheitlich ns
        self.hi, self.lo = m1["high"].to_numpy(), m1["low"].to_numpy()
        self.op, self.cl = m1["open"].to_numpy(), m1["close"].to_numpy()
        self._tf = {}

    def tf(self, name: str) -> dict:
        if name in self._tf:
            return self._tf[name]
        if name == "M1":
            n = len(self.t)
            d = {"hi": self.hi, "lo": self.lo, "cl": self.cl, "t0": self.t,
                 "i_start": np.arange(n), "i_end": np.arange(1, n + 1)}
        else:
            idx = self.m1.index
            if name == "H4":
                key = ((idx.tz_convert("America/New_York") + pd.Timedelta(hours=7)).tz_localize(None)).floor("4h")
            else:
                key = idx.tz_localize(None).floor({"M15": "15min", "H1": "1h"}[name])
            codes, uniq = pd.factorize(key, sort=True)
            starts = np.flatnonzero(np.r_[True, codes[1:] != codes[:-1]])
            ends = np.r_[starts[1:], len(codes)]
            d = {"hi": np.maximum.reduceat(self.hi, starts), "lo": np.minimum.reduceat(self.lo, starts),
                 "cl": self.cl[ends - 1], "t0": self.t[starts], "i_start": starts, "i_end": ends}
        self._tf[name] = d
        return d


def outcome(s: Series, i0: int, p0: float, d: int, g: float, window_min: int):
    """(res, pnl in G, Ende-Index, unklar) ab M1-Index i0. unklar = +G und -G in derselben
    M1-Kerze (als fail gewertet; fuer die Gegenrichtung ebenfalls als Verlust zu werten)."""
    n = len(s.t)
    end_t = s.t[min(i0, n - 1)] + window_min * 60_000_000_000
    i_last = int(np.searchsorted(s.t, end_t, side="right")) - 1
    if i0 > i_last or i0 >= n:
        return "open", 0.0, i0, False
    tgt, stp = p0 + d * g, p0 - d * g
    lo_b = i0
    for span in (60, 1440, 10 ** 9):
        hi_b = min(i0 + span, i_last + 1)
        hi_a, lo_a = s.hi[lo_b:hi_b], s.lo[lo_b:hi_b]
        if d > 0:
            th, ts = hi_a >= tgt, lo_a <= stp
        else:
            th, ts = lo_a <= tgt, hi_a >= stp
        ih = np.flatnonzero(th)
        is_ = np.flatnonzero(ts)
        fh = ih[0] if len(ih) else None
        fs = is_[0] if len(is_) else None
        if fh is not None or fs is not None:
            if fs is not None and (fh is None or fs <= fh):
                j = lo_b + fs
                o = s.op[j]
                gap = (o <= stp) if d > 0 else (o >= stp)
                return "fail", (d * (o - p0) / g if gap else -1.0), j, fh is not None and fs == fh
            j = lo_b + fh
            o = s.op[j]
            gap = (o >= tgt) if d > 0 else (o <= tgt)
            return "hit", (d * (o - p0) / g if gap else 1.0), j, False
        if hi_b > i_last:
            break
        lo_b = hi_b
    return "open", d * (s.cl[i_last] - p0) / g, i_last, False


def _rec(base: dict, kind: str, sig: int, s: Series, i0: int, p0: float, g: float, win: int, t_ev) -> dict:
    res, pnl, j, amb = outcome(s, i0, p0, sig, g, win)
    return {**base, "kind": kind, "signal": sig, "t": t_ev, "p0": p0, "res": res, "pnl_g": pnl,
            "t_exit": s.t[min(j, len(s.t) - 1)], "ambig": amb}


def _close_time(s, tf, k) -> int:
    """Schlusszeitpunkt der Kerze k (Entscheidungszeitpunkt fuer Signal und Filter)."""
    return s.t[tf["i_end"][k] - 1] + 60_000_000_000


def _htf_after_touch(s, tf, k, L, g, approach, win, base, out):
    """Klassifiziert die Signalkerze k (HTF) und sucht ggf. den Retest. t = Kerzenschluss."""
    if (tf["cl"][k] - L) * approach < 0:          # Schluss zurueck auf der Anlaufseite
        out.append(_rec(base, "respected", -approach, s, tf["i_end"][k], tf["cl"][k], g, win, _close_time(s, tf, k)))
        return
    if tf["cl"][k] == L:
        return
    out.append(_rec(base, "broken", approach, s, tf["i_end"][k], tf["cl"][k], g, win, _close_time(s, tf, k)))
    # Retest: erst G jenseits (M1), dann erste Rueckkehr zum Level innerhalb RETEST_BARS Kerzen
    i_from = tf["i_end"][k]
    i_to = tf["i_end"][min(k + RETEST_BARS, len(tf["cl"]) - 1)]
    if i_from >= i_to:
        return
    away = (s.hi[i_from:i_to] >= L + g) if approach > 0 else (s.lo[i_from:i_to] <= L - g)
    back = (s.lo[i_from:i_to] <= L) if approach > 0 else (s.hi[i_from:i_to] >= L)
    ia, ib = np.flatnonzero(away), np.flatnonzero(back)
    if not len(ia) or not len(ib) or ib[0] <= ia[0]:
        return                                     # zurueck, bevor G erreicht war -> kein Retest
    m_back = i_from + ib[0]
    j = int(np.searchsorted(tf["i_end"], m_back, side="right"))   # Kerze, die die Rueckkehr enthaelt
    if j > k + RETEST_BARS or j >= len(tf["cl"]):
        return
    m_away_bar = int(np.searchsorted(tf["i_end"], i_from + ia[0], side="right"))
    if j <= m_away_bar:                            # G-Lauf und Rueckkehr in derselben Kerze: Reihenfolge unklar
        return
    if (tf["cl"][j] - L) * approach > 0:
        out.append(_rec(base, "retest", approach, s, tf["i_end"][j], tf["cl"][j], g, win, _close_time(s, tf, j)))


def instance_events(s: Series, levels: pd.DataFrame, tf_name: str, g_pips: float, win_days: int,
                    sym: str) -> list[dict]:
    """Ereignisse an zeitbegrenzten Leveln (je Level nur das erste Ereignis)."""
    tf = s.tf(tf_name)
    g = g_pips * PIP[sym]
    win = win_days * 1440
    out = []
    t_from = pd.DatetimeIndex(levels["t_from"]).as_unit("ns").asi8
    t_to = pd.DatetimeIndex(levels["t_to"]).as_unit("ns").asi8
    b0s = np.searchsorted(tf["t0"], t_from, side="left")
    b1s = np.searchsorted(tf["t0"], t_to, side="left")
    for r, b0, b1 in zip(levels.itertuples(index=False), b0s, b1s):
        if b1 - b0 < 2:
            continue
        L, want = r.price, int(r.dir)
        hi, lo = tf["hi"][b0:b1], tf["lo"][b0:b1]
        cand = []
        # Anlauf von unten (approach +1): erst G unter dem Level, dann erste Beruehrung
        if want in (0, -1):            # Engulfing bear: Level ueber dem Kurs -> Anlauf von unten
            a = np.flatnonzero(lo <= L - g)
            if len(a):
                k = np.flatnonzero(hi[a[0] + 1:] >= L)
                if len(k):
                    cand.append((a[0] + 1 + k[0], +1))
        if want in (0, 1):
            a = np.flatnonzero(hi >= L + g)
            if len(a):
                k = np.flatnonzero(lo[a[0] + 1:] <= L)
                if len(k):
                    cand.append((a[0] + 1 + k[0], -1))
        if not cand:
            continue
        kk, approach = min(cand)
        k = b0 + kk
        base = {"sym": sym, "type": r.type, "sub": r.sub, "placebo": int(getattr(r, "placebo", 0)),
                "tf": tf_name, "G": g_pips, "approach": approach, "level": L,
                "prev_body": float(getattr(r, "prev_body", np.nan))}
        if tf_name == "M1":
            # Beruehrungskerze: Durchlauf schon in derselben Kerze -> konservativ fail
            thr = (s.hi[k] >= L + g) if approach > 0 else (s.lo[k] <= L - g)
            if thr:
                both = (s.lo[k] <= L - g) if approach > 0 else (s.hi[k] >= L + g)
                out.append({**base, "kind": "touch", "signal": -approach, "t": s.t[k], "p0": L,
                            "res": "fail", "pnl_g": -1.0, "t_exit": s.t[k], "ambig": bool(both)})
            else:
                out.append(_rec(base, "touch", -approach, s, k + 1, L, g, win, s.t[k]))
        else:
            if (tf["cl"][k - 1] - L) * approach >= 0 if k > 0 else True:
                continue                               # Vorkerze schloss nicht auf der Anlaufseite
            _htf_after_touch(s, tf, k, L, g, approach, win, base, out)
    return out


def grid_events(s: Series, tf_name: str, g_pips: float, win_days: int, sym: str, offset_pips: float,
                level_type: str, placebo: int) -> list[dict]:
    """Dauerhafte Rasterlevel (runde/halbe Zahl bzw. Schein-Raster). Je frischem Anlauf ein Ereignis."""
    tf = s.tf(tf_name)
    pip = PIP[sym]
    step, off, g = GRID_PIPS * pip, offset_pips * pip, g_pips * pip
    win = win_days * 1440
    hi, lo, cl = tf["hi"], tf["lo"], tf["cl"]
    k_lo = np.ceil((lo - off) / step - 1e-9).astype(np.int64)
    k_hi = np.floor((hi - off) / step + 1e-9).astype(np.int64)
    last_touch: dict[int, int] = {}
    lookback = {"M1": 1440 * 5, "M15": 96 * 5, "H1": 24 * 5, "H4": 6 * 5}[tf_name]
    out = []
    for k in np.nonzero(k_hi >= k_lo)[0]:
        if k == 0:
            continue
        for lv in range(k_lo[k], k_hi[k] + 1):
            L = lv * step + off
            prev = last_touch.get(lv)
            last_touch[lv] = k
            start = max(prev + 1 if prev is not None else k - lookback, 0)
            if start >= k:
                continue
            if cl[k - 1] < L and lo[start:k].min() <= L - g:
                approach = +1
            elif cl[k - 1] > L and hi[start:k].max() >= L + g:
                approach = -1
            else:
                continue
            base = {"sym": sym, "type": level_type, "sub": f"off{offset_pips:g}", "placebo": placebo,
                    "tf": tf_name, "G": g_pips, "approach": approach, "level": L}
            if tf_name == "M1":
                thr = (s.hi[k] >= L + g) if approach > 0 else (s.lo[k] <= L - g)
                if thr:
                    both = (s.lo[k] <= L - g) if approach > 0 else (s.hi[k] >= L + g)
                    out.append({**base, "kind": "touch", "signal": -approach, "t": s.t[k], "p0": L,
                                "res": "fail", "pnl_g": -1.0, "t_exit": s.t[k], "ambig": bool(both)})
                else:
                    out.append(_rec(base, "touch", -approach, s, k + 1, L, g, win, s.t[k]))
            else:
                _htf_after_touch(s, tf, k, L, g, approach, win, base, out)
    return out


def placebo_shift(levels: pd.DataFrame, g_pips: float, sym: str, copies: int = 2, seed: int = 7) -> pd.DataFrame:
    """Schein-Level: jedes Level um zufaellige +-(0,5..2) G verschoben, gleiche Gueltigkeit."""
    rng = np.random.default_rng(seed)
    parts = []
    for c in range(copies):
        shift = rng.uniform(0.5, 2.0, len(levels)) * rng.choice([-1, 1], len(levels)) * g_pips * PIP[sym]
        parts.append(levels.assign(price=levels["price"].to_numpy() + shift, placebo=c + 1))
    return pd.concat(parts, ignore_index=True)


def cost_in_g(sym: str, g_pips: float) -> float:
    return RT_PIPS[sym] / g_pips
