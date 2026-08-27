"""Post-hoc macro filters for gold_trend_pullback_atr trades - the "Real
interest rates" and "News/Sentiment (COT)" ideas from the "Top-Tipps von
Tradern" article (see chat, 2026-08-13). Applied to an already-simulated
trades DataFrame (dropping a trade here is equivalent to never having
entered it), same pattern and same no-lookahead prior-day-value join as
asian_range_breakout/filters.py - reused directly rather than duplicated,
since it's generic (keys off `entry_time`, which strategy.backtest.
simulate_trades' output also has).

Not validated yet - building these is step one (this file), sweeping/
IS-OOS-testing them (same discipline as the ADX/vol regime filter in
scripts/research_gold_trend_pullback_atr_regime_filter.py) is a later step.

Data sources, both free/no-API-key, both already used elsewhere in this repo:
  - real yield: bond_yield_indicator.fred.fetch_us_real_yield (FRED DFII10)
  - COT sentiment: asian_range_breakout.cot.fetch_cot_gold + wang_sentiment_index
"""

import pandas as pd

from asian_range_breakout.filters import attach_series_level


def attach_real_yield(trades: pd.DataFrame, real_yield_daily: pd.Series) -> pd.DataFrame:
    """Attaches the prior trading day's US 10y REAL yield (percent) as
    `real_yield_prior` - no-lookahead prior-day join (see attach_series_level)."""
    return attach_series_level(trades, real_yield_daily, "real_yield_prior")


def apply_real_yield_filter(
    trades: pd.DataFrame, real_yield_daily: pd.Series, yield_max: float | None = None, yield_min: float | None = None
) -> pd.DataFrame:
    """Drops trades outside [yield_min, yield_max] on the prior day's real
    yield. Article's own rule of thumb: real yields <1% = supportive for
    Gold (favor buying), >2% = headwind (favor avoiding/selling) - i.e. a
    long-only strategy like this one would use yield_max=1.0 or 2.0 to
    require a non-hostile macro backdrop, not to "pick direction" (this
    strategy never shorts)."""
    if trades.empty or (yield_max is None and yield_min is None):
        return trades
    out = attach_real_yield(trades, real_yield_daily).dropna(subset=["real_yield_prior"])
    mask = pd.Series(True, index=out.index)
    if yield_min is not None:
        mask &= out["real_yield_prior"] >= yield_min
    if yield_max is not None:
        mask &= out["real_yield_prior"] <= yield_max
    return out[mask]


def attach_cot_gold_sentiment(trades: pd.DataFrame, sentiment_index: pd.Series) -> pd.DataFrame:
    """Attaches the CFTC COT Wang-sentiment index (see asian_range_breakout.
    cot.fetch_cot_gold + wang_sentiment_index; already publication-lag-shifted
    there, so this is a plain no-lookahead prior-value join) as `cot_si`,
    0=3y low non-commercial net-long positioning, 1=3y high."""
    return attach_series_level(trades, sentiment_index, "cot_si")


def apply_cot_sentiment_filter(
    trades: pd.DataFrame, sentiment_index: pd.Series, si_max: float | None = None, si_min: float | None = None
) -> pd.DataFrame:
    """Drops trades outside [si_min, si_max] on the prior COT report's
    sentiment index. Article frames COT as "large players' positioning
    signals coming shifts" - a long-only strategy might use si_max to avoid
    entering fresh longs when speculators are already crowded at a 3-year
    net-long extreme (classic contrarian-crowding read), or si_min to
    require positioning isn't already at a 3-year bearish extreme. Which
    direction actually helps (if either) is untested - this is the filter
    building block, not a validated rule."""
    if trades.empty or (si_max is None and si_min is None):
        return trades
    out = attach_cot_gold_sentiment(trades, sentiment_index).dropna(subset=["cot_si"])
    mask = pd.Series(True, index=out.index)
    if si_min is not None:
        mask &= out["cot_si"] >= si_min
    if si_max is not None:
        mask &= out["cot_si"] <= si_max
    return out[mask]
