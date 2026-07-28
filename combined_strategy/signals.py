"""EMA S/R rejection signal (from ema_strategy.signals), plus two optional
confluence filters carried over from the ADX-VWAP paper's theoretical
framework:

- `use_vwap_filter` (Foundation 1, fair-value anchoring): don't take a
  pullback-long that's already stretched far above the session VWAP (or a
  pullback-short far below it) - avoid chasing an overextended move just
  because it also happens to touch the slower daily/weekly EMA.
- `use_session_confluence_filter` (Foundation 2, liquidity nodes): require
  the rejection to occur near a prior-session high or low, not in open air.

Both are entry filters (AND-ed onto the base condition), evaluated
independently and combined, so each can be ablation-tested against the
unfiltered baseline.
"""

import pandas as pd

from ema_strategy.indicators import double_ema
from strategy.indicators import compute_adaptive_theta


def build_signals(
    h4: pd.DataFrame,
    ema_length: int = 50,
    ema_smooth: int = 15,
    use_vwap_filter: bool = False,
    vwap_theta_window_bars: int = 250,
    vwap_theta_multiplier: float = 1.0,
    use_session_confluence_filter: bool = False,
    confluence_atr_mult: float = 1.0,
) -> pd.DataFrame:
    df = h4.copy()
    df["trigger_ema"] = double_ema(df["Close"], ema_length, ema_smooth)

    touched_from_above = (df["Low"] <= df["trigger_ema"]) & (df["Close"] > df["trigger_ema"])
    touched_from_below = (df["High"] >= df["trigger_ema"]) & (df["Close"] < df["trigger_ema"])

    long_cond = (df["weekly_bias"] == 1) & (df["daily_bias"] == 1) & touched_from_above
    short_cond = (df["weekly_bias"] == -1) & (df["daily_bias"] == -1) & touched_from_below

    if use_vwap_filter:
        theta = compute_adaptive_theta(df, vwap_theta_window_bars, vwap_theta_multiplier)
        not_overextended_long = df["deviation"] <= theta
        not_overextended_short = df["deviation"] >= -theta
        long_cond &= not_overextended_long.fillna(False)
        short_cond &= not_overextended_short.fillna(False)

    if use_session_confluence_filter:
        atr = (df["High"] - df["Low"]).rolling(14).mean()
        dist_to_high = (df["Close"] - df["prev_high"]).abs()
        dist_to_low = (df["Close"] - df["prev_low"]).abs()
        near_extreme = (dist_to_high <= confluence_atr_mult * atr) | (dist_to_low <= confluence_atr_mult * atr)
        long_cond &= near_extreme.fillna(False)
        short_cond &= near_extreme.fillna(False)

    df["signal"] = 0
    df.loc[long_cond.fillna(False), "signal"] = 1
    df.loc[short_cond.fillna(False), "signal"] = -1
    return df
