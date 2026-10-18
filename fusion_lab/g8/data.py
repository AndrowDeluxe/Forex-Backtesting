"""Kursdaten fuer den G8-Waehrungsstaerke-Nachbau (Phase 1, Schritt 4).

Panel = Wert jeder der acht Waehrungen in USD (USD selbst = 1), taeglich.
Zwei Quellen:
  - "fred":  FRED H.10 Noon Buying Rates (wie im Original-Footer "Quellen FRED,
             BIZ"), ab 1999, aber ~1 Woche Nachlauf (Stand 09.10.: bis 02.10.).
  - "duka":  Dukascopy D1 (Bid-Schluss 22:00 UTC) ueber combined_strategy.data,
             tagesaktuell, fuer den laufenden Betrieb.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

CACHE_DIR = Path(__file__).resolve().parents[2] / "data_cache" / "g8"
FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD"]

# Waehrung -> (FRED-Serie, True wenn die Serie "USD je Waehrung" ist, sonst "Waehrung je USD")
FRED_SERIES = {
    "EUR": ("DEXUSEU", True), "GBP": ("DEXUSUK", True), "AUD": ("DEXUSAL", True), "NZD": ("DEXUSNZ", True),
    "JPY": ("DEXJPUS", False), "CHF": ("DEXSZUS", False), "CAD": ("DEXCAUS", False),
}
# Waehrung -> (Dukascopy-Paar, True wenn xxxUSD)
DUKA_PAIRS = {
    "EUR": ("EURUSD", True), "GBP": ("GBPUSD", True), "AUD": ("AUDUSD", True), "NZD": ("NZDUSD", True),
    "JPY": ("USDJPY", False), "CHF": ("USDCHF", False), "CAD": ("USDCAD", False),
}


def fetch_fred(series: str, force_refresh: bool = False) -> pd.Series:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{series}.parquet"
    if path.exists() and not force_refresh:
        return pd.read_parquet(path)[series]
    df = pd.read_csv(FRED_CSV_URL.format(series=series))
    df.columns = ["date", series]
    df["date"] = pd.to_datetime(df["date"])
    df[series] = pd.to_numeric(df[series], errors="coerce")
    s = df.set_index("date")[series].dropna()
    s.to_frame().to_parquet(path)
    return s


def usd_value_panel(source: str = "fred", start: str = "1999-01-01", end: str | None = None,
                    force_refresh: bool = False) -> pd.DataFrame:
    """Wert je Waehrung in USD. Nur Tage, an denen alle sieben Kurse vorliegen
    (FRED kennt US-Feiertage nicht als Handelstag -- diese Tage fallen weg)."""
    cols = {}
    if source == "fred":
        for ccy, (series, usd_per_ccy) in FRED_SERIES.items():
            s = fetch_fred(series, force_refresh)
            cols[ccy] = s if usd_per_ccy else 1.0 / s
    elif source == "duka":
        from combined_strategy.data import fetch_timeframe
        end = end or pd.Timestamp.today().strftime("%Y-%m-%d")
        for ccy, (pair, xxxusd) in DUKA_PAIRS.items():
            c = fetch_timeframe(pair, "D1", start, end)["Close"]
            c.index = c.index.tz_convert(None).normalize()
            cols[ccy] = c if xxxusd else 1.0 / c
    else:
        raise ValueError(source)
    panel = pd.DataFrame(cols).dropna()
    panel.insert(0, "USD", 1.0)
    panel = panel[(panel.index >= pd.Timestamp(start)) & ((end is None) | (panel.index <= pd.Timestamp(end or "2100")))]
    return panel[CURRENCIES]


def log_values(panel: pd.DataFrame) -> pd.DataFrame:
    return np.log(panel)
