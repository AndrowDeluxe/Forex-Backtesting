"""Long-only, single-position, fixed-ATR-stop / fixed-R-target Gold (XAUUSD)
trend-pullback strategy.

Built as an ORIGINAL, independent reference point for the publicly stated
concept behind the paid "Smart Gold Hunter" MQL5-Market EA (long-only, real
Stop Loss/Take Profit, no grid, no martingale, controlled risk management) -
see chat for context. That EA is closed-source (compiled .ex5 only, no
.mq5) and was never inspected; nothing here is derived from its code.

Entry: uptrend filter (close above a slow EMA) + pullback-and-resume trigger
(close crosses back above a fast EMA after dipping to/below it) - a
standard, non-repainting trend-continuation setup.

Exit: reuses strategy.backtest.simulate_trades' generic ATR-stop / R-multiple
-target machinery (use_vwap_target=False, take_profit_r set) rather than a
VWAP or session-time exit, matching the "no grid/martingale, real SL/TP"
simplicity the EA advertises. `prev_high`/`prev_low` are set to the signal
bar's own close (not a breakout trigger level, unlike e.g. orb_strategy) so
the stop resolves to a plain entry_price -/+ stop_atr_mult*ATR. `session` is
held constant across the whole series so trades are never force-closed by a
session rollover - the position is only ever closed by its stop or target.
"""

import numpy as np
import pandas as pd

from checklist_strategy.indicators import compute_session_ok, rsi
from gold_trend_pullback_atr.indicators import bollinger_bands, macd
from strategy.indicators import compute_adx


def generate_signal(
    df: pd.DataFrame,
    trend_ema: int = 200,
    fast_ema: int = 20,
    atr_n: int = 14,
    adx_min: float | None = None,
    vol_window: int | None = None,
    vol_quantile: float | None = None,
    rsi_n: int = 14,
    rsi_min: float | None = None,
    rsi_max: float | None = None,
    bb_window: int = 20,
    bb_k: float = 2.0,
    bb_require_not_overbought: bool = False,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    macd_require_bullish: bool = False,
    session_start_hour: float | None = None,
    session_end_hour: float | None = None,
) -> pd.DataFrame:
    """`adx_min` and `vol_window`/`vol_quantile` implement the regime filter
    suggested by the full-sample regime decomposition (trades cluster in
    high-ADX, mid/high-volatility bars) - but computed causally here (a
    trailing rolling ATR quantile, using only bars up to and including the
    signal bar) rather than the full-sample quantile the decomposition used,
    which would leak future data into a live-usable filter.

    The remaining filters (rsi_*, bb_*, macd_*, session_*) implement every
    price/time-based idea from the "Top-Tipps von Tradern" article (see
    chat, 2026-08-13) that this generic listicle attached a concrete,
    testable rule to: Moving Averages (already the ema_trend/ema_fast
    entry itself), RSI, Bollinger Bands, MACD, and "best trading session".
    None of these are validated yet - building them is step one, sweeping/
    IS-OOS-testing them (same discipline as the adx_min/vol regime filter)
    is a separate, later step. All are OFF by default (None/False), so
    existing calls are unaffected.
    """
    df = compute_adx(df, n=atr_n)  # adds atr, plus_di, minus_di, adx

    df["ema_trend"] = df["close"].ewm(span=trend_ema, adjust=False).mean()
    df["ema_fast"] = df["close"].ewm(span=fast_ema, adjust=False).mean()
    df["rsi"] = rsi(df["close"], rsi_n)
    bb = bollinger_bands(df["close"], window=bb_window, k=bb_k)
    df["bb_mid"], df["bb_upper"], df["bb_lower"] = bb["mid"], bb["upper"], bb["lower"]
    m = macd(df["close"], fast=macd_fast, slow=macd_slow, signal=macd_signal)
    df["macd"], df["macd_signal"], df["macd_hist"] = m["macd"], m["signal_line"], m["histogram"]

    uptrend = df["close"] > df["ema_trend"]
    cross_up = (df["close"] > df["ema_fast"]) & (df["close"].shift(1) <= df["ema_fast"].shift(1))
    base_signal = uptrend & cross_up

    if adx_min is not None:
        base_signal &= df["adx"] >= adx_min

    if vol_window is not None and vol_quantile is not None:
        atr_threshold = df["atr"].rolling(vol_window, min_periods=vol_window // 2).quantile(vol_quantile)
        base_signal &= df["atr"] >= atr_threshold

    if rsi_min is not None:
        base_signal &= df["rsi"] >= rsi_min
    if rsi_max is not None:
        base_signal &= df["rsi"] <= rsi_max

    if bb_require_not_overbought:
        # article: "close near the upper band -> market may be overbought" -
        # a long-only entry skips bars already pressed against the upper band.
        base_signal &= df["close"] < df["bb_upper"]

    if macd_require_bullish:
        # article: MACD line crossing above the signal line -> bullish impulse.
        base_signal &= df["macd"] > df["macd_signal"]

    if session_start_hour is not None and session_end_hour is not None:
        session_ok = compute_session_ok(df.index, start_hour=session_start_hour, end_hour=session_end_hour)
        base_signal &= session_ok.to_numpy()

    df["signal"] = np.where(base_signal, 1, 0)

    df["vwap"] = df["close"]  # inert placeholder - use_vwap_target=False
    df["prev_high"] = df["close"]
    df["prev_low"] = df["close"]
    df["session"] = 0  # constant - only the ATR stop or R-multiple target ever closes a trade
    return df


def run_pipeline(df: pd.DataFrame, **kwargs) -> pd.DataFrame:
    return generate_signal(df, **kwargs)
