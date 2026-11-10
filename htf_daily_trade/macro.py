"""Makro-Gates fuer den Daily-Edge (Nutzerauftrag 02.11.2026).

1. Regime nach Angelo (OneNote „Elite 2 / Makro Angelo / Zusammenfassung Regime“):
   US 10y-2y-Spread, 2y und 10y heute gegen vor 20 Handelstagen.
   Spread steigt = Steepener, faellt = Flattener; beide Renditen fallen = Bull, steigen = Bear;
   gegenlaeufig = Twist (kein Regime).
   Bull Flattener = Goldilocks, Bear Steepener = Reflation, Bear Flattener = Inflation,
   Bull Steepener = Deflation.
   Richtung je Markt aus der Risk-Regime-Matrix (Dennis Schwer Consulting, „Risk Regime Matrix“):
   Goldilocks/Reflation: USD short, Gold long, Industrie-Rohstoffe long;
   Inflation: USD long, Gold short, Industrie-Rohstoffe short;
   Deflation: USD long, Gold ohne Angabe, Industrie-Rohstoffe short.
2. G8-Staerke (fusion_lab/g8, kalibrierter SMH-Nachbau, Score = Mittel 1W/1M/3M):
   XXXUSD long nur wenn Score XXX > Score USD; USDJPY spiegelbildlich;
   Gold/Silber long nur wenn USD-Score < 0 (V).
Beide Gates nutzen nur Daten bis zum Vortag des Einstiegs.
"""

from __future__ import annotations

import pandas as pd

from fusion_lab.g8.data import log_values, usd_value_panel
from fusion_lab.g8.model import score

REGIME_DIR = {  # Regime -> Markt -> erlaubte Richtung (None = keine Angabe, beide erlaubt)
    "Goldilocks": {"usd": "short", "gold": "long", "industrie": "long"},
    "Reflation": {"usd": "short", "gold": "long", "industrie": "long"},
    "Inflation": {"usd": "long", "gold": "short", "industrie": "short"},
    "Deflation": {"usd": "long", "gold": None, "industrie": "short"},
}
MARKET_KIND = {  # wie die Matrix-Zeile auf den Markt wirkt
    "EURUSD": ("usd", -1), "GBPUSD": ("usd", -1), "AUDUSD": ("usd", -1), "USDJPY": ("usd", +1),
    "XAUUSD": ("gold", +1), "XAGUSD": ("industrie", +1),
    "NZDUSD": ("usd", -1), "USDCAD": ("usd", +1), "USDCHF": ("usd", +1),  # seit 10.11. (Filter-Matrix)
}
G8_BASE = {"EURUSD": ("EUR", "USD"), "GBPUSD": ("GBP", "USD"), "AUDUSD": ("AUD", "USD"), "USDJPY": ("USD", "JPY"),
           "NZDUSD": ("NZD", "USD"), "USDCAD": ("USD", "CAD"), "USDCHF": ("USD", "CHF")}


def regime_series(lag: int = 20) -> pd.Series:
    """Rohes Zinskurven-Regime -- Logik liegt im Filter-Baustein fusion_lab.filters.zinskurve_regime."""
    from fusion_lab.filters.zinskurve_regime import regime_series as _rs
    return _rs(lag)


def g8_scores() -> pd.DataFrame:
    sc, _ = score(log_values(usd_value_panel("fred")), "xs")
    return sc


class MacroGate:
    def __init__(self):
        self.reg = regime_series()
        self.g8 = g8_scores()

    def _prev(self, s, date):
        i = s.index.searchsorted(pd.Timestamp(date), side="left") - 1
        return None if i < 0 else s.iloc[i]

    def regime(self, date) -> str | None:
        return self._prev(self.reg, date)

    def regime_ok(self, market: str, side: str, date) -> bool:
        r = self.regime(date)
        if r is None or r == "Twist":
            return True
        kind, sgn = MARKET_KIND[market]
        pref = REGIME_DIR[r][kind]
        if pref is None:
            return True
        # Matrix-Richtung des Assets in Markt-Richtung uebersetzen
        want_long_asset = pref == "long"
        market_long = want_long_asset if sgn == +1 else not want_long_asset
        return (side == "long") == market_long

    def g8_ok(self, market: str, side: str, date) -> bool:
        row = self._prev(self.g8, date)
        if row is None or row.isna().any():
            return True
        if market in G8_BASE:
            base, quote = G8_BASE[market]
            stronger = row[base] > row[quote]
            return stronger if side == "long" else not stronger
        usd_weak = row["USD"] < 0
        return usd_weak if side == "long" else not usd_weak

    def ok(self, kind: str, market: str, side: str, date) -> bool:
        if kind == "ohne":
            return True
        if kind == "regime":
            return self.regime_ok(market, side, date)
        if kind == "g8":
            return self.g8_ok(market, side, date)
        if kind == "beide":
            return self.regime_ok(market, side, date) and self.g8_ok(market, side, date)
        if kind == "gegen_regime":  # Kontrolle
            return not self.regime_ok(market, side, date) or self.regime(date) in (None, "Twist")
        raise ValueError(kind)
