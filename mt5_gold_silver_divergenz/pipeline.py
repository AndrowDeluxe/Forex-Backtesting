"""Backtest replication of the community "Divergenz Gold/Silber" MT5 bot
(long-only Gold, references Silver but never trades it; see
`.../Bots/Neue Bots/3-Divergenz-Gold-Silber/strategy.py` for the live
source). config.py there claims a pre-existing research result (OOS ratio
2.43-2.65 across 3 split methods, 142 trades/10yr H4, top-5-trade
concentration 10.7%) from a script
`backtest-pipeline/idea_r28_intermarket_divergenz.py` that does not exist
anywhere findable on this machine (searched the whole user profile) -- the
"Neue Bots" package is an intentionally research-script-stripped community
release (its own CHANGELOG.md: "Nicht enthalten: interne Test-/Backtest-
Skripte und Forschungsnotizen"). This module is an independent, from-scratch
reconstruction against this repo's own data/process rather than a
verification of that unlocatable prior number -- see knowledge/projects/
mt5-gold-silber-divergenz.md for how the two compare.

Idea: Gold and Silver normally move together. Take each instrument's own
`ret_len`-bar return, subtract (Gold's momentum minus Silver's momentum) ->
a momentum-DIFFERENCE series `d`, not a price spread. When `d` drops below
its own trailing `-band_mult`-sigma band (Gold badly lagging Silver) and then
recovers back above that band (a transition event, not a persistent state),
that's read as a Gold-catches-up long signal -- combined with the usual
EMA(trend_len) trend filter on Gold itself.

Entry, on the last CLOSED XAUUSD bar:
  1. d(t-1) <= band(t-1)  -> Gold was lagging Silver on the PRIOR bar
  2. d(t)   >  band(t)    -> and now recovers back above (the actual
                             transition event, not a standing condition)
  3. close_xau(t) > EMA(trend_len)  -> only in a genuine Gold uptrend

`_ema`/`_atr` reproduce the bot's own formulas verbatim (plain
`ewm(alpha=1/length)` from the first bar, matching `mt5_trend_pullback.
pipeline`'s "Haupt-Bot" style, NOT `mt5_david_v2.pipeline`'s
`min_periods=length` style -- the two live bots' authors used different EMA
seeding conventions and this reconstruction preserves whichever the bot in
question actually runs) rather than `strategy/indicators`'s differently-
seeded Wilder smoothing, for the same reason as the other two bots: backtest
signals should line up with what the live bot would actually have fired.

Exit: reuses `strategy.backtest.simulate_trades`'s generic ATR-stop /
R-multiple-target machinery (`use_vwap_target=False`, `take_profit_r=rr`),
matching the bot's fixed SL/TP-at-entry order. `prev_high`/`prev_low` are set
to the signal bar's own close (shifted by 1, same reason as the other two
pipelines) and `session` is held constant (only stop/target ever exit).

`confirm_len` (optional, off by default -- NOT part of the live bot) is a
research-only plausibility filter added 2026-08-25 during Phase 5
("Kombination mit vorhandenen Bausteinen"): require Silver's OWN
`confirm_len`-bar return to be positive at the signal bar too, i.e. Silver
must itself be genuinely rising, not just "less negative than Gold" --
otherwise the momentum-difference crossing can fire on a bar where both
metals are falling and Gold is merely falling *less*, which looks like
"catching up" in the difference series without Silver actually confirming
upward momentum. Chosen on IS (2016-2022) only, validated on OOS
(2023-2026): see scripts/research_mt5_gold_silver_divergenz_optimization.py
and knowledge/projects/mt5-gold-silber-divergenz.md for the full sweep and
Phase 6 re-validation of the resulting config.
"""

import numpy as np
import pandas as pd

from strategy.indicators import compute_adx

# Defaults match config.py's values exactly.
TREND_LEN = 150
ATR_LEN = 14
ATR_STOP_MULT = 2.0
RR_RATIO = 2.0
RET_LEN = 20
BAND_LOOKBACK = 100
BAND_MULT = 1.5


def _ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


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


def _diff_and_band(
    df_x: pd.DataFrame, df_y: pd.DataFrame, ret_len: int, band_lookback: int, band_mult: float,
) -> tuple[pd.Series, pd.Series]:
    """Momentum difference d(t) and its -band_mult-sigma band, aligned to
    df_x's own bar index (last known df_y close ON OR BEFORE each df_x
    timestamp, never later -- causal, matches the bot's own comment "wie
    beim BTC-Season-Bot")."""
    y_on_x = df_y["close"].reindex(df_x.index, method="ffill")
    ret_x = df_x["close"] / df_x["close"].shift(ret_len) - 1.0
    ret_y = y_on_x / y_on_x.shift(ret_len) - 1.0
    d = ret_x - ret_y

    mean = d.rolling(band_lookback, min_periods=band_lookback).mean()
    std = d.rolling(band_lookback, min_periods=band_lookback).std()
    band = mean - band_mult * std
    return d, band


def generate_signal(
    df_xau: pd.DataFrame,
    df_xag: pd.DataFrame,
    trend_len: int = TREND_LEN,
    atr_len: int = ATR_LEN,
    ret_len: int = RET_LEN,
    band_lookback: int = BAND_LOOKBACK,
    band_mult: float = BAND_MULT,
    confirm_len: int | None = None,
) -> pd.DataFrame:
    df = compute_adx(df_xau.copy(), n=atr_len)  # populates df["adx"] for simulate_trades' per-trade record; df["atr"] overwritten below by the bot-exact one

    d, band = _diff_and_band(df, df_xag, ret_len, band_lookback, band_mult)
    df["d"] = d
    df["band"] = band
    df["ema_trend"] = _ema(df["close"], trend_len)
    df["atr"] = _atr(df, atr_len)

    now_unter = d <= band
    prev_unter = now_unter.shift(1)
    kreuzung = (~now_unter) & prev_unter  # d recovers back above its band -- the actual transition event

    up_trend = df["close"] > df["ema_trend"]

    valid = d.notna() & band.notna() & prev_unter.notna() & df["ema_trend"].notna() & df["atr"].notna() & (df["atr"] > 0)

    long_sig = kreuzung & up_trend & valid

    if confirm_len is not None:
        y_on_x = df_xag["close"].reindex(df_xau.index, method="ffill")
        silver_ret = y_on_x / y_on_x.shift(confirm_len) - 1.0
        confirmed = silver_ret > 0
        long_sig &= confirmed.fillna(False)

    df["signal"] = np.where(long_sig, 1, 0)

    df["vwap"] = df["close"]  # inert placeholder -- use_vwap_target=False
    df["prev_high"] = df["close"].shift(1)  # see module docstring: makes the stop resolve to entry_price - stop_atr_mult*ATR
    df["prev_low"] = df["close"].shift(1)
    df["session"] = 0  # constant -- only the ATR stop or R-multiple target ever closes a trade
    return df


def run_pipeline(
    df_xau: pd.DataFrame,
    df_xag: pd.DataFrame,
    trend_len: int = TREND_LEN,
    atr_len: int = ATR_LEN,
    ret_len: int = RET_LEN,
    band_lookback: int = BAND_LOOKBACK,
    band_mult: float = BAND_MULT,
    confirm_len: int | None = None,
) -> pd.DataFrame:
    return generate_signal(
        df_xau, df_xag, trend_len=trend_len, atr_len=atr_len,
        ret_len=ret_len, band_lookback=band_lookback, band_mult=band_mult,
        confirm_len=confirm_len,
    )
