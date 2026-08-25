"""Backtest replication of the community "David-V2" MT5 bot (long AND short,
EURUSD/GBPUSD/USDJPY H1 + Gold H4; see
`.../Bots/Neue Bots/2-David-V2/strategy.py` for the live source).

Entry, on the last CLOSED bar (mirrors the bot's own `check_signal`):
  LONG:  close > EMA(trend_len) + puffer   -> uptrend (outside the neutral
         zone), AND RSI(rsi_len) crosses up through rsi_oversold.
  SHORT: close < EMA(trend_len) - puffer   -> downtrend, AND RSI crosses down
         through (100 - rsi_oversold) (mirrored threshold).
  puffer = ATR(atr_len) * trend_buffer_atr -- a neutral zone around the EMA:
  price within one buffer-width of the EMA is trend-less noise, not traded
  (bot's own `strategy.py` docstring: "ohne Puffer entscheidet reines
  Rauschen ueber die Richtung").

`_ema`/`_rsi`/`_atr` reproduce the bot's own formulas verbatim (`ewm(...,
min_periods=length)`, Wilder-alpha with the same flat-market special-casing
the bot uses for RSI) rather than `strategy/indicators`'s differently-seeded
Wilder smoothing -- same deliberate choice as `mt5_trend_pullback/pipeline.py`,
so backtest signals line up with what the live bot would actually have fired.

Exit: reuses `strategy.backtest.simulate_trades`'s generic ATR-stop /
R-multiple-target machinery (`use_vwap_target=False`, `take_profit_r=rr`),
matching the bot's real fixed SL/TP-at-entry order (no trailing, no
breakeven -- the bot sends SL/TP once and never touches them again in the
*backtest*; the live bot's equity-percent-based SECURE_PROFIT trailing and
daily loss/profit halts are NOT modelled here, see knowledge/projects/
mt5-david-v2-pullback.md for why and what that omission means).
`prev_high`/`prev_low` are set to the signal bar's own close (not a breakout
trigger level) so the stop resolves to a plain `entry_price -/+
stop_atr_mult * ATR`, and `session` is held constant so a trade is only ever
closed by its stop or target -- never a time-based exit, matching the live bot.
"""

import numpy as np
import pandas as pd

from strategy.indicators import compute_adx

# Defaults match config.py's values (long+short, "Davids Original-Setup --
# bewusst als Live-Experiment", not a per-market overfit variant).
TREND_LEN = 200
RSI_LEN = 14
RSI_OVERSOLD = 35.0
TREND_BUFFER_ATR = 0.25
ATR_LEN = 14
ATR_STOP_MULT = 1.5
RR_RATIO = 2.0
TRADE_LONG = True
TRADE_SHORT = True

# Live bot's own strategy.py: an EMA needs roughly 2-3x its span to settle
# (ewm(min_periods=length) returns a value at exactly `length` bars, but one
# still dominated by the seed price) -- EMA_WARMUP_FACTOR=2 there. Matched
# here as an explicit positional mask (not just NaN-masking, which would let
# signals fire from bar `trend_len` onward -- ~half the live bot's own
# warmup window) so backtest signals never fire earlier than the live bot's
# `check_signal` would even attempt to.
EMA_WARMUP_FACTOR = 2


def _ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False, min_periods=length).mean()


