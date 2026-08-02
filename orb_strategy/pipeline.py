"""Opening Range Breakout (ORB), per Holmberg, Loennbark & Lundstroem (2013)
-- see app_pages/orb_writeup.py for the source write-up.

Each day's open anchors two thresholds, upper/lower = open +/- atr_mult x
(prior day's ATR) -- the prior day's, not today's, since today's own ATR
isn't known yet at the open (no lookahead). The first bar within a day
whose high/low crosses a threshold fires a long/short signal; at most one
entry per day (classic ORB), matching the paper's "one position per day"
framing. A bar that crosses both thresholds at once is ambiguous with only
OHLC bars (no tick data) and is skipped, not forced into a direction.

Reuses strategy/backtest.py::simulate_trades unmodified via the same
prev_high/prev_low-aliasing pattern already used by cls_squeeze.py and
cls_advanced.py -- here aliased to mean the ORB threshold level itself
(not a prior session's extreme), so the stop lands `stop_atr_mult` ATRs
beyond the threshold that triggered entry. use_vwap_target=False is
required (ORB has no VWAP target notion); the exit is the stop or the
session (calendar day) rollover at day's close -- classic ORB "ride it to
the close" behaviour, no fixed R:R/breakeven mechanics like
checklist_strategy.

Two separate ATRs are computed on purpose: `day_atr` (from resampled
DAILY bars, prior day's value only - no lookahead) calibrates the ORB
threshold itself, matching the paper's own daily-bar methodology. `atr`
(computed directly on the M15 bars) is what the generic engine uses to
size the STOP - an earlier version reused day_atr for both, which made
the stop roughly a full day's range wide and meant it essentially never
triggered (>99% of trades rode to session_end regardless of what happened
intraday). `vol_regime` labels each day "expansion" (day_atr above its
own rolling median) or "contraction" (below) - the paper's own
Contraction-Expansion framing, for splitting results by day-level
volatility regime rather than only the bar-level ADX/ATR-tercile split in
strategy.metrics.regime_decomposition.
"""

import numpy as np
import pandas as pd

from strategy.indicators import compute_adx, compute_atr


