"""Weekly Gold vs. Bitcoin data for the Vojtko & Dujava (2026) dual-momentum
rotation - real data only: Gold from the same Dukascopy XAUUSD daily feed
used throughout this repo (combined_strategy.data), Bitcoin from the same
Binance BTCUSDT daily feed already used by triple_ma_strategy/
auction_playbook. This is a disclosed deviation from the paper's data
(GLD/IBIT ETF prices) - those aren't in this repo's data stack, so gold and
Bitcoin are represented by their own spot prices instead."""

import pandas as pd

from auction_playbook.data import fetch_klines
from combined_strategy.data import fetch_timeframe


def fetch_weekly_gold_btc(start: str, end: str) -> pd.DataFrame:
    """Wednesday-close weekly series (matches the paper's rebalancing day)."""
    gold_d1 = fetch_timeframe("GOLD", "D1", start, end)  # combined_strategy capitalizes OHLC columns
    btc_d1 = fetch_klines("BTCUSDT", "1d", start, end)  # auction_playbook keeps them lowercase

    daily = pd.DataFrame({"gold": gold_d1["Close"], "btc": btc_d1["close"]}).dropna()
    weekly = daily.resample("W-WED").last().dropna()
    return weekly


def fetch_daily_ohlc_gold_btc(start: str, end: str) -> dict[str, pd.DataFrame]:
    """Full daily OHLC (lowercase columns, for strategy.indicators.compute_atr)
    - needed for the ATR-based stop-loss / prop-firm-risk simulation, as
    opposed to fetch_weekly_gold_btc's close-only weekly series."""
    gold_d1 = fetch_timeframe("GOLD", "D1", start, end)
    btc_d1 = fetch_klines("BTCUSDT", "1d", start, end)

    gold = gold_d1.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close"})[["open", "high", "low", "close"]]
    btc = btc_d1[["open", "high", "low", "close"]]
    return {"gold": gold.dropna(), "btc": btc.dropna()}
