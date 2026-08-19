"""Market-structure primitives for the CTTNL (mentor-material, chat
2026-08-14) SMC framework: fractal swing points, External Range Liquidity
(ERL) tracking, and a CHoCH/BOS bias state machine. Generic - works on any
OHLC DataFrame (used for both the H4 HTF layer and the M1 LTF layer in
pipeline.py).

Terminology mapping from the mentor's slides to code:
  - "External Range Liquidity" (ERL): the most recent CONFIRMED swing
    high/low that hasn't yet been broken - "das High, welches Liquidität
    rausnimmt, um ein neues Low zu formen, kreiert eine neue Range und
    stellt External Range Liquidity dar."
  - "CHoCH" (Change of Character): the FIRST break of an ERL boundary
    against the prevailing bias - signals a possible reversal.
  - "BOS" (Break of Structure): a SUBSEQUENT break of a new ERL boundary
    in the SAME (already-shifted) direction - confirms the new bias.
  - A cycle ends whenever the current-side ERL is broken (bias flips).

Not implemented here: "Liquidity Blocks" (a discretionary counter-trend-
candle-plus-engulfing pattern) - the source material presents it as a
supplementary POI concept, not a strict requirement of the 3-Phase entry
checklist, and it is the most subjective piece to encode. Everything else
in the checklist (ERL, Inducement, Early Ones, CHoCH/BOS) is implemented.
"""

import numpy as np
import pandas as pd


def detect_fractal_swings(df: pd.DataFrame, k: int = 2) -> pd.DataFrame:
    """A bar at position i is a swing high if its `high` is the max of the
    window [i-k, i+k], a swing low if its `low` is the min of that window -
    standard k-bar fractal (k=2 -> 5-bar fractal). Causal: the fact "bar i
    was a swing point" only becomes knowable once bar i+k has printed, so
    both the boolean flag AND the price are exposed via .shift(k) - a swing
    high confirmed and readable at row i+k carries the price from row i.
    No lookahead: nothing at row j uses information from after row j.

    Adds columns: swing_high_confirmed (bool), swing_high_price (float),
    swing_low_confirmed (bool), swing_low_price (float)."""
    df = df.copy()
    window = 2 * k + 1
    roll_max = df["high"].rolling(window, center=True).max()
    roll_min = df["low"].rolling(window, center=True).min()
    raw_swing_high = df["high"] == roll_max
    raw_swing_low = df["low"] == roll_min

    df["swing_high_confirmed"] = raw_swing_high.shift(k).fillna(False).astype(bool)
    df["swing_high_price"] = df["high"].shift(k)
    df["swing_low_confirmed"] = raw_swing_low.shift(k).fillna(False).astype(bool)
    df["swing_low_price"] = df["low"].shift(k)
    return df


def track_external_range_liquidity(df: pd.DataFrame) -> pd.DataFrame:
    """Requires detect_fractal_swings' output columns. Tracks, bar by bar,
    the most recent confirmed swing high/low as the current ERL boundary
    (erl_high/erl_low) - replaced whenever a newer swing point confirms.
    erl_high_broken/erl_low_broken flag the bar where close first trades
    beyond that boundary (a cycle-ending event per the mentor material)."""
    df = df.copy()
    n = len(df)
    sh_conf = df["swing_high_confirmed"].to_numpy()
    sh_price = df["swing_high_price"].to_numpy()
    sl_conf = df["swing_low_confirmed"].to_numpy()
    sl_price = df["swing_low_price"].to_numpy()

    erl_high = np.full(n, np.nan)
    erl_low = np.full(n, np.nan)
    cur_high, cur_low = np.nan, np.nan
    for i in range(n):
        if sh_conf[i] and not np.isnan(sh_price[i]):
            cur_high = sh_price[i]
        if sl_conf[i] and not np.isnan(sl_price[i]):
            cur_low = sl_price[i]
        erl_high[i] = cur_high
        erl_low[i] = cur_low

    df["erl_high"] = erl_high
    df["erl_low"] = erl_low
    df["erl_high_broken"] = df["close"] > df["erl_high"]
    df["erl_low_broken"] = df["close"] < df["erl_low"]
    return df


def compute_choch_bos_bias(df: pd.DataFrame) -> pd.DataFrame:
    """Requires track_external_range_liquidity's output. Bias state machine:
    starts neutral (0). Each bar where erl_high_broken flips bias from
    non-bullish to bullish is a CHoCH-up; each subsequent erl_high_broken
    while already bullish is a BOS-up (confirmation). Symmetric for
    erl_low_broken/bearish. `bias` is forward-filled (persists until an
    opposite-direction break flips it) - the "current trend context" the
    mentor material calls Phase 1.

    Adds columns: bias (1 bullish / -1 bearish / 0 undetermined-yet),
    is_choch (bool, first break in a new direction), is_bos (bool,
    confirming break while already in that bias)."""
    df = df.copy()
    n = len(df)
    high_broken = df["erl_high_broken"].to_numpy()
    low_broken = df["erl_low_broken"].to_numpy()

    bias = np.zeros(n, dtype=int)
    is_choch = np.zeros(n, dtype=bool)
    is_bos = np.zeros(n, dtype=bool)
    cur_bias = 0
    for i in range(n):
        if high_broken[i] and not low_broken[i]:
            if cur_bias != 1:
                is_choch[i] = True
                cur_bias = 1
            else:
                is_bos[i] = True
        elif low_broken[i] and not high_broken[i]:
            if cur_bias != -1:
                is_choch[i] = True
                cur_bias = -1
            else:
                is_bos[i] = True
        bias[i] = cur_bias

    df["bias"] = bias
    df["is_choch"] = is_choch
    df["is_bos"] = is_bos
    return df


def compute_market_structure(df: pd.DataFrame, k: int = 2) -> pd.DataFrame:
    """Convenience wrapper: fractal swings -> ERL tracking -> CHoCH/BOS bias,
    in one call."""
    df = detect_fractal_swings(df, k=k)
    df = track_external_range_liquidity(df)
    df = compute_choch_bos_bias(df)
    return df
