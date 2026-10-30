"""Doppel-BOS-Einstieg an Key Levels (Plan 18.10.2026, Edge Card Feld 02 "Einstieg").

Ablauf je frischer M1-Beruehrung (Ausloeser aus Stufe 1, Anlauf >= 20 Pips):
  1. BOS 1: Schluss einer Kerze jenseits des letzten BESTAETIGTEN Swings
     (Variante A: M5, Variante B: M15).
  2. Danach Stop-Order am naechsten bestaetigten M5-Swing in dieselbe Richtung
     (Swing-Kerze nach BOS 1, Bestaetigung k Kerzen spaeter). Fuellung = BOS 2.
  3. Beobachtungsfenster 8 h ab Beruehrung; ein BOS 1 in Gegenrichtung
     verwirft die laufende Folge. Es zaehlt der erste gefuellte Einstieg.
Richtung: gegen den Anlauf = Umkehr, mit dem Anlauf = Durchlauf.

Kein Blick in die Zukunft: Swings werden erst k Kerzen nach dem Extrem
verwendet (detect_fractal_swings), die Order erst danach aktiv.
"""

import numpy as np
import pandas as pd

from gold_smc_htf_ltf.structure import detect_fractal_swings, track_external_range_liquidity
from keylevels.events import Series, outcome

K_SWING = 2           # M5/M15-Fractal wie in der August-Umsetzung (ANNAHME)
WATCH_MIN = 8 * 60    # Beobachtungsfenster ab Beruehrung (ANNAHME)
G_LIST = (10, 20, 30)
WIN_DAYS = {10: 1, 20: 1, 30: 2}


class Structure:
    """Bestaetigte Swings eines Timeframes als Arrays (Bezug: Kerzenindex)."""

    def __init__(self, s: Series, tf_name: str):
        tf = s.tf(tf_name)
        df = pd.DataFrame({"high": tf["hi"], "low": tf["lo"], "close": tf["cl"]})
        df = track_external_range_liquidity(detect_fractal_swings(df, k=K_SWING))
        self.tf = tf
        self.erl_hi = df["erl_high"].to_numpy()          # Stand NACH Schluss der Kerze i
        self.erl_lo = df["erl_low"].to_numpy()
        n = len(df)
        self.sh_conf = df["swing_high_confirmed"].to_numpy()   # an Kerze i bestaetigt (Swing bei i-k)
        self.sl_conf = df["swing_low_confirmed"].to_numpy()
        self.sh_px = df["swing_high_price"].to_numpy()
        self.sl_px = df["swing_low_price"].to_numpy()
        self.n = n


def _bar_at(tf: dict, t_ns: int) -> int:
    """Erste Kerze, die bei oder nach t beginnt."""
    return int(np.searchsorted(tf["t0"], t_ns, side="left"))


def bos1_events(s: Series, st: Structure, t_from: int, t_end: int) -> list[tuple[int, int]]:
    """BOS-1-Ereignisse (Richtung, Schlusszeit) zwischen t_from und t_end: Kerzenschluss
    jenseits des letzten bestaetigten Swings; je gebrochenem Swing nur einmal."""
    tf = st.tf
    b = max(_bar_at(tf, t_from), 1)
    done_hi, done_lo = np.nan, np.nan
    ev = []
    while b < st.n and tf["t0"][b] < t_end:
        c, lo_ref, hi_ref = tf["cl"][b], st.erl_lo[b - 1], st.erl_hi[b - 1]
        t_close = s.t[tf["i_end"][b] - 1] + 60_000_000_000
        if not np.isnan(lo_ref) and c < lo_ref and lo_ref != done_lo:
            ev.append((-1, t_close))
            done_lo = lo_ref
        if not np.isnan(hi_ref) and c > hi_ref and hi_ref != done_hi:
            ev.append((+1, t_close))
            done_hi = hi_ref
        b += 1
    return ev


def find_trigger(s: Series, m5: Structure, bos1: Structure, t_touch: int) -> dict | None:
    """Erster gefuellter Doppel-BOS nach t_touch. bos1 = Struktur fuer BOS 1 (M5 oder M15).
    Ein BOS 1 in Gegenrichtung storniert die offene Stop-Order der anderen Richtung."""
    t_end = t_touch + WATCH_MIN * 60_000_000_000
    ev = bos1_events(s, bos1, t_touch, t_end)
    best = None
    for n, (d, t1) in enumerate(ev):
        t_cancel = next((t for dd, t in ev[n + 1:] if dd == -d), t_end)
        trig = _fill_after(s, m5, d, t1, t_cancel)
        if trig is not None and (best is None or trig["t_fill"] < best["t_fill"]):
            best = trig
    return best


def _fill_after(s: Series, m5: Structure, d: int, t1: int, t_end: int) -> dict | None:
    tf = m5.tf
    j0 = _bar_at(tf, t1)                      # erste M5-Kerze nach BOS 1
    conf = m5.sl_conf if d < 0 else m5.sh_conf
    px = m5.sl_px if d < 0 else m5.sh_px
    # erster Swing, dessen Extrem-Kerze (Index-k) nach BOS 1 liegt und der bestaetigt ist
    j = j0 + K_SWING
    while j < m5.n and tf["t0"][j] < t_end:
        if conf[j] and (j - K_SWING) >= j0:
            level = px[j]
            # Order aktiv ab Kerze j+1 (Bestaetigung erst mit Schluss von j bekannt)
            i_from = tf["i_end"][j]
            i_to = int(np.searchsorted(s.t, t_end, side="left"))
            if i_from >= i_to:
                return None
            hit = (s.lo[i_from:i_to] <= level) if d < 0 else (s.hi[i_from:i_to] >= level)
            k = np.flatnonzero(hit)
            if not len(k):
                return None
            i_fill = i_from + k[0]
            o = s.op[i_fill]
            fill = min(o, level) if d < 0 else max(o, level)   # Gap -> Eroeffnungskurs
            return {"t_fill": s.t[i_fill], "i_fill": i_fill, "price": fill, "dir": d, "t_bos1": t1}
        j += 1
    return None


def measure(s: Series, trig: dict, pip: float) -> dict:
    """+G/-G zuerst fuer G in G_LIST, dazu MFE/MAE ueber 1 Tag (Pips). Fuell-Minute konservativ."""
    i, p0, d = trig["i_fill"], trig["price"], trig["dir"]
    out = {}
    for g in G_LIST:
        gg = g * pip
        # Stop schon in der Fuell-Minute erreicht?
        adverse = (s.hi[i] >= p0 + gg) if d < 0 else (s.lo[i] <= p0 - gg)
        if adverse:
            res, pnl, amb = "fail", -1.0, True
        else:
            res, pnl, _, amb = outcome(s, i + 1, p0, d, gg, WIN_DAYS[g] * 1440)
        out[f"res_{g}"], out[f"pnl_{g}"], out[f"amb_{g}"] = res, pnl, amb
    end = int(np.searchsorted(s.t, s.t[i] + 86_400_000_000_000, side="right"))
    hi, lo = s.hi[i:end].max(), s.lo[i:end].min()
    out["mfe_pips"] = ((hi - p0) if d > 0 else (p0 - lo)) / pip
    out["mae_pips"] = ((p0 - lo) if d > 0 else (hi - p0)) / pip
    return out
