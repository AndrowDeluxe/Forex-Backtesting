"""Gold-Kursdaten fuer den OmniGold-Nachbau, in MT5-Brokerzeit.

Quelle ist dasselbe Dukascopy-M1 wie bei ny_open_orb (`fetch_m1` liefert
New-Yorker Ortszeit, tz-aware). Der Tester-Server laeuft auf EET mit
EU-Sommerzeit (Europe/Athens): damit liegen 99,2 % der 1.424 MT5-Einstiege
2022-2026 in der zugehoerigen M1-Kerze. Ein fester Versatz "NY + 7 h" trifft
nur 92 % -- er liegt in den Wochen zwischen US- und EU-Zeitumstellung
(Maerz, Ende Okt./Anfang Nov.) eine Stunde daneben.
"""

from pathlib import Path

import pandas as pd

from ny_open_orb.data import fetch_m1

BROKER_TZ = "Europe/Athens"
CACHE = Path(__file__).parent / "results" / "gold_m1_broker.parquet"


def load_gold_m1(start: str = "2018-01-01", end: str = "2026-10-16", refresh: bool = False) -> pd.DataFrame:
    """M1-OHLC (Bid) mit tz-naivem Index in Brokerzeit."""
    if CACHE.exists() and not refresh:
        df = pd.read_parquet(CACHE)
    else:
        df = fetch_m1("GOLD", start, end)
        df.index = df.index.tz_convert(BROKER_TZ).tz_localize(None).rename("time")
        df = df[["open", "high", "low", "close"]]
        df = df[~df.index.duplicated()]
        df.to_parquet(CACHE)
    return df.loc[start:end]


if __name__ == "__main__":
    d = load_gold_m1(refresh=True)
    print(d.index.min(), d.index.max(), len(d))
