"""CLS settlement-cutoff squeeze/reversion signal.

Hypothesis (practitioner market-microstructure folklore, NOT an established,
peer-reviewed result the way the ADX-VWAP paper's VWAP-anchoring thesis is):
banks square up CLS funding positions in a daily settlement cutoff window
(default 06:00-07:00 UTC), producing mechanical, non-informational order
flow that displaces price away from its VWAP fair value. As London
liquidity comes online just after the cutoff, price is hypothesised to
partially revert toward that VWAP anchor. Treat this as an empirical
question to test, not a given.

Reuses the paper's VWAP/ADX machinery, swapping the spatial trigger
(previous *session's* extreme) for the cutoff window's own same-day
high/low (`compute_intraday_window_extremes`), and restricting entries to a
post-cutoff entry window instead of the full session.
"""

import pandas as pd

from strategy.indicators import compute_adaptive_theta


def generate_cls_squeeze_signal(
    df: pd.DataFrame,
    entry_start_hour: float,
    entry_end_hour: float,
    theta: float | pd.Series | None = None,
    theta_window_bars: int = 500,
    theta_multiplier: float = 1.0,
    adx_ceiling: float | None = None,
    direction_mode: str = "reversion",
) -> pd.DataFrame:
    """`direction_mode`: "reversion" (default) fades the displacement -
    short at the window high, long at the window low, betting on a return
    to VWAP. "momentum" flips both to bet on continuation instead - the
    window breach is a genuine directional move, not a mechanical
    overshoot. Same trigger/filter conditions either way; only which side
    is long vs. short changes.
    """
    if direction_mode not in ("reversion", "momentum"):
        raise ValueError(f"direction_mode must be 'reversion' or 'momentum', got {direction_mode!r}")

    df = df.copy()
    if theta is None:
        theta = compute_adaptive_theta(df, theta_window_bars, theta_multiplier)
    df["theta"] = theta

    hour = df.index.hour + df.index.minute / 60.0
    in_entry_window = (hour >= entry_start_hour) & (hour < entry_end_hour)

    cond_adx_elevated = df["adx"] > df["adx_mean"]
    cond_adx_decaying = df["delta_adx"] <= 0
    cond_adx_ceiling = df["adx"] < adx_ceiling if adx_ceiling is not None else True

    cond_at_high = df["close"] >= df["window_high"]
    cond_above_vwap = df["deviation"] > df["theta"]

    cond_at_low = df["close"] <= df["window_low"]
    cond_below_vwap = df["deviation"] < -df["theta"]

    at_high_mask = (
        in_entry_window & cond_at_high & cond_above_vwap & cond_adx_elevated & cond_adx_decaying & cond_adx_ceiling
    )
    at_low_mask = (
        in_entry_window & cond_at_low & cond_below_vwap & cond_adx_elevated & cond_adx_decaying & cond_adx_ceiling
    )

    df["signal"] = 0
    if direction_mode == "reversion":
        df.loc[at_high_mask.fillna(False), "signal"] = -1
        df.loc[at_low_mask.fillna(False), "signal"] = 1
    else:
        df.loc[at_high_mask.fillna(False), "signal"] = 1
        df.loc[at_low_mask.fillna(False), "signal"] = -1
    return df


def run_cls_squeeze_pipeline(
    df: pd.DataFrame,
    cutoff_start_hour: float = 6.0,
    cutoff_end_hour: float = 7.0,
    entry_start_hour: float = 7.0,
    entry_end_hour: float = 7.5,
    adx_n: int = 14,
    adx_window: int = 20,
    theta_window_bars: int = 500,
    theta_multiplier: float = 1.0,
    adx_ceiling: float | None = None,
    vwap_reset_hour: int = 0,
    direction_mode: str = "reversion",
) -> pd.DataFrame:
    """`vwap_reset_hour=0`: VWAP accumulates from Asian-session (calendar-day)
    open so it has an established anchor by the time the cutoff window
    starts, rather than resetting mid-window. `direction_mode`: see
    `generate_cls_squeeze_signal`.
    """
    from strategy.indicators import (
        compute_adx,
        compute_intraday_window_extremes,
        compute_regime_filter,
        compute_vwap_and_deviation,
    )

    out = compute_vwap_and_deviation(df, reset_hour=vwap_reset_hour)
    out = compute_intraday_window_extremes(out, cutoff_start_hour, cutoff_end_hour)
    out = compute_adx(out, n=adx_n)
    out = compute_regime_filter(out, adx_window=adx_window)
    out = generate_cls_squeeze_signal(
        out, entry_start_hour, entry_end_hour,
        theta_window_bars=theta_window_bars, theta_multiplier=theta_multiplier,
        adx_ceiling=adx_ceiling, direction_mode=direction_mode,
    )
    # simulate_trades() is signal-agnostic and just reads "prev_high"/
    # "prev_low" as *the* trigger/stop reference level - alias rather than
    # touch that well-tested code for a same-day-window trigger.
    out["prev_high"] = out["window_high"]
    out["prev_low"] = out["window_low"]
    return out
