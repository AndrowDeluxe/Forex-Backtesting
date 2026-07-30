"""Binance market data for the Auction Market Playbook reconstruction.

Unlike the FX side of this repo (Dukascopy, bid-only OHLCV), Binance's own
`/klines` endpoint already reports **taker buy base asset volume** per bar
(index 9 of the raw response) - i.e. how much of that bar's volume was
aggressive buying (taker hit the ask) vs aggressive selling (taker hit the
bid, `volume - taker_buy_volume`). That is real trade-side data, not a
synthetic guess from OHLC shape.

Explicit limitation, disclosed rather than hidden: the source PDF describes
tick-by-tick footprint reading ("big buy/sell prints", "footprint
imbalance"). True tick-level reconstruction would need Binance's
`/aggTrades` endpoint paged 1000 rows at a time - for a liquid pair like
BTCUSDT over a multi-month backtest that's realistically hundreds of
thousands of paginated calls, not practical on the free REST API. Per-candle
taker buy/sell volume is a coarser, but still genuine (not invented),
aggression signal - the best available at this data budget.

Cached to `data_cache_crypto/` (gitignored, parquet), keyed by
(symbol, interval, start, end) - same pattern as `strategy/real_data.py`.
"""

from pathlib import Path

import pandas as pd
import requests

CACHE_DIR = Path(__file__).resolve().parents[1] / "data_cache_crypto"
BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
MAX_LIMIT = 1000  # Binance's per-request cap


def _cache_path(symbol: str, interval: str, start: str, end: str) -> Path:
    return CACHE_DIR / f"{symbol}_{interval}_{start}_{end}.parquet"


def fetch_klines(symbol: str, interval: str, start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    """Real Binance OHLCV + taker buy/sell volume, `start`/`end` as date strings (UTC).

    Columns: open, high, low, close, volume, taker_buy_volume,
    taker_sell_volume, n_trades, delta (= taker_buy - taker_sell, the
    per-bar CVD building block). UTC DatetimeIndex, named `timestamp`.
    """
    path = _cache_path(symbol, interval, start, end)
    if path.exists() and not force_refresh:
        return pd.read_parquet(path)

    start_ms = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    end_ms = int(pd.Timestamp(end, tz="UTC").timestamp() * 1000)

    rows = []
    cursor = start_ms
    while cursor < end_ms:
        resp = requests.get(
            BINANCE_KLINES_URL,
            params={"symbol": symbol, "interval": interval, "startTime": cursor, "endTime": end_ms, "limit": MAX_LIMIT},
            timeout=30,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        rows.extend(batch)
        last_open_time = batch[-1][0]
        if len(batch) < MAX_LIMIT or last_open_time <= cursor:
            break
        cursor = last_open_time + 1

    if not rows:
        raise ValueError(f"No klines returned for {symbol} {interval} {start}..{end}")

    df = pd.DataFrame(
        rows,
        columns=[
            "open_time", "open", "high", "low", "close", "volume", "close_time",
            "quote_volume", "n_trades", "taker_buy_volume", "taker_buy_quote_volume", "ignore",
        ],
    )
    df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df.set_index("timestamp").sort_index()
    df = df.drop_duplicates()

    for col in ("open", "high", "low", "close", "volume", "taker_buy_volume"):
        df[col] = df[col].astype(float)
    df["n_trades"] = df["n_trades"].astype(int)
    df["taker_sell_volume"] = df["volume"] - df["taker_buy_volume"]
    df["delta"] = df["taker_buy_volume"] - df["taker_sell_volume"]

    out = df[["open", "high", "low", "close", "volume", "taker_buy_volume", "taker_sell_volume", "n_trades", "delta"]]

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out.to_parquet(path)
    return out
