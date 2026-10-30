"""Gold-M1 genau so, wie der MT5-Tester (MetaQuotes-Demo) es im Modell
"1 Minute OHLC" verwendet.

Quelle: `copy_rates_range` ueber das portable Tester-Terminal
(`C:\\Users\\andre\\MT5-Terminals\\Tester-Portable`, MaxBars unbegrenzt),
exportiert nach results/xau_m1_mq.parquet (2018-01-02 bis 2026-10-28,
Brokerzeit). Gegenprobe 2026: 100 % identisch mit den aus Original-Ticks
gebauten Kerzen.
"""

from pathlib import Path

import pandas as pd

M1 = Path(__file__).parent / "results" / "xau_m1_mq.parquet"


def load_m1(start: str | None = None, end: str | None = None) -> pd.DataFrame:
    d = pd.read_parquet(M1)
    return d.loc[start:end]


def bars(m1: pd.DataFrame, tf: str = "15min") -> pd.DataFrame:
    return m1.resample(tf).agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
