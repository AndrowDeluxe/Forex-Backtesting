"""Long-only, single-position, fixed-ATR-stop / fixed-R-target Gold (XAUUSD)
M1 momentum-thrust strategy.

Different entry logic from gold_trend_pullback_atr (which failed to beat
buy-and-hold even after 6 filters, see chat 2026-08-13/14) - not another
filter on the same EMA-pullback core, but a different signal family
entirely: momentum continuation off an outsized short-horizon thrust,
measured on M1 bars.

Why M1 data but NOT M1-frequency scalping: a viability check (chat) found
the average M1 bar range (~5bps at current Gold prices) is roughly the same
order of magnitude as realistic round-trip cost (~4-8bps) - naive "trade
every bar" scalping is cost-doomed by construction, independent of signal
quality. This strategy instead uses M1 granularity only for ENTRY TIMING
PRECISION (catching the exact minute a real thrust starts) while sizing
stops/targets in ATR multiples wide enough (several dollars, several times
the single-bar noise) that realistic costs are a small fraction of the
target, and holds for as many bars as it takes to hit that target - not a
fixed short hold.

Entry: `momentum_r` = the ATR-normalized net directional move over the
trailing `lookback_bars` M1 bars (same construction as asian_range_
breakout.filters.attach_pre_window_momentum, adapted from a post-hoc filter
into a standalone entry trigger here). Long-only: fires when momentum_r >=
momentum_r_min, i.e. price already moved several ATRs in a short window -
a real burst, not noise - betting on continuation.

Exit: reuses strategy.backtest.simulate_trades' generic ATR-stop / R-
multiple-target machinery (use_vwap_target=False, take_profit_r set),
`prev_high`/`prev_low` set to the signal bar's own close (stop resolves to
entry_price -/+ stop_atr_mult*ATR, not a breakout trigger level), `session`
held constant so trades are only ever closed by their stop or target.
"""

import numpy as np
import pandas as pd

from gold_m1_momentum_thrust.validation import detect_bb_lower_touch, detect_inducement, detect_nw_support_touch
from strategy.indicators import compute_adx


def generate_signal(
    df: pd.DataFrame,
    lookback_bars: int = 10,
    momentum_r_min: float = 3.0,
    atr_n: int = 30,
) -> pd.DataFrame:
    df = compute_adx(df, n=atr_n)  # adds atr, plus_di, minus_di, adx

    momentum = df["close"] - df["close"].shift(lookback_bars)
    df["momentum_r"] = momentum / df["atr"]

    df["signal"] = np.where(df["momentum_r"] >= momentum_r_min, 1, 0)

    df["vwap"] = df["close"]  # inert placeholder - use_vwap_target=False
    df["prev_high"] = df["close"]
    df["prev_low"] = df["close"]
    df["session"] = 0  # constant - only the ATR stop or R-multiple target ever closes a trade
    return df


def run_pipeline(df: pd.DataFrame, **kwargs) -> pd.DataFrame:
    return generate_signal(df, **kwargs)


def generate_signal_fade(
    df: pd.DataFrame,
    lookback_bars: int = 10,
    momentum_r_min: float = 3.0,
    atr_n: int = 30,
) -> pd.DataFrame:
    """Mirror of generate_signal: FADES the thrust instead of chasing it -
    short after an outsized up-move, long after an outsized down-move.
    Built after generate_signal's continuation bet failed catastrophically
    (Sharpe -5 to -17 across every parameter combo, chat 2026-08-14): a win
    rate that consistently lands near 20-30% against a ~1:1 R:R is itself
    evidence the *opposite* direction wins more often than not on this
    timeframe - this variant tests that directly rather than inferring it."""
    df = compute_adx(df, n=atr_n)

    momentum = df["close"] - df["close"].shift(lookback_bars)
    df["momentum_r"] = momentum / df["atr"]

    df["signal"] = np.where(
        df["momentum_r"] >= momentum_r_min, -1,
        np.where(df["momentum_r"] <= -momentum_r_min, 1, 0),
    )

    df["vwap"] = df["close"]
    df["prev_high"] = df["close"]
    df["prev_low"] = df["close"]
    df["session"] = 0
    return df


