"""Bridges ema_strategy's Title-Case OHLCV convention and strategy's
lowercase convention so both packages' indicator code can be reused as-is
instead of being reimplemented a third time."""

import pandas as pd

from ema_strategy.indicators import adx, double_ema  # noqa: F401 - re-exported for callers
from strategy.indicators import compute_prev_session_extremes, compute_vwap_and_deviation


def attach_vwap_and_session_extremes(df: pd.DataFrame, reset_hour: int = 0) -> pd.DataFrame:
    """Attach session VWAP/deviation (paper Eq. 1-3) and previous-session
    high/low (Sec. 4.3) to a Title-Case H4 OHLCV frame.

    `reset_hour=0` (plain calendar day, UTC) rather than the ADX-VWAP app's
    22h NY-ish convention: this frame spans FX, metals, indices and energy,
    which don't share a single natural "session close" the way FX majors do.
    """
    lower = df.rename(
        columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
    )
    lower = compute_vwap_and_deviation(lower, reset_hour=reset_hour)
    lower = compute_prev_session_extremes(lower)

    out = df.copy()
    out["vwap"] = lower["vwap"]
    out["deviation"] = lower["deviation"]
    out["prev_high"] = lower["prev_high"]
    out["prev_low"] = lower["prev_low"]
    return out
