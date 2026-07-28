"""Pipeline (H4 -> daily/weekly bias -> signals -> trades -> metrics) and the
three parameter presets: baseline, "V2" (daily EMA(60) trend + H12 rejection),
and "V2-Trail" (V2 + breakeven/chandelier trailing stop).

See the original project's README_Ergebnisse.md for the full derivation and
the honest in-sample/out-of-sample overfitting findings behind these presets.
"""

import pandas as pd

from ema_strategy.backtest import simulate_trades
from ema_strategy.data import attach_adx, attach_htf_bias, resample_ohlc
from ema_strategy.metrics import compute_metrics
from ema_strategy.signals import build_signals

EMA_LENGTH = 50
EMA_SMOOTH = 15

# "V2": simple EMA(60) (no double smoothing) on weekly/daily/H12, H12 trigger
# timeframe instead of H4, SL = ATR(14) x 1.5 instead of extreme + buffer,
# immediate exit on daily bias flip instead of its own trigger-EMA cross. TP
# stays a fixed RR (default 2R).
V2_TRIGGER_RULE = "12h"
V2_PARAMS = dict(
    ema_length=60, ema_smooth=1,
    sl_mode="atr_multiple", atr_multiplier=1.5,
    exit_on_htf_bias_flip=True, htf_bias_col="daily_bias",
    min_rejection_atr=0.0, require_htf_slope=False, invalidation_confirm_bars=1,
)

# "V2-Trail": V2 plus breakeven + chandelier trailing stop. Once a trade is
# `breakeven_trigger_r` in profit, SL moves to breakeven and then trails the
# highest high / lowest low since entry (`trail_atr_mult` x ATR(14)). If
# trend strength (ADX(14) on daily) at entry was above `adx_threshold`, the
# fixed TP is dropped entirely -- the trade then only exits via
# trail/trend-invalidation/time-limit.
#
# Values are the result of a grid search (optimize_v2_trail.py, in-sample);
# recalibrated after a first estimate (2.5x/25/1.0R) underperformed plain V2.
V2_TRAIL_PARAMS = dict(
    V2_PARAMS,
    use_trailing_stop=True, breakeven_trigger_r=1.5, trail_atr_mult=3.0,
    adx_col="daily_adx", adx_threshold=25.0,
)


def run_pipeline(h4: pd.DataFrame, risk_pct=0.01, rr=2.0,
                  ema_length=EMA_LENGTH, ema_smooth=EMA_SMOOTH,
                  daily: pd.DataFrame = None, weekly: pd.DataFrame = None,
                  sl_buffer_atr=0.1, min_rejection_atr=0.0,
                  require_htf_slope=False, invalidation_confirm_bars=1,
                  sl_mode="signal_extreme", atr_multiplier=1.5,
                  exit_on_htf_bias_flip=False, htf_bias_col="daily_bias",
                  use_trailing_stop=False, breakeven_trigger_r=1.0,
                  trail_atr_mult=2.5, adx_col="daily_adx", adx_threshold=25.0):
    """
    daily/weekly: optional, pre-loaded long history (e.g. 15y of daily data)
        so the weekly/daily bias has more context than just the short H4
        window. Falls back to resampling from `h4` if not given.

    `h4` is generically the trigger timeframe (default H4). For a different
    trigger resolution (e.g. H12) simply pass an accordingly resampled
    DataFrame (see resample_ohlc(h4, "12h")).
    """
    if daily is None:
        daily = resample_ohlc(h4, "D")
    if weekly is None:
        weekly = resample_ohlc(daily, "W")

    merged = attach_htf_bias(h4, daily, "daily", ema_length, ema_smooth)
    merged = attach_htf_bias(merged, weekly, "weekly", ema_length, ema_smooth)
    if use_trailing_stop:
        merged = attach_adx(merged, daily, "daily")
    merged = merged.dropna(subset=["daily_bias", "weekly_bias"])

    signals = build_signals(merged, ema_length, ema_smooth,
                             min_rejection_atr=min_rejection_atr,
                             require_htf_slope=require_htf_slope)
    trades, equity = simulate_trades(signals, risk_pct=risk_pct, rr=rr,
                                      sl_buffer_atr=sl_buffer_atr,
                                      invalidation_confirm_bars=invalidation_confirm_bars,
                                      sl_mode=sl_mode, atr_multiplier=atr_multiplier,
                                      exit_on_htf_bias_flip=exit_on_htf_bias_flip,
                                      htf_bias_col=htf_bias_col,
                                      use_trailing_stop=use_trailing_stop,
                                      breakeven_trigger_r=breakeven_trigger_r,
                                      trail_atr_mult=trail_atr_mult,
                                      adx_col=adx_col, adx_threshold=adx_threshold)
    metrics = compute_metrics(trades, equity, price_series=h4["Close"])
    return signals, trades, equity, metrics, daily, weekly