def compute_orb_frame(
    df: pd.DataFrame, atr_n: int = 14, atr_mult: float = 1.0, vol_regime_lookback: int = 60,
    volume_avg_n: int = 20,
) -> pd.DataFrame:
    out = df.copy()
    out["session"] = out.index.normalize()

    if "volume" in out.columns:
        # Shifted by 1 so the breakout bar's own volume never feeds into its
        # own baseline (no lookahead) - a simple N-bar rolling average, not
        # time-of-day-matched, so this is a blunt "busier than recent bars"
        # measure, not a precise same-time-of-day seasonal baseline.
        out["volume_avg"] = out["volume"].rolling(volume_avg_n, min_periods=volume_avg_n // 2).mean().shift(1)
        out["volume_ratio"] = out["volume"] / out["volume_avg"]

    daily = out.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    daily_atr = compute_atr(daily, n=atr_n).shift(1)  # prior day's ATR only - threshold calibration
    daily_atr_median = daily_atr.rolling(vol_regime_lookback, min_periods=vol_regime_lookback // 2).median()
    vol_regime = pd.Series(
        np.where(daily_atr > daily_atr_median, "expansion", "contraction"),
        index=daily_atr.index, dtype=object,
    )
    vol_regime[daily_atr.isna() | daily_atr_median.isna()] = None

    out["day_open"] = daily["open"].reindex(out["session"]).to_numpy()
    out["day_atr"] = daily_atr.reindex(out["session"]).to_numpy()
    out["vol_regime"] = vol_regime.reindex(out["session"]).to_numpy()

    out["orb_upper"] = out["day_open"] + atr_mult * out["day_atr"]
    out["orb_lower"] = out["day_open"] - atr_mult * out["day_atr"]

    out["atr"] = compute_atr(out, n=atr_n)  # M15-scale - sizes the STOP, not the threshold
    out["adx"] = compute_adx(out)["adx"]
    return out


def generate_orb_signal(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    high, low = out["high"].to_numpy(), out["low"].to_numpy()
    upper, lower = out["orb_upper"].to_numpy(), out["orb_lower"].to_numpy()
    session_codes = pd.factorize(out["session"].to_numpy())[0]

    n = len(out)
    signal = np.zeros(n, dtype=int)
    fired_session = -1
    for i in range(n):
        if np.isnan(upper[i]) or np.isnan(lower[i]):
            continue
        if session_codes[i] == fired_session:
            continue
        broke_up = high[i] >= upper[i]
        broke_down = low[i] <= lower[i]
        if broke_up and not broke_down:
            signal[i] = 1
            fired_session = session_codes[i]
        elif broke_down and not broke_up:
            signal[i] = -1
            fired_session = session_codes[i]

    out["signal"] = signal
    out["prev_high"] = out["orb_upper"]
    out["prev_low"] = out["orb_lower"]
    out["vwap"] = out["close"]  # inert placeholder - use_vwap_target=False
    return out


def apply_orb_filters(
    df: pd.DataFrame, long_only: bool = False, adx_min: float | None = None,
    exclude_weekday: str | None = None, volume_min_ratio: float | None = None,
) -> pd.DataFrame:
    """Post-hoc entry filters, applied to an already-signaled frame (from
    generate_orb_signal). Deliberately does NOT re-trigger a long entry on a
    day whose only breakout was a short (or vice versa) - a filtered-out
    signal simply means no trade that day, matching what a trader who
    ignores short/low-ADX setups would actually see.

    `long_only`: drop short signals - the Nasdaq deep-dive found the ORB
    edge concentrated almost entirely on the long side (short ~breakeven,
    PF 1.05 vs long's 1.76), consistent with this being partly a trend/beta
    effect on a structurally rising asset rather than a symmetric breakout
    edge.
    `adx_min`: drop signals where ADX at the breakout bar is below this -
    the deep-dive's regime_decomposition found the strongest buckets were
    ADX>=25 (PF 1.5-1.6) vs. ADX<25 being flat-to-losing (PF 0.45), a
    bigger effect than the volatility-tercile axis.
    `exclude_weekday`: drop signals whose bar falls on this weekday (e.g.
    "Thursday") - found by ranking weekdays on the In-Sample half
    (2016-2021) and confirming the weakest one stayed a net loser on the
    untouched Out-of-Sample half (2021-2026). Deliberately per-asset, not
    a shared constant: Nasdaq's weakest day is Thursday, SP500's is Monday
    - a shared "one filter fits all assets" search was abandoned after the
    combined full-period view turned out to obscure this (see chat/MEMORY).
    `volume_min_ratio`: drop signals where the breakout bar's volume is
    below this multiple of its own trailing 20-bar average (`volume_ratio`
    column) - an economically-motivated confirmation (a genuine breakout
    should draw above-average participation, not just drift through on
    thin volume), not another arbitrary numeric sweep. Requires a `volume`
    column in the input data.
    """
    out = df.copy()
    if long_only:
        out.loc[out["signal"] == -1, "signal"] = 0
    if adx_min is not None:
        out.loc[out["adx"] < adx_min, "signal"] = 0
    if exclude_weekday is not None:
        out.loc[out.index.day_name() == exclude_weekday, "signal"] = 0
    if volume_min_ratio is not None:
        out.loc[out["volume_ratio"] < volume_min_ratio, "signal"] = 0
    return out


def run_orb_pipeline(
    df: pd.DataFrame, atr_n: int = 14, atr_mult: float = 1.0,
    long_only: bool = False, adx_min: float | None = None,
    exclude_weekday: str | None = None, volume_min_ratio: float | None = None,
) -> pd.DataFrame:
    out = compute_orb_frame(df, atr_n=atr_n, atr_mult=atr_mult)
    out = generate_orb_signal(out)
    out = apply_orb_filters(
        out, long_only=long_only, adx_min=adx_min, exclude_weekday=exclude_weekday,
        volume_min_ratio=volume_min_ratio,
    )
    return out


def attach_vol_regime(trades: pd.DataFrame, signaled: pd.DataFrame) -> pd.DataFrame:
    """simulate_trades() only carries a fixed set of columns into its output
    (see strategy/backtest.py) - this attaches the day-level `vol_regime`
    label back onto each trade by looking up its entry day's session."""
    if trades.empty:
        return trades.assign(vol_regime=pd.Series(dtype=object))
    day_regime = signaled.groupby("session")["vol_regime"].first()
    out = trades.copy()
    out["vol_regime"] = day_regime.reindex(out["entry_time"].dt.normalize()).to_numpy()
    return out