def run_pipeline_fade(df: pd.DataFrame, **kwargs) -> pd.DataFrame:
    return generate_signal_fade(df, **kwargs)


def generate_signal_pullback(
    df: pd.DataFrame,
    lookback_bars: int = 15,
    momentum_r_min: float = 3.0,
    post_thrust_window: int = 30,
    pullback_r_min: float = 1.0,
    atr_n: int = 30,
    require_inducement: bool = False,
    inducement_swing_window: int = 20,
    inducement_confirm_bars: int = 5,
    require_nw_support: bool = False,
    nw_h: float = 8.0,
    nw_mult: float = 3.0,
    nw_window: int = 500,
    require_bb_touch: bool = False,
    bb_window: int = 20,
    bb_k: float = 2.0,
    validation_confirm_bars: int = 5,
) -> pd.DataFrame:
    """Long-only alternative to both generate_signal (chase the thrust -
    failed) and generate_signal_fade (short the thrust): stay long-only
    (matching the original "Smart Gold Hunter"-inspired convention this
    whole family of strategies started from, chat 2026-08-13) but time the
    entry off the RETRACEMENT after an up-thrust rather than the thrust
    itself - "buy the dip after the spike", not "buy the breakout".

    Mechanics: `thrust_recent` is True for `post_thrust_window` bars after
    momentum_r last touched >= momentum_r_min (an up-thrust happened
    recently). `pullback_r` is how far, in ATR units, price has since
    pulled back from its rolling `post_thrust_window`-bar high. Entry fires
    the first bar both conditions hold - a thrust happened recently AND
    price has now retraced at least `pullback_r_min` ATRs from the peak it
    reached. Note `peak_since_thrust` is a plain rolling max over
    `post_thrust_window` bars, not strictly gated to start exactly at the
    thrust bar - a deliberate simplification, not a precision claim.

    `require_inducement`/`require_nw_support`/`require_bb_touch` (see
    validation.py, chat 2026-08-14): additional AND-gates requiring a real
    support test (liquidity-sweep-and-reject, Nadaraya-Watson lower band,
    or Bollinger lower band) shortly before entry - built after plain
    momentum/fade/pullback all failed near-identically (~23-26% win rate
    regardless of direction), on the theory that entries timed off a
    genuine rejection whipsaw into their stop less than entries timed off
    the raw thrust/pullback alone. None validated yet - this is the
    building-block step."""
    df = compute_adx(df, n=atr_n)

    momentum = df["close"] - df["close"].shift(lookback_bars)
    df["momentum_r"] = momentum / df["atr"]

    thrust_now = df["momentum_r"] >= momentum_r_min
    thrust_recent = thrust_now.rolling(post_thrust_window, min_periods=1).max().astype(bool)
    peak_since_thrust = df["close"].rolling(post_thrust_window, min_periods=1).max()
    df["pullback_r"] = (peak_since_thrust - df["close"]) / df["atr"]

    base_signal = thrust_recent & (df["pullback_r"] >= pullback_r_min)

    if require_inducement:
        df["inducement_recent"] = detect_inducement(df, swing_window=inducement_swing_window, confirm_bars=inducement_confirm_bars)
        base_signal &= df["inducement_recent"]
    if require_nw_support:
        df["nw_support_recent"] = detect_nw_support_touch(df, h=nw_h, mult=nw_mult, window=nw_window, confirm_bars=validation_confirm_bars)
        base_signal &= df["nw_support_recent"]
    if require_bb_touch:
        df["bb_touch_recent"] = detect_bb_lower_touch(df, bb_window=bb_window, bb_k=bb_k, confirm_bars=validation_confirm_bars)
        base_signal &= df["bb_touch_recent"]

    df["signal"] = np.where(base_signal, 1, 0)

    df["vwap"] = df["close"]
    df["prev_high"] = df["close"]
    df["prev_low"] = df["close"]
    df["session"] = 0
    return df


