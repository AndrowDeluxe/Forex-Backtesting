"""Daily OHLC for the multi-asset pullback system (Beluská & Vojtko 2026),
sourced from the same Dukascopy D1 feed as combined_strategy - real data
only. Their paper trades SPY/EEM/IEF/FXE/GLD/DBC; this repo's data stack
only has direct or reasonable proxies for 4 of those 6 (no EEM/IEF
equivalent exists here), so this is an honestly-scoped subset:
  SP500 -> SPY, GOLD -> GLD, OIL -> DBC (narrower: crude only, not a broad
  commodity basket), EURUSD -> FXE. EEM and IEF are dropped, not faked."""

import pandas as pd

from combined_strategy.data import fetch_timeframe

ASSET_KEYS = ["SP500", "GOLD", "OIL", "EURUSD"]


def fetch_daily_ohlc(start: str, end: str) -> dict[str, pd.DataFrame]:
    out = {}
    for key in ASSET_KEYS:
        df = fetch_timeframe(key, "D1", start, end)
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        out[key] = df[["open", "high", "low", "close"]].dropna()
    return out
