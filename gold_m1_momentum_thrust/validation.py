"""Entry-validation filters for the M1 pullback strategy (chat 2026-08-14,
after plain momentum/fade/pullback all failed near-identically - win rates
~23-26% across every direction hypothesis, pointing at the EXIT/whipsaw
mechanics rather than direction). These don't change exit mechanics; they
gate the entry on evidence that a real support test (not just "price
touched some level") already happened, on the theory that entries timed
off a genuine rejection are less likely to immediately whipsaw into a
tight ATR stop than entries timed off the raw thrust/pullback alone.

Three independent validators, each producing a boolean Series (True =
recently validated, entry allowed):
  - detect_inducement: SMC-style liquidity-sweep + rejection (price wicks
    below a recent swing low, then closes back above it - a "stop hunt"
    that traps late shorts before the real move up).
  - detect_nw_support_touch: price touched/pierced the lower band of a
    Nadaraya-Watson envelope (checklist_strategy.indicators, reused as-is).
  - detect_bb_lower_touch: price touched/pierced the lower Bollinger Band
    (gold_trend_pullback_atr.indicators, reused as-is).

All three are "was there a real support test in the last `confirm_bars`
bars", not just "is price below X right now" - matching how inducement
naturally works (the sweep-and-reject is a specific past event, not a
current price level) and applied the same way to NW/BB for consistency.
"""

import pandas as pd

from checklist_strategy.indicators import nadaraya_watson_envelope
from gold_trend_pullback_atr.indicators import bollinger_bands


def detect_inducement(df: pd.DataFrame, swing_window: int = 20, confirm_bars: int = 5) -> pd.Series:
    """Long-bias inducement: a rolling `swing_window`-bar low (causal,
    shifted 1 so it never includes the current bar) gets swept (low[t] <
    swing_low[t]) and then rejected (close[t] > swing_low[t]) - a stop
    hunt below recent structure. True for `confirm_bars` bars afterward."""
    swing_low = df["low"].rolling(swing_window, min_periods=swing_window).min().shift(1)
    swept_and_rejected = (df["low"] < swing_low) & (df["close"] > swing_low)
    return swept_and_rejected.rolling(confirm_bars, min_periods=1).max().astype(bool)


def detect_nw_support_touch(
    df: pd.DataFrame, h: float = 8.0, mult: float = 3.0, window: int = 500, confirm_bars: int = 5
) -> pd.Series:
    """True for `confirm_bars` bars after price's low touched/pierced the
    Nadaraya-Watson envelope's lower band - a real test of that dynamic
    support, not just "price is currently below the mid line"."""
    nw = nadaraya_watson_envelope(df["close"], h=h, mult=mult, window=window)
    touched = df["low"] <= nw["lower"]
    return touched.rolling(confirm_bars, min_periods=1).max().astype(bool)


def detect_bb_lower_touch(df: pd.DataFrame, bb_window: int = 20, bb_k: float = 2.0, confirm_bars: int = 5) -> pd.Series:
    """True for `confirm_bars` bars after price's low touched/pierced the
    lower Bollinger Band - same "real test, not just a current level"
    construction as detect_nw_support_touch."""
    bb = bollinger_bands(df["close"], window=bb_window, k=bb_k)
    touched = df["low"] <= bb["lower"]
    return touched.rolling(confirm_bars, min_periods=1).max().astype(bool)
