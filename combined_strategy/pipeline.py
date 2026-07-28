"""Pipeline: H4 -> daily/weekly EMA bias + daily ADX (ema_strategy) -> VWAP
and prior-session extremes (strategy, via combined_strategy.indicators) ->
signals (with optional filters) -> trades -> metrics.

Reuses ema_strategy.data.attach_htf_bias/attach_adx unmodified (they only
care about Close/generic merge, so the Title-Case OHLCV convention already
matches) and ema_strategy.metrics.compute_metrics unmodified (strategy-
agnostic given trades+equity).
"""

import pandas as pd

from combined_strategy.backtest import simulate_trades
from combined_strategy.indicators import attach_vwap_and_session_extremes
from combined_strategy.signals import build_signals
from ema_strategy.data import attach_adx, attach_htf_bias
from ema_strategy.metrics import compute_metrics

EMA_LENGTH = 50
EMA_SMOOTH = 15


def run_pipeline(
    h4: pd.DataFrame, daily: pd.DataFrame, weekly: pd.DataFrame,
    risk_pct: float = 0.01, rr: float = 2.0,
    ema_length: int = EMA_LENGTH, ema_smooth: int = EMA_SMOOTH,
    sl_buffer_atr: float = 0.1, invalidation_confirm_bars: int = 1,
    use_vwap_filter: bool = False, vwap_theta_window_bars: int = 250, vwap_theta_multiplier: float = 1.0,
    use_session_confluence_filter: bool = False, confluence_atr_mult: float = 1.0,
    exit_on_adx_exhaustion: bool = False, adx_exhaustion_entry_threshold: float = 25.0,
    adx_exhaustion_confirm_bars: int = 2,
):
    merged = attach_htf_bias(h4, daily, "daily", ema_length, ema_smooth)
    merged = attach_htf_bias(merged, weekly, "weekly", ema_length, ema_smooth)
    merged = attach_adx(merged, daily, "daily")
    merged = attach_vwap_and_session_extremes(merged)
    merged = merged.dropna(subset=["daily_bias", "weekly_bias"])

    signals = build_signals(
        merged, ema_length, ema_smooth,
        use_vwap_filter=use_vwap_filter,
        vwap_theta_window_bars=vwap_theta_window_bars,
        vwap_theta_multiplier=vwap_theta_multiplier,
        use_session_confluence_filter=use_session_confluence_filter,
        confluence_atr_mult=confluence_atr_mult,
    )
    trades, equity = simulate_trades(
        signals, risk_pct=risk_pct, rr=rr, sl_buffer_atr=sl_buffer_atr,
        invalidation_confirm_bars=invalidation_confirm_bars,
        exit_on_adx_exhaustion=exit_on_adx_exhaustion,
        adx_exhaustion_col="daily_adx",
        adx_exhaustion_entry_threshold=adx_exhaustion_entry_threshold,
        adx_exhaustion_confirm_bars=adx_exhaustion_confirm_bars,
    )
    metrics = compute_metrics(trades, equity, price_series=h4["Close"])
    return signals, trades, equity, metrics
