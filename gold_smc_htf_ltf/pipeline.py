"""HTF (H4) -> LTF (M1) SMC entry pipeline, translating the user's mentor
material (CTTNL, chat 2026-08-14) into a testable signal:

Phase 1 (HTF context, H4): External Range Liquidity (see structure.py) is
swept and rejected ("Early Ones liquidated" + "HTF-Inducement identified")
-> establishes htf_bias (long/short) and htf_target (the opposing ERL
level - "trade from liquidity to liquidity"), valid for `htf_valid_bars`
H4 bars.

Phase 2 (LTF reaction, M1): while htf_bias is active, M1 shows its OWN
sweep-and-reject (the M1-scale Early Ones/Inducement) followed by an M1
CHoCH in the SAME direction ("Sweep & Shift").

Phase 3 (execution): entry fires on the M1 bar the CHoCH confirms. Stop
sits just behind the swept M1 wick extreme (stop_atr_mult adds a small
ATR buffer - "SL hinter dem Punkt, an dem die Early Ones ausgestoppt
wurden"). Target is the HTF opposing liquidity level itself (not an
R-multiple) - implemented by reusing strategy.backtest.simulate_trades'
use_vwap_target mechanism with `vwap` repurposed to hold that literal
price level, so a long exits when close >= htf_target and a short when
close <= htf_target, exactly matching "TP an der nächsten großen
Liquiditätszone."

Bidirectional (long AND short) - the source material is symmetric, unlike
the long-only gold_trend_pullback_atr/gold_m1_momentum_thrust families.

No-lookahead note on the H4->M1 merge: an H4 bar's structure state (bias,
ERL levels) is only genuinely known once that H4 bar has CLOSED - its
index timestamp is its OPEN time, so the H4 frame is shifted forward by
one H4 bar length (4h) before merge_asof'ing onto the M1 index. Fractal
swing confirmation lag (k bars) is already baked in via structure.py's
own shift(k).
"""

import numpy as np
import pandas as pd

from gold_smc_htf_ltf.structure import compute_market_structure
from strategy.indicators import compute_adx

H4_BAR_LENGTH = pd.Timedelta(hours=4)