def _rsi(close: pd.Series, length: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
    avg_loss = loss.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()

    rs = avg_gain.divide(avg_loss.where(avg_loss > 0))
    out = 100.0 - 100.0 / (1.0 + rs)

    flat = avg_loss.eq(0)
    out = out.mask(flat & avg_gain.gt(0), 100.0)
    out = out.mask(flat & avg_gain.eq(0), 50.0)
    return out


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
    return tr.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()


def generate_signal(
    df: pd.DataFrame,
    trend_len: int = TREND_LEN,
    rsi_len: int = RSI_LEN,
    rsi_oversold: float = RSI_OVERSOLD,
    trend_buffer_atr: float = TREND_BUFFER_ATR,
    atr_len: int = ATR_LEN,
    trade_long: bool = TRADE_LONG,
    trade_short: bool = TRADE_SHORT,
    adx_min: float | None = None,
    vol_window: int | None = None,
    vol_quantile: float | None = None,
) -> pd.DataFrame:
    """`adx_min` is an optional, off-by-default research-only trend-strength
    floor (not part of the live bot), same pattern as
    `mt5_trend_pullback.pipeline.generate_signal`.

    `vol_window`+`vol_quantile`: a causal, NORMALIZED volatility floor --
    ATR as a fraction of price (atr/close, not raw dollar-ATR) must be >= its
    own trailing `vol_window`-bar rolling `vol_quantile` quantile. Normalized
    deliberately: an earlier raw-dollar-ATR version of this idea on the
    Gold/Silber-Divergenz bot turned out to be an artifact of gold's own
    secular price rise (see knowledge/projects/mt5-gold-silber-divergenz.md)
    -- FX majors don't drift that much, but normalizing costs nothing and
    avoids repeating the same mistake."""
    df = compute_adx(df, n=atr_len)  # populates df["adx"] for simulate_trades' per-trade record; df["atr"] overwritten below by the bot-exact one

    df["ema_trend"] = _ema(df["close"], trend_len)
    df["rsi"] = _rsi(df["close"], rsi_len)
    df["atr"] = _atr(df, atr_len)

    puffer = df["atr"] * trend_buffer_atr
    up_trend = df["close"] > df["ema_trend"] + puffer
    down_trend = df["close"] < df["ema_trend"] - puffer

    overbought = 100.0 - rsi_oversold
    rsi_prev = df["rsi"].shift(1)
    crossed_up = (rsi_prev <= rsi_oversold) & (df["rsi"] > rsi_oversold)
    crossed_down = (rsi_prev >= overbought) & (df["rsi"] < overbought)

    valid = df["ema_trend"].notna() & df["rsi"].notna() & rsi_prev.notna() & df["atr"].notna() & (df["atr"] > 0)

    min_bars = max(trend_len * EMA_WARMUP_FACTOR, rsi_len + 1, atr_len + 1) + 2
    too_early = pd.Series(np.arange(len(df)), index=df.index) < min_bars - 1
    valid &= ~too_early

    long_sig = up_trend & crossed_up & valid
    short_sig = down_trend & crossed_down & valid
    if adx_min is not None:
        long_sig &= df["adx"] >= adx_min
        short_sig &= df["adx"] >= adx_min
    if vol_window is not None and vol_quantile is not None:
        atr_pct = df["atr"] / df["close"]
        atr_pct_threshold = atr_pct.rolling(vol_window, min_periods=max(vol_window // 2, 1)).quantile(vol_quantile)
        vol_ok = atr_pct >= atr_pct_threshold
        long_sig &= vol_ok
        short_sig &= vol_ok
    if not trade_long:
        long_sig = long_sig & False
    if not trade_short:
        short_sig = short_sig & False

    df["signal"] = np.where(long_sig, 1, np.where(short_sig, -1, 0))

    df["vwap"] = df["close"]  # inert placeholder -- use_vwap_target=False
    # shift(1): simulate_trades reads prev_high/prev_low at entry_i = signal_i + 1,
    # so shifting by 1 here makes that read land on the SIGNAL bar's own close --
    # see mt5_trend_pullback/pipeline.py's docstring for why getting this wrong
    # produces nonsensical outlier R-multiples.
    df["prev_high"] = df["close"].shift(1)
    df["prev_low"] = df["close"].shift(1)
    df["session"] = 0  # constant -- only the ATR stop or R-multiple target ever closes a trade
    return df


def run_pipeline(
    df: pd.DataFrame,
    trend_len: int = TREND_LEN,
    rsi_len: int = RSI_LEN,
    rsi_oversold: float = RSI_OVERSOLD,
    trend_buffer_atr: float = TREND_BUFFER_ATR,
    atr_len: int = ATR_LEN,
    trade_long: bool = TRADE_LONG,
    trade_short: bool = TRADE_SHORT,
    adx_min: float | None = None,
    vol_window: int | None = None,
    vol_quantile: float | None = None,
) -> pd.DataFrame:
    return generate_signal(
        df, trend_len=trend_len, rsi_len=rsi_len, rsi_oversold=rsi_oversold,
        trend_buffer_atr=trend_buffer_atr, atr_len=atr_len,
        trade_long=trade_long, trade_short=trade_short, adx_min=adx_min,
        vol_window=vol_window, vol_quantile=vol_quantile,
    )
