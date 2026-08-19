"""Mean-Reversion ("catch your breath after a strong trend") strategy - a
single-timeframe signal (tested on both M5 and M15, per the user's
instruction), structurally the mirror image of continuation.py's "double"
entry variant: "im M5 den Bruch zweier Lows unabhängig vom HTF... Entry
ist der Bruch des Highs/Lows welches den BOS der Range gemacht hat" (chat
2026-08-14/15) - but FADED instead of followed, since the premise here is
trend exhaustion, not continuation.

Mechanics:
  1. Detect two consecutive same-direction BOS events on the entry
     timeframe itself (bos_count>=2) - "der Bruch zweier Lows" (or highs).
  2. Fade: after a bullish double-BOS (two up-breaks, bias=1), look to go
     SHORT on a sweep-and-reject of the current erl_high (price attempts a
     third push up, gets rejected - classic exhaustion). Symmetric for a
     bearish double-BOS -> LONG on a sweep-and-reject of erl_low.

HTF context (NOT a directional filter - the user's own framing: "die
Wahrscheinlichkeit für ein M5 Reversal ist höher" when the HTF trend is
already stable/strong, i.e. a probability booster, tested as an optional
gate, not baked in): an externally-supplied HTF trend-strength series
(trend.trend_adx_di's raw ADX value, regardless of direction) can require
ADX >= a threshold before a fade signal is allowed to fire.

Exit: ATR stop + R-multiple target (a modest snap-back target fits mean-
reversion's own logic better than continuation.py's "next external H4
range" - fading a strong trend all the way to the next major structural
level would be an unrealistically large ask against the grain of that
trend). breakeven_trigger_r is swept downstream like every other exit
parameter this session, via BacktestConfig - not hardcoded here.
"""

import numpy as np
import pandas as pd

from gold_smc_htf_ltf.structure import compute_market_structure
from gold_smc_htf_ltf.volume import compute_rolling_pressure_zscore
from strategy.indicators import compute_adx


def _sweep_and_reject(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    swept_low = (df["low"] < df["erl_low"]) & (df["close"] > df["erl_low"])
    swept_high = (df["high"] > df["erl_high"]) & (df["close"] < df["erl_high"])
    return swept_low, swept_high


def _bar_length(index: pd.DatetimeIndex) -> pd.Timedelta:
    diffs = pd.Series(index[1:] - index[:-1])
    return diffs.mode().iloc[0]


def compute_double_bos_count(df: pd.DataFrame) -> pd.Series:
    """How many consecutive same-direction is_bos events have fired since
    the last CHoCH (bias flip) - resets to 0 on every flip, +1 on every
    subsequent is_bos while the bias holds."""
    bias = df["bias"].to_numpy()
    is_bos = df["is_bos"].to_numpy()
    n = len(df)
    count = np.zeros(n, dtype=int)
    cur_bias, cur_count = 0, 0
    for i in range(n):
        if bias[i] != cur_bias:
            cur_bias = bias[i]
            cur_count = 0
        if is_bos[i]:
            cur_count += 1
        count[i] = cur_count
    return pd.Series(count, index=df.index)


def generate_signal(
    ltf_df: pd.DataFrame,
    k: int = 2,
    confirm_bars: int = 20,
    atr_n: int = 30,
    htf_trend_strength: pd.Series | None = None,
    htf_adx_min: float | None = None,
    vol_zscore_min: float | None = None,
    vol_sum_window: int = 15,
    vol_zscore_window: int = 100,
) -> pd.DataFrame:
    """`htf_trend_strength`: an externally-computed HTF ADX Series (see
    trend.trend_adx_di - pass its underlying ADX values, not the
    direction), already merge_asof-aligned onto ltf_df's index by the
    caller (no-lookahead shift is the caller's responsibility, same
    convention as continuation.py). `htf_adx_min` gates on it if given;
    None (default) means the strength filter is off - tested both ways.

    `vol_zscore_min` (chat 2026-08-15, see volume.py): requires genuine
    counter-direction volume PRESSURE at the fade zone, not just any
    sweep - a short fade (after a bullish double-BOS) needs the rolling
    signed-pressure z-score at/around the sweep to be <= -vol_zscore_min
    (real recent selling pressure), a long fade needs it
    >= +vol_zscore_min (real recent buying pressure). None (default)
    means the volume filter is off."""
    ltf = compute_market_structure(ltf_df, k=k)
    ltf = compute_adx(ltf, n=atr_n)
    ltf["bos_count"] = compute_double_bos_count(ltf)
    double_bos_recent = (ltf["bos_count"] >= 2).rolling(confirm_bars, min_periods=1).max().astype(bool)

    swept_low, swept_high = _sweep_and_reject(ltf)

    fade_long = double_bos_recent & (ltf["bias"] == -1) & swept_low
    fade_short = double_bos_recent & (ltf["bias"] == 1) & swept_high

    if htf_adx_min is not None:
        if htf_trend_strength is None:
            raise ValueError("htf_adx_min given but htf_trend_strength is None")
        strong = htf_trend_strength >= htf_adx_min
        fade_long &= strong
        fade_short &= strong

    if vol_zscore_min is not None:
        pressure_z = compute_rolling_pressure_zscore(ltf, sum_window=vol_sum_window, zscore_window=vol_zscore_window)
        ltf["pressure_zscore"] = pressure_z
        fade_long &= pressure_z >= vol_zscore_min
        fade_short &= pressure_z <= -vol_zscore_min

    ltf["signal"] = np.where(fade_long, 1, np.where(fade_short, -1, 0))
    ltf["prev_low"] = ltf["low"].where(swept_low)
    ltf["prev_high"] = ltf["high"].where(swept_high)
    ltf["vwap"] = ltf["close"]  # inert - use_vwap_target=False (ATR/R-multiple TP, see module docstring)
    ltf["session"] = 0
    return ltf


def run_pipeline(
    ltf_df: pd.DataFrame,
    k: int = 2,
    confirm_bars: int = 20,
    atr_n: int = 30,
    htf_df: pd.DataFrame | None = None,
    htf_adx_n: int = 14,
    htf_adx_min: float | None = None,
    vol_zscore_min: float | None = None,
    vol_sum_window: int = 15,
    vol_zscore_window: int = 100,
) -> pd.DataFrame:
    """Convenience wrapper: if `htf_df` + `htf_adx_min` are given, computes
    ADX on htf_df, aligns it onto ltf_df's index (no-lookahead shift by
    htf_df's own bar length), and passes it through to generate_signal as
    the trend-strength gate."""
    htf_trend_strength = None
    if htf_df is not None and htf_adx_min is not None:
        htf = compute_adx(htf_df, n=htf_adx_n)
        shift = _bar_length(htf.index)
        shifted = htf["adx"].copy()
        shifted.index = (shifted.index + shift).as_unit("us")
        shifted = shifted.sort_index()
        left = pd.DataFrame(index=pd.DatetimeIndex(ltf_df.index).as_unit("us"))
        merged = pd.merge_asof(left, shifted.rename("htf_adx"), left_index=True, right_index=True, direction="backward")
        htf_trend_strength = pd.Series(merged["htf_adx"].to_numpy(), index=ltf_df.index)

    return generate_signal(
        ltf_df, k=k, confirm_bars=confirm_bars, atr_n=atr_n, htf_trend_strength=htf_trend_strength, htf_adx_min=htf_adx_min,
        vol_zscore_min=vol_zscore_min, vol_sum_window=vol_sum_window, vol_zscore_window=vol_zscore_window,
    )
