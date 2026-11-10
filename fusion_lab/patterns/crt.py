"""Candle Range Theory (CRT) -- wiederverwendbarer Muster-Baustein.

Quelle: Tim (Elite Coaching, Call „OC CRT“), [[tim-oc-crt-call]]. Getestet am 10.11.2026 (Sperre
`tim_crt`): als Einstieg ohne Edge, die Gruppe „Early Ones geholt“ wirkt nur ueber die weitere
Stopweite. Als Baustein fuer andere Kontexte festgehalten (Nutzerentscheid 10.11.), z. B. als
Einstiegs-Timing an einem Makro-/HTF-Level; neue Einsaetze zaehlen als Varianten.

Definitionen:
  CRT short  C2.high > C1.high, C1.low < C2.close < C1.high, C2.low >= C1.low.  long spiegelbildlich.
  Bruch      C2 sweept eine Seite und schliesst jenseits von C1 (Kontrollgruppe).
  Stop = Sweep-Extrem von C2, Ziel = anderes Extrem von C1, Einstieg = Schluss C2.
  grp  „Early Ones“ = juengstes bestaetigtes Fractal-Swing (n/n) der `lookback` Kerzen vor C1
       jenseits von C1: geholt / fehlt / kein.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SWING_N, SWING_LOOKBACK = 2, 20


def resample_server(m15: pd.DataFrame, tf: str) -> pd.DataFrame:
    """M15 (UTC) zu H1/H4/D1 an der Broker-Serverzeit (New York + 7 h)."""
    if tf == "M15":
        return m15
    rule = {"H1": "1h", "H4": "4h", "D1": "1D"}[tf]
    srv = m15.tz_convert("America/New_York")
    srv.index = srv.index.tz_localize(None) + pd.Timedelta(hours=7)
    out = srv.resample(rule).agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()
    out.index = (out.index - pd.Timedelta(hours=7)).tz_localize("America/New_York", ambiguous="NaT",
                                                                    nonexistent="shift_forward").tz_convert("UTC")
    return out[out.index.notna()]


def swings(h: np.ndarray, l: np.ndarray, n: int = SWING_N) -> tuple[np.ndarray, np.ndarray]:
    """Fractal-Hoch/-Tief an Kerze i (n links/rechts); bekannt erst ab Kerze i+n."""
    sh = np.zeros(len(h), bool)
    sl = np.zeros(len(h), bool)
    for i in range(n, len(h) - n):
        win_h, win_l = h[i - n:i + n + 1], l[i - n:i + n + 1]
        sh[i] = h[i] == win_h.max() and (win_h == h[i]).sum() == 1
        sl[i] = l[i] == win_l.min() and (win_l == l[i]).sum() == 1
    return sh, sl


def early_level(i0: int, side: str, h, l, sh, sl, n: int = SWING_N, lookback: int = SWING_LOOKBACK):
    """Juengstes vor C1 bestaetigtes Swing-Extrem jenseits von C1 (short: ueber C1.high)."""
    lo = max(0, i0 - lookback)
    for j in range(i0 - n, lo - 1, -1):
        if side == "short" and sh[j] and h[j] > h[i0]:
            return h[j]
        if side == "long" and sl[j] and l[j] < l[i0]:
            return l[j]
    return None


def detect(x: pd.DataFrame) -> pd.DataFrame:
    """Alle CRT- und Bruch-Kerzen; i1 = Position von C2 in x."""
    h, l, c = (x[k].to_numpy() for k in ("High", "Low", "Close"))
    sh, sl = swings(h, l)
    rows = []
    for i1 in range(1, len(c) - 1):
        i0 = i1 - 1
        up, dn = h[i1] > h[i0], l[i1] < l[i0]
        if up == dn:
            continue
        side = "short" if up else "long"
        inside = l[i0] < c[i1] < h[i0]
        broke = c[i1] > h[i0] if up else c[i1] < l[i0]
        if not (inside or broke):
            continue
        lvl = early_level(i0, side, h, l, sh, sl)
        if lvl is None:
            grp = "kein"
        elif (h[i1] > lvl) if up else (l[i1] < lvl):
            grp = "geholt"
        else:
            grp = "fehlt"
        rows.append({"t": x.index[i1], "i1": i1, "side": side, "typ": "CRT" if inside else "Bruch",
                     "grp": grp, "entry": c[i1], "stop": h[i1] if up else l[i1],
                     "target": l[i0] if up else h[i0]})
    return pd.DataFrame(rows)
