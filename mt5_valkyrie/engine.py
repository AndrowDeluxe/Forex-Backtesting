"""Tick-Simulator fuer Valkyrie-Positionen auf dem OHLC-Tickmodell.

Exit-Regel (hergeleitet aus den MT5-Berichten): ab Gewinn >= TRAIL_START x
SL-Abstand zieht der SL bei jedem Tick auf Hoechststand - TRAIL_DIST nach,
sobald das mehr als TRAIL_STEP Verbesserung bringt.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

TRAIL_START = 0.22
TRAIL_DIST = 0.50
TRAIL_STEP = 0.10
EXPIRY = np.timedelta64(int(29.75 * 3600), "s")
MAX_HOLD_TICKS = 4 * 60 * 24 * 60
# Sonder-TPs: fester Trailing-Start in $ und 0,80 $ Abstand (TP 8 nur n=11, unsicher)
TRAIL_BY_TP = {8: (5.5, 0.8), 12: (8.0, 0.8), 22: (20.0, 0.8)}


def trail_params(tp_dist: float, sl_dist: float) -> tuple[float, float]:
    """Trailing-Start (als Anteil des SL-Abstands) und Abstand je TP-Klasse."""
    special = TRAIL_BY_TP.get(int(round(tp_dist)))
    if special is None:
        return TRAIL_START, TRAIL_DIST
    return special[0] / sl_dist, special[1]


@dataclass
class Ticks:
    t: np.ndarray
    bid: np.ndarray
    ask: np.ndarray

    @classmethod
    def from_frame(cls, tk: pd.DataFrame) -> "Ticks":
        return cls(tk.index.to_numpy(), tk["bid"].to_numpy(), tk["ask"].to_numpy())


def fill(tk: Ticks, s: int, level: float, t_set, expiry=EXPIRY):
    """Erster Tick nach t_set, der die Stop-Order ausloest; sonst None."""
    i = int(np.searchsorted(tk.t, np.datetime64(t_set), side="right"))
    j = int(np.searchsorted(tk.t, np.datetime64(t_set) + expiry, side="right"))
    px = tk.ask[i:j] if s > 0 else tk.bid[i:j]
    hit = np.nonzero(px >= level if s > 0 else px <= level)[0]
    return None if not len(hit) else i + int(hit[0])


def manage(tk: Ticks, i0: int, s: int, p_in: float, sl: float, tp: float,
           start: float = TRAIL_START, dist: float = TRAIL_DIST, step: float = TRAIL_STEP):
    """Fuehrt eine Position ab Tick i0; liefert (Austrittstick, Austrittskurs)."""
    arm = start * abs(p_in - sl)
    peak = -np.inf
    end = min(len(tk.t), i0 + MAX_HOLD_TICKS)
    px_all = tk.bid if s > 0 else tk.ask
    for i in range(i0 + 1, end):
        px = px_all[i]
        if (px - sl) * s <= 0:
            return i, sl
        if (px - tp) * s >= 0:
            return i, tp
        fav = (px - p_in) * s
        if fav > peak:
            peak = fav
            if peak >= arm:
                nsl = p_in + s * (peak - dist)
                if (nsl - sl) * s > step:
                    sl = nsl
    return end - 1, px_all[end - 1]
