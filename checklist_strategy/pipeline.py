"""Orchestrates: raw OHLC -> indicators -> checklist state machine -> signal."""

import pandas as pd

from checklist_strategy.indicators import (
    compute_regime_ok,
    nadaraya_watson_envelope,
    rsi_multi_length,
    rsi_with_ma,
)
from checklist_strategy.signals import generate_checklist_signals
from strategy.indicators import compute_atr


def run_checklist_pipeline(
    df: pd.DataFrame,
    nw_h: float = 8.0, nw_mult: float = 3.0, nw_window: int = 500,
    rsi2_min_length: int = 10, rsi2_max_length: int = 20,
    rsi3_length: int = 14, rsi3_ma_length: int = 14,
    atr_period: int = 3,
    confirm1_expiry_bars: int = 8, confirm2_expiry_bars: int = 8,
    use_regime_filter: bool = False,
    regime_adx_threshold: float = 25.0,
    regime_vol_lookback: int = 200,
    regime_require_not_trending: bool = True,
    regime_require_volatile: bool = True,
) -> pd.DataFrame:
    """`use_regime_filter`: gate the final entry trigger on a market-state
    condition (see compute_regime_ok) - layered on top of the 4-indicator
    checklist, not a replacement for any of its stages. The trend half
    (`regime_require_not_trending`) and volatility half
    (`regime_require_volatile`) can be tested individually - the combined
    filter can be too restrictive to sample from at all (see MEMORY).
    """
    out = df.copy()

    env = nadaraya_watson_envelope(out["close"], h=nw_h, mult=nw_mult, window=nw_window)
    out["env_mid"] = env["mid"]
    out["env_upper"] = env["upper"]
    out["env_lower"] = env["lower"]

    out["avg_rsi"] = rsi_multi_length(out["close"], rsi2_min_length, rsi2_max_length)

    rm = rsi_with_ma(out["close"], rsi3_length, rsi3_ma_length)
    out["rsi"] = rm["rsi"]
    out["rsi_ma"] = rm["rsi_ma"]

    out["atr"] = compute_atr(out, n=atr_period)
    out["regime_ok"] = compute_regime_ok(
        out, adx_threshold=regime_adx_threshold, vol_lookback=regime_vol_lookback,
        require_not_trending=regime_require_not_trending, require_volatile=regime_require_volatile,
    )

    out = generate_checklist_signals(
        out, confirm1_expiry_bars=confirm1_expiry_bars, confirm2_expiry_bars=confirm2_expiry_bars,
        require_regime_ok=use_regime_filter,
    )
    return out
