"""Multi-timeframe EMA ribbon, extracted from the user's own Pine Script
indicator ("Custom MTF EMA Ribbon", chat 2026-08-18): four EMAs from
different timeframes plotted together - H4 EMA(50), Daily EMA(50), Weekly
EMA(50), Daily EMA(200) by default (the script's own defaults).

The Pine script itself is pure display (no signal logic) - this module
turns it into a testable "reversal zone" concept for reversal_cascade.py:
a REVERSAL ZONE is where price has stretched far away from the ribbon
(in ATR terms) - the classic EMA-ribbon mean-reversion reading ("too far,
too fast, snaps back"), matching the H4 double-manipulation exhaustion
premise the cascade is built around.

No-lookahead: each higher-timeframe EMA is only knowable once that bar has
closed, so every series is shifted forward by its own bar length before
being merge_asof'd (backward) onto the H4 index - same convention as
every other HTF->LTF alignment in this package.
"""

import pandas as pd

from strategy.indicators import compute_atr


def _bar_length(index: pd.DatetimeIndex) -> pd.Timedelta:
    diffs = pd.Series(index[1:] - index[:-1])
    return diffs.mode().iloc[0]


def _ema_on_h4(h4_index: pd.DatetimeIndex, df: pd.DataFrame, length: int) -> pd.Series:
    ema = df["close"].ewm(span=length, adjust=False).mean()
    shifted = ema.copy()
    shifted.index = (shifted.index + _bar_length(df.index)).as_unit("us")
    shifted = shifted.sort_index()
    left = pd.DataFrame(index=pd.DatetimeIndex(h4_index).as_unit("us"))
    merged = pd.merge_asof(left, shifted.rename("ema"), left_index=True, right_index=True, direction="backward")
    return pd.Series(merged["ema"].to_numpy(), index=h4_index)


def compute_ribbon(
    h4_df: pd.DataFrame,
    d1_df: pd.DataFrame,
    w1_df: pd.DataFrame,
    len_h4: int = 50,
    len_d1_fast: int = 50,
    len_d1_slow: int = 200,
    len_w1: int = 50,
    atr_n: int = 14,
) -> pd.DataFrame:
    """Returns h4_df with added columns: ema_h4, ema_d1_fast, ema_d1_slow,
    ema_w1, ribbon_mean (average of the four), ribbon_extension_atr (how
    many ATRs `close` sits above/below ribbon_mean, signed)."""
    df = h4_df.copy()
    df["ema_h4"] = df["close"].ewm(span=len_h4, adjust=False).mean()
    df["ema_d1_fast"] = _ema_on_h4(df.index, d1_df, len_d1_fast)
    df["ema_d1_slow"] = _ema_on_h4(df.index, d1_df, len_d1_slow)
    df["ema_w1"] = _ema_on_h4(df.index, w1_df, len_w1)

    df["ribbon_mean"] = df[["ema_h4", "ema_d1_fast", "ema_d1_slow", "ema_w1"]].mean(axis=1)
    atr = compute_atr(df, n=atr_n)
    df["ribbon_extension_atr"] = (df["close"] - df["ribbon_mean"]) / atr
    return df


def detect_ribbon_reversal_zone(df: pd.DataFrame, extension_atr_min: float = 3.0) -> tuple[pd.Series, pd.Series]:
    """Requires compute_ribbon's output. Returns (stretched_up,
    stretched_down): price sits >= extension_atr_min ATRs above/below the
    ribbon mean - a candidate exhaustion/reversal zone in that direction."""
    stretched_up = df["ribbon_extension_atr"] >= extension_atr_min
    stretched_down = df["ribbon_extension_atr"] <= -extension_atr_min
    return stretched_up, stretched_down
