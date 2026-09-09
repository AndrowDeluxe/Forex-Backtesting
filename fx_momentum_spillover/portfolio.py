"""Monthly cross-sectional portfolio engine: turns a signal (raw individual-
momentum score, or the spillover model's P(up)-0.5) into a vol-targeted
daily return series. Own, simpler engine - NOT adapted from
ou_paper_backtest (event-driven daily engine over US equities, a poor
architectural fit for a monthly cross-sectional FX rebalance, see this
session's plan for why). Mirrors the paper's stated construction: long/
short by sign of the signal, inverse-realized-vol position sizing per
pair, the whole portfolio then scaled to a 10% target annualized vol on a
rolling 1-year window, 1-day execution lag, bps transaction costs on
turnover.

Bug found + fixed 2026-09-09 while running scripts/research_fx_momentum_
spillover.py: an EARLIER version sized each pair as an un-normalized
sign(signal)/vol (typical magnitude 10-40, unbounded as vol -> small) and
combined pairs via a plain .mean() for returns but .sum() for turnover -
that asymmetry let turnover (and therefore cost) reach a completely
different order of magnitude than the return series it was being
subtracted from, producing single-day net returns past -300% and a
"volatility" that grew explosively with cost_bps instead of just being a
drag. Fixed by properly NORMALIZING weights so gross exposure
(sum of |weight| across pairs) is always exactly 1 at every rebalance -
standard risk-parity-by-inverse-vol construction - so both the return
combination (a proper weighted sum) and the turnover calculation operate
on the same well-bounded scale."""

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def realized_vol(closes: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """Rolling annualized realized vol of daily simple returns per pair."""
    ret = closes.pct_change()
    return ret.rolling(window).std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)


def daily_weights_from_signal(
    signal_at_rebalance: pd.DataFrame, closes: pd.DataFrame, vol_window: int = 20
) -> pd.DataFrame:
    """signal_at_rebalance: DataFrame (rebalance_dates x pair) - sign of
    this determines long/short, magnitude is ignored (only used for the
    long/short call, matching the paper: "if this average exceeds 0.5,
    long; else short" - a directional call, not a conviction-weighted one).

    Returns a daily (date x pair) weight matrix: sign(signal)/realized_vol,
    NORMALIZED at each rebalance date so gross exposure (sum of |weight|
    across the 7 pairs) is exactly 1 - standard risk-parity-by-inverse-vol,
    and what keeps turnover on a sane, bounded scale (see module docstring
    for the bug this fixes). Held constant from the day AFTER each
    rebalance date through the day OF the next rebalance date (that
    offset-by-one-day fill IS the paper's 1-day execution lag - the return
    achieved on day dt+1 already uses the weight decided at dt, not a
    same-day weight). NaN signal -> that pair contributes 0 that period (no
    position, not "hold prior period"; excluded from the normalization)."""
    vol = realized_vol(closes, vol_window)
    raw = pd.DataFrame(index=closes.index, columns=closes.columns, dtype=float)
    reb_dates = signal_at_rebalance.index

    for i, dt in enumerate(reb_dates):
        if dt not in vol.index:
            continue
        sign = np.sign(signal_at_rebalance.loc[dt])
        v = vol.loc[dt].replace(0, np.nan)
        raw_w = (sign / v).reindex(closes.columns)
        gross = raw_w.abs().sum()
        w = raw_w / gross if gross > 0 else raw_w * 0.0
        end = reb_dates[i + 1] if i + 1 < len(reb_dates) else closes.index[-1]
        mask = (raw.index > dt) & (raw.index <= end)
        raw.loc[mask, :] = w.to_numpy()

    return raw.fillna(0.0)


def backtest_portfolio(
    weights: pd.DataFrame,
    closes: pd.DataFrame,
    target_vol: float = 0.10,
    vol_window: int = 252,
    cost_bps: float = 2.5,
    max_leverage: float = 3.0,
) -> pd.Series:
    """`weights` (from daily_weights_from_signal) already have gross
    exposure 1 at every date, so the portfolio return is a proper weighted
    SUM (not mean) of per-pair simple returns. Scales the whole portfolio
    to `target_vol` annualized using its own trailing `vol_window`-day
    realized vol (prior-day value, no lookahead, capped at `max_leverage`x
    so a rare near-zero trailing-vol reading can't blow up both the return
    AND the turnover-based cost - see module docstring), and subtracts
    per-rebalance-day transaction costs (cost_bps * turnover, turnover =
    sum of |weight_t - weight_{t-1}| across pairs on the ACTUALLY-APPLIED,
    leverage-scaled weights) - matches the paper's "results are presented
    net of trading costs, fixed at 2.5 basis points for all assets"."""
    simple_ret = closes.pct_change()
    raw_port_ret = (weights * simple_ret).sum(axis=1)

    trailing_vol = raw_port_ret.rolling(vol_window).std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)
    scale = (target_vol / trailing_vol.shift(1)).clip(upper=max_leverage)
    scaled_ret = raw_port_ret * scale

    scaled_weights = weights.multiply(scale, axis=0)
    turnover = scaled_weights.diff().abs().sum(axis=1).fillna(0.0)
    cost = turnover * (cost_bps / 10_000.0)
    net_ret = scaled_ret - cost

    return net_ret.dropna()
