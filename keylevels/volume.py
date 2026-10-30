"""Volumen-Varianten fuer den Doppel-BOS-Einstieg (Plan 18.10.2026).

(a) High-Volume-Zone am Level: Fixed Range Volume Profile aus M1-Tick-Volumen
    ueber die letzte H4-Range (letztes bestaetigtes Swing-Hoch bis -Tief, k = 3)
    vor der Beruehrung. HVN, wenn die Preisstufe des Levels (Breite 2 Pips) zu
    den oberen 20 % nach Volumen gehoert oder der POC hoechstens 5 Pips entfernt
    liegt. Liegt das Level ausserhalb der Range: kein HVN.
(b) Druck-Naeherung: gold_smc_htf_ltf/volume.py (Volumen gewichtet nach der
    Schlussposition in der Kerze), M5, Summe 15 / z-Score 100 - Wert der letzten
    GESCHLOSSENEN M5-Kerze vor der Fuellung.
"""

import numpy as np
import pandas as pd

from gold_smc_htf_ltf.structure import detect_fractal_swings
from gold_smc_htf_ltf.volume import compute_rolling_pressure_zscore
from keylevels.events import Series

BIN_PIPS = 2.0
POC_PIPS = 5.0
TOP_SHARE = 0.20
K_H4 = 3


class VolumeContext:
    def __init__(self, s: Series, pip: float):
        self.s, self.pip = s, pip
        h4 = s.tf("H4")
        df = pd.DataFrame({"high": h4["hi"], "low": h4["lo"]})
        sw = detect_fractal_swings(df, k=K_H4)
        # Zeitpunkt, ab dem ein Swing bekannt ist = Schluss der Bestaetigungskerze
        t_known = s.t[h4["i_end"] - 1] + 60_000_000_000
        hi_idx = np.flatnonzero(sw["swing_high_confirmed"].to_numpy())
        lo_idx = np.flatnonzero(sw["swing_low_confirmed"].to_numpy())
        self.hi_known, self.hi_px = t_known[hi_idx], sw["swing_high_price"].to_numpy()[hi_idx]
        self.hi_start = h4["i_start"][hi_idx - K_H4]          # M1-Index der Swing-Kerze
        self.lo_known, self.lo_px = t_known[lo_idx], sw["swing_low_price"].to_numpy()[lo_idx]
        self.lo_start = h4["i_start"][lo_idx - K_H4]
        m5 = s.tf("M5")
        df5 = pd.DataFrame({"high": m5["hi"], "low": m5["lo"], "close": m5["cl"],
                            "volume": np.add.reduceat(s.m1["volume"].to_numpy(), m5["i_start"])})
        self.m5 = m5
        self.z5 = compute_rolling_pressure_zscore(df5).to_numpy()
        self.vol = s.m1["volume"].to_numpy()

    def hvn(self, level: float, t: int) -> bool:
        a = np.searchsorted(self.hi_known, t, side="right") - 1
        b = np.searchsorted(self.lo_known, t, side="right") - 1
        if a < 0 or b < 0:
            return False
        top, bot = self.hi_px[a], self.lo_px[b]
        if not (bot <= level <= top) or top <= bot:
            return False
        i0, i1 = sorted((self.hi_start[a], self.lo_start[b]))
        if i1 <= i0:
            return False
        px = self.s.cl[i0:i1 + 1]
        w = self.vol[i0:i1 + 1]
        step = BIN_PIPS * self.pip
        bins = np.floor((px - bot) / step).astype(int)
        prof = np.bincount(np.clip(bins, 0, None), weights=w)
        if prof.sum() <= 0:
            return False
        lb = int(np.floor((level - bot) / step))
        if lb >= len(prof):
            return False
        poc = bot + (np.argmax(prof) + 0.5) * step
        thr = np.quantile(prof, 1 - TOP_SHARE)
        return bool(prof[lb] >= thr or abs(poc - level) <= POC_PIPS * self.pip)

    def pressure_z(self, i_fill_m1: int) -> float:
        """z der letzten geschlossenen M5-Kerze vor der Fuell-Minute."""
        b = int(np.searchsorted(self.m5["i_end"], i_fill_m1, side="right")) - 1
        # Kerze b ist die letzte, deren Ende <= i_fill_m1 liegt -> vollstaendig geschlossen
        return float(self.z5[b]) if b >= 0 else np.nan
