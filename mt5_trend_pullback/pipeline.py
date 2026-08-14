"""Backtest replication of the community "MT5 Trend+Pullback Bot" (long-only,
Gold/Silver/Platinum H1 + CHFJPY/USDJPY H4; see
`.../Bots/Ideen1/MT5-TrendPullback-Bot/strategy.py` for the live source).

Entry, on the last CLOSED bar (exactly the bot's `check_signal`):
  1. close > EMA(trend_len)                    -> uptrend filter
  2. RSI(rsi_len) crosses up through rsi_oversold -> pullback resumption

`_ema`/`_rsi`/`_atr` reproduce the bot's own formulas verbatim (plain
`ewm(alpha=1/length)` from the first bar) rather than `strategy/indicators`'s
differently-seeded Wilder smoothing (`wilder_smooth` seeds with the mean of
the first `n` values) - a deliberate choice so backtest signals line up with
what the live bot would actually have fired on the same bars, at the cost of
not sharing code with the rest of this repo's indicator layer.

Exit: reuses `strategy.backtest.simulate_trades`'s generic ATR-stop /
R-multiple-target machinery (`use_vwap_target=False`, `take_profit_r=rr`),
matching the bot's real fixed SL/TP-at-entry order (no trailing, no
breakeven - the bot sends SL/TP once and never touches them again).
`prev_high`/`prev_low` are set to the signal bar's own close (not a breakout
trigger level) so the stop resolves to a plain `entry_price - stop_atr_mult *
ATR`, and `session` is held constant so a trade is only ever closed by its
stop or target - never a time-based exit, matching the live bot.
"""

import numpy as np
import pandas as pd

from strategy.indicators import compute_adx

# Defaults match config.py's "neutral, robustness-tested" values (not the
# per-market overfit ones the bot's own config explicitly warns against).
TREND_LEN = 150
RSI_LEN = 14
RSI_OVERSOLD = 35.0
ATR_LEN = 14
ATR_STOP_MULT = 2.0
RR_RATIO = 2.0


def _ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


def _rsi(series: pd.Series, length: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / length, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50.0)


def _atr(df: pd.DataFrame, length: int) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / length, adjust=False).mean()


def generate_signal(
    df: pd.DataFrame,
    trend_len: int = TREND_LEN,
    rsi_len: int = RSI_LEN,
    rsi_oversold: float = RSI_OVERSOLD,
    atr_len: int = ATR_LEN,
    adx_min: float | None = None,
    vol_window: int | None = None,
    vol_quantile: float | None = None,
    session_hours: tuple[int, int] | None = None,
) -> pd.DataFrame:
    """None of `adx_min`/`vol_window`+`vol_quantile`/`session_hours` are part
    of the live bot - all three are optional, off-by-default research-only
    regime filters:
      - `adx_min`: ADX(atr_len) >= adx_min at signal time (trend-strength floor).
      - `vol_window`+`vol_quantile`: ATR >= its own trailing rolling quantile
        (causal - each bar's threshold uses only bars up to and including it,
        same pattern as gold_trend_pullback_atr/pipeline.py's regime filter),
        a volatility floor independent of trend strength.
      - `session_hours`: (start_hour, end_hour) in UTC: only take signals
        whose signal bar closed inside that window (session/liquidity filter,
        same idea as strategy.indicators.filter_session_window elsewhere in
        this repo, applied as a mask here instead of dropping bars outright
        so indicator warmup/continuity is unaffected).
    All are computed causally, so any would be usable live without look-ahead
    if ever adopted."""
    # `adx` is required by strategy.backtest.simulate_trades's per-trade
    # record and, when adx_min is set, gates entries too. Computed first so
    # its own `atr` column gets overwritten below by the bot-exact one.
    df = compute_adx(df, n=atr_len)

    df["ema_trend"] = _ema(df["close"], trend_len)
    df["rsi"] = _rsi(df["close"], rsi_len)
    df["atr"] = _atr(df, atr_len)

    up_trend = df["close"] > df["ema_trend"]
    cross_up = (df["rsi"] > rsi_oversold) & (df["rsi"].shift(1) <= rsi_oversold)
    base_signal = up_trend & cross_up

    if adx_min is not None:
        base_signal &= df["adx"] >= adx_min

    if vol_window is not None and vol_quantile is not None:
        atr_threshold = df["atr"].rolling(vol_window, min_periods=max(vol_window // 2, 1)).quantile(vol_quantile)
        base_signal &= df["atr"] >= atr_threshold

    if session_hours is not None:
        start_h, end_h = session_hours
        hour = df.index.hour
        if start_h < end_h:
            in_session = (hour >= start_h) & (hour < end_h)
        else:  # wraps past midnight UTC (e.g. (22, 6))
            in_session = (hour >= start_h) | (hour < end_h)
        base_signal &= in_session

    df["signal"] = np.where(base_signal, 1, 0)

    df["vwap"] = df["close"]  # inert placeholder - use_vwap_target=False
    # shift(1): simulate_trades reads prev_high/prev_low at entry_i = signal_i + 1,
    # so shifting by 1 here makes that read land on the SIGNAL bar's own close (as
    # intended - see module docstring), not the entry bar's own close. Getting this
    # wrong lets initial_risk collapse toward zero whenever the entry bar's own
    # open-close move happens to nearly cancel stop_atr_mult*ATR, producing
    # nonsensical 50+ R outlier trades once R-multiples are used for position
    # sizing (return_pct-based metrics are unaffected - they don't use prev_low).
    df["prev_high"] = df["close"].shift(1)
    df["prev_low"] = df["close"].shift(1)
    df["session"] = 0  # constant - only the ATR stop or R-multiple target ever closes a trade
    return df


def run_pipeline(
    df: pd.DataFrame,
    trend_len: int = TREND_LEN,
    rsi_len: int = RSI_LEN,
    rsi_oversold: float = RSI_OVERSOLD,
    atr_len: int = ATR_LEN,
    adx_min: float | None = None,
    vol_window: int | None = None,
    vol_quantile: float | None = None,
    session_hours: tuple[int, int] | None = None,
) -> pd.DataFrame:
    return generate_signal(
        df, trend_len=trend_len, rsi_len=rsi_len, rsi_oversold=rsi_oversold,
        atr_len=atr_len, adx_min=adx_min, vol_window=vol_window,
        vol_quantile=vol_quantile, session_hours=session_hours,
    )
