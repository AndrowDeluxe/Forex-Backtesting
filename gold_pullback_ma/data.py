"""Daily Gold OHLC, built from the same Dukascopy M15 source as
asian_range_breakout (asian_range_breakout.data.fetch_gold_m15) - real
data, not yfinance. Gold trades ~23h/day with no clean exchange calendar,
so "daily bar" here means calendar-day resample of the NY-local M15 series
(same convention already used repo-wide for daily_close series, e.g.
scripts/research_gold_trend_bias_seasonality.py)."""

from asian_range_breakout.data import fetch_gold_m15


def fetch_gold_daily_ohlc(start: str, end: str):
    """Returns a daily OHLC DataFrame (tz-naive index, NY calendar day),
    resampled from Gold M15. Empty/holiday days are dropped."""
    df = fetch_gold_m15(start, end)
    daily = df.tz_localize(None).resample("D").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}
    )
    return daily.dropna(subset=["open", "high", "low", "close"])
