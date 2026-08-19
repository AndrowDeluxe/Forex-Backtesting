"""Volume-pressure filter for the mean-reversion fade (chat 2026-08-15):
"Volumen im jeweiligen Marktbereich... echten Kaufs- oder Verkaufsdruck
filtern." Dukascopy only gives TICK volume (price-update count), not
signed trade volume, so directional pressure is approximated the standard
way: weight each bar's volume by where it closed within its own
high-low range (close near the high = buying pressure, near the low =
selling pressure) - a common proxy when true bid/ask-classified volume
isn't available.

Applied to the mean-reversion fade as a "real pressure, not just a wick"
confirmation: before fading a bullish double-BOS short, require genuine
recent SELLING pressure (not just any sweep) at/around the entry zone -
and symmetrically buying pressure before fading a bearish double-BOS long.
"""

import numpy as np
import pandas as pd


def compute_signed_volume_pressure(df: pd.DataFrame) -> pd.Series:
    rng = (df["high"] - df["low"]).replace(0, np.nan)
    close_position = (df["close"] - df["low"]) / rng  # 0 = at the low, 1 = at the high
    pressure = (2 * close_position - 1) * df["volume"]  # ranges roughly -volume..+volume
    return pressure.fillna(0.0)


def compute_rolling_pressure_zscore(df: pd.DataFrame, sum_window: int = 15, zscore_window: int = 100) -> pd.Series:
    """Rolling SUM of signed pressure over `sum_window` bars (a "zone", not
    a single bar - "starke Volumenbereiche"), then a causal rolling
    z-score of that sum against its own trailing `zscore_window`-bar
    history - "how unusual is the pressure building up right now" rather
    than a fixed volume threshold, which would need re-tuning as gold's
    absolute price/volume level drifts over the backtest window."""
    pressure = compute_signed_volume_pressure(df)
    pressure_sum = pressure.rolling(sum_window, min_periods=sum_window // 2).sum()
    roll_mean = pressure_sum.rolling(zscore_window, min_periods=zscore_window // 2).mean()
    roll_std = pressure_sum.rolling(zscore_window, min_periods=zscore_window // 2).std()
    return (pressure_sum - roll_mean) / roll_std.replace(0, np.nan)
