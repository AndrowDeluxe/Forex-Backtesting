"""Makro-Veto fuer Gold-Einstiege (aus dem Gold-Confirmation-Test, Lock `gold_confirm_v1`).

MACRO-Block = Mittel aus Realzins 10J, USD (DXY), Breakeven 10J, EPU, je als 3-Jahres-Perzentil
0..100 (hoch = bullisch fuer Gold). Wert vom letzten Handelstag VOR dem Einstiegstag.

Regel: kein Long bei MACRO <= 35, kein Short bei MACRO >= 65.
Befund CTNL-Reversal (gesperrte Trades, Ø R):
  Long  IS -0,56 (n 77) | OOS -0,85 (n 34) | Tresor -1,16 (n 5)
  Short IS -1,02 (n 32) | OOS -0,65 (n 35) | Tresor  -    (n 0)
Nicht live geschaltet. Details: knowledge/projects/gold-confirmation-score.md
"""

from __future__ import annotations

import pandas as pd

from fusion_lab.gold_confirm.score import GoldScoreFilter, build

__all__ = ["GoldMacroVetoFilter", "GoldScoreFilter"]

MACRO_PARTS = ["m_real", "m_usd", "m_infl", "m_geo"]


def _side(side) -> int:
    if isinstance(side, str):
        return 1 if side.lower() in ("long", "buy") else -1
    return 1 if side > 0 else -1


class GoldMacroVetoFilter:
    """Schnittstelle wie CotFlowFilter/GoldZinskurvenFilter: direction(day), allows(side, day).
    `side` als 'long'/'short' oder +1/-1. Gilt nur fuer Gold (XAUUSD)."""

    def __init__(self, long_min: float = 65, short_max: float = 35, frame: pd.DataFrame | None = None):
        self.frame = build() if frame is None else frame
        self._f = GoldScoreFilter(long_min, short_max, column="MACRO", frame=self.frame)

    def value(self, day) -> float:
        return self._f.value(day)

    def direction(self, day) -> int:
        return self._f.direction(day)

    def allows(self, side, day) -> bool:
        return self._f.allows(_side(side), day)

    def explain(self, day) -> dict:
        """MACRO-Wert und Einzelteile (0..100) vom Vortag -- fuer Logs/Telegram."""
        day = pd.Timestamp(day).tz_localize(None) if pd.Timestamp(day).tzinfo else pd.Timestamp(day)
        prior = self.frame.loc[: day.normalize() - pd.Timedelta(days=1)]
        if prior.empty:
            return {}
        row = prior.iloc[-1]
        return {"tag": prior.index[-1].date().isoformat(), "MACRO": round(float(row["MACRO"]) * 100, 1),
                **{c: round(float(row[c]) * 100, 1) for c in MACRO_PARTS if c in row and row[c] == row[c]}}