def _sweep_and_reject(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Early Ones sweep / Inducement: wick beyond the current ERL boundary,
    close back inside. Returns (swept_low, swept_high) boolean Series -
    swept_low is a bullish signal (support swept+rejected), swept_high a
    bearish one."""
    swept_low = (df["low"] < df["erl_low"]) & (df["close"] > df["erl_low"])
    swept_high = (df["high"] > df["erl_high"]) & (df["close"] < df["erl_high"])
    return swept_low, swept_high


def compute_htf_context(h4_df: pd.DataFrame, k: int = 2, htf_valid_bars: int = 12) -> pd.DataFrame:
    """Phase 1. Adds htf_bias (1/-1/0) and htf_target (opposing ERL price
    level, NaN when htf_bias==0) to the H4 frame.

    Fix (chat 2026-08-14, after the first backtest showed 43% of trades
    exiting via "target" but only 11% win rate): htf_target used to stay
    FROZEN at the price captured on the signal bar for the full
    `htf_valid_bars` window, even if price had already reached/passed that
    level in the meantime (an H4 close beyond it - erl_high_broken/
    erl_low_broken - without a fresh opposite-direction swing resetting the
    ERL value). A LATER M1 entry could then find its "target" already a few
    ticks away or behind current price - trivial, near-zero-or-negative
    "wins". Fix: the HTF context now expires IMMEDIATELY once its own
    target level is reached, instead of persisting for the rest of the
    window."""
    h4 = compute_market_structure(h4_df, k=k)
    swept_low, swept_high = _sweep_and_reject(h4)
    signal = np.where(swept_low, 1, np.where(swept_high, -1, 0))

    n = len(h4)
    erl_high = h4["erl_high"].to_numpy()
    erl_low = h4["erl_low"].to_numpy()
    erl_high_broken = h4["erl_high_broken"].to_numpy()
    erl_low_broken = h4["erl_low_broken"].to_numpy()
    htf_bias = np.zeros(n, dtype=int)
    htf_target = np.full(n, np.nan)
    cur_bias, cur_target, remaining = 0, np.nan, 0
    for i in range(n):
        if remaining > 0 and cur_bias != 0:
            target_reached = (cur_bias == 1 and erl_high_broken[i]) or (cur_bias == -1 and erl_low_broken[i])
            if target_reached:
                remaining = 0
                cur_bias = 0
        if signal[i] != 0:
            cur_bias = int(signal[i])
            cur_target = erl_high[i] if cur_bias == 1 else erl_low[i]
            remaining = htf_valid_bars
        if remaining > 0:
            htf_bias[i] = cur_bias
            htf_target[i] = cur_target
            remaining -= 1
        else:
            htf_bias[i] = 0
            htf_target[i] = np.nan
            cur_bias = 0

    h4["htf_bias"] = htf_bias
    h4["htf_target"] = htf_target
    return h4


def run_pipeline(
    h4_df: pd.DataFrame,
    m1_df: pd.DataFrame,
    k_htf: int = 2,
    k_ltf: int = 2,
    htf_valid_bars: int = 12,
    ltf_shift_confirm_bars: int = 10,
    atr_n: int = 30,
    min_target_distance_atr: float = 1.0,
) -> pd.DataFrame:
    h4 = compute_htf_context(h4_df, k=k_htf, htf_valid_bars=htf_valid_bars)

    h4_shifted = h4[["htf_bias", "htf_target"]].copy()
    h4_shifted.index = h4_shifted.index + H4_BAR_LENGTH  # only knowable after the H4 bar closes

    m1 = compute_market_structure(m1_df, k=k_ltf)
    m1 = compute_adx(m1, n=atr_n)  # adds atr, adx (needed by simulate_trades)
    swept_low_ltf, swept_high_ltf = _sweep_and_reject(m1)
    m1["sweep_low_level"] = m1["low"].where(swept_low_ltf).ffill(limit=ltf_shift_confirm_bars)
    m1["sweep_high_level"] = m1["high"].where(swept_high_ltf).ffill(limit=ltf_shift_confirm_bars)
    m1["ltf_sweep_bull_recent"] = swept_low_ltf.rolling(ltf_shift_confirm_bars, min_periods=1).max().astype(bool)
    m1["ltf_sweep_bear_recent"] = swept_high_ltf.rolling(ltf_shift_confirm_bars, min_periods=1).max().astype(bool)

    m1 = m1.sort_index()
    h4_shifted = h4_shifted.sort_index()
    m1.index = m1.index.as_unit("us")  # merge_asof requires matching datetime64 resolution on both sides
    h4_shifted.index = h4_shifted.index.as_unit("us")
    merged = pd.merge_asof(m1, h4_shifted, left_index=True, right_index=True, direction="backward")
    if not merged.index.equals(m1.index):
        merged.index = m1.index  # merge_asof preserves left row order/count; restore the exact DatetimeIndex defensively

    choch_bull = merged["is_choch"] & (merged["bias"] == 1)
    choch_bear = merged["is_choch"] & (merged["bias"] == -1)

    # "no eng. LIQ in target = no A+ Setup" (mentor material): reject entries
    # whose target is already too close (in ATR terms) to be a genuine move,
    # not just a residual sliver left over from a stale/near-reached level.
    target_dist_ok_long = (merged["htf_target"] - merged["close"]) >= min_target_distance_atr * merged["atr"]
    target_dist_ok_short = (merged["close"] - merged["htf_target"]) >= min_target_distance_atr * merged["atr"]

    entry_long = (
        choch_bull & merged["ltf_sweep_bull_recent"] & (merged["htf_bias"] == 1)
        & merged["sweep_low_level"].notna() & merged["htf_target"].notna() & target_dist_ok_long
    )
    entry_short = (
        choch_bear & merged["ltf_sweep_bear_recent"] & (merged["htf_bias"] == -1)
        & merged["sweep_high_level"].notna() & merged["htf_target"].notna() & target_dist_ok_short
    )

    merged["signal"] = np.where(entry_long, 1, np.where(entry_short, -1, 0))
    merged["prev_low"] = merged["sweep_low_level"]
    merged["prev_high"] = merged["sweep_high_level"]
    merged["vwap"] = merged["htf_target"]
    merged["session"] = 0
    return merged