def run_pipeline_pullback(df: pd.DataFrame, **kwargs) -> pd.DataFrame:
    return generate_signal_pullback(df, **kwargs)


def generate_signal_inducement_structure(
    df: pd.DataFrame,
    swing_window: int = 20,
    confirm_bars: int = 20,
    atr_n: int = 30,
) -> pd.DataFrame:
    """Standalone SMC-style entry - the user's own inducement design (chat
    2026-08-14): "inducement + structure confirmation", NOT inducement as
    an extra filter bolted onto the earlier momentum-thrust+pullback signal
    (that's what require_inducement on generate_signal_pullback did, and
    the user clarified that's not what they meant). This entry drops the
    momentum-thrust premise entirely:

    1. A rolling `swing_window`-bar low/high (causal, shifted 1) define the
       recent structural low/high.
    2. INDUCEMENT: price sweeps below the swing low (low < swing_low) and
       closes back above it the same bar (close > swing_low) - a liquidity
       grab that traps late shorts, classic SMC "stop hunt".
    3. STRUCTURE CONFIRMATION (break of structure): within `confirm_bars`
       bars after that inducement, close breaks back above the swing HIGH
       that existed at the moment of the sweep - a genuine higher-high,
       confirming the downswing structure just broke, not just a wick.

    Entry fires on the first bar structure confirmation happens. Long-only.
    `reference_high` is carried forward via a limited forward-fill from
    each inducement bar's own swing_high value - if a newer inducement
    happens before the old one's window expires, its swing_high takes
    over (most recent sweep wins)."""
    df = compute_adx(df, n=atr_n)

    swing_low = df["low"].rolling(swing_window, min_periods=swing_window).min().shift(1)
    swing_high = df["high"].rolling(swing_window, min_periods=swing_window).max().shift(1)

    induced = (df["low"] < swing_low) & (df["close"] > swing_low)
    df["induced"] = induced

    reference_high = swing_high.where(induced).ffill(limit=confirm_bars)
    df["reference_high"] = reference_high

    base_signal = (df["close"] > reference_high).fillna(False)
    df["signal"] = np.where(base_signal, 1, 0)

    df["vwap"] = df["close"]
    df["prev_high"] = df["close"]
    df["prev_low"] = df["close"]
    df["session"] = 0
    return df


def run_pipeline_inducement_structure(df: pd.DataFrame, **kwargs) -> pd.DataFrame:
    return generate_signal_inducement_structure(df, **kwargs)


def generate_signal_inducement_only(
    df: pd.DataFrame,
    swing_window: int = 20,
    atr_n: int = 30,
) -> pd.DataFrame:
    """Simplest possible inducement entry: fires immediately on the
    liquidity-sweep-and-reject bar itself (see validation.detect_inducement),
    no break-of-structure confirmation wait - a more literal "only trade
    when an inducement has happened" reading than either
    generate_signal_pullback's require_inducement gate (stacked onto a
    separate momentum-thrust+pullback premise) or generate_signal_
    inducement_structure (waits for a subsequent break of structure). Best
    guess pending the user's own reference chart images (chat 2026-08-14) -
    likely to be revised once those arrive."""
    df = compute_adx(df, n=atr_n)

    swing_low = df["low"].rolling(swing_window, min_periods=swing_window).min().shift(1)
    induced = (df["low"] < swing_low) & (df["close"] > swing_low)
    df["induced"] = induced

    df["signal"] = np.where(induced, 1, 0)

    df["vwap"] = df["close"]
    df["prev_high"] = df["close"]
    df["prev_low"] = df["close"]
    df["session"] = 0
    return df


def run_pipeline_inducement_only(df: pd.DataFrame, **kwargs) -> pd.DataFrame:
    return generate_signal_inducement_only(df, **kwargs)
