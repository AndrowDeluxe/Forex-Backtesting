"""Gap-Fade EUR/USD & GBP/USD -- daily weekend-gap fade.

Reconstructs the core rule from Caporale & Plastun (2016), "Price Gaps:
Another Market Anomaly?" (Brunel University London / Sumy State University,
Working Paper 16-16, SSRN 2850057): short at the open whenever the day's
open gaps up from the prior close by at least `threshold_pct`, flatten at
the close (EOD). No stop-loss in the source paper -- flagged as an open
caveat in app_pages/gap_fade_writeup.py.

The paper's own MetaTrader-robot backtest names no explicit cost model.
This engine always nets a spread_bps round-trip cost, using the same
"basis points of price" convention already established in
strategy/backtest.py (spread_bps / 10_000 = round-trip cost fraction).
"""

import numpy as np
import pandas as pd
from scipy import stats

# Fixed a priori from the paper's own Table 7 profit/drawdown trade-off pick
# -- NOT re-optimised on this repo's data. See the in-sample-threshold-
# selection caveat in app_pages/gap_fade_writeup.py.
DEFAULT_THRESHOLD_PCT = {"EURUSD": 0.10, "GBPUSD": 0.05}


def compute_gap_trades(daily: pd.DataFrame, threshold_pct: float, spread_bps: float = 1.0) -> pd.DataFrame:
    """One row per day with a qualifying positive gap.

    `daily`: daily OHLC indexed by date (any case column names). Returns a
    DataFrame indexed by entry_date with gap_pct, gross_pnl_pct (before
    cost) and pnl_pct (after a spread_bps round-trip cost) -- both are the
    SHORT position's return, so positive = profitable trade.

    Dukascopy's D1 candles use midnight-UTC boundaries, not the FX trading
    week -- the market reopens Sunday ~21-22:00 UTC, so there is a near-
    empty "Sunday" candle (a couple of hours, tiny volume) ahead of every
    Monday bar. Left in, `shift(1)` compares Monday's open to that sliver's
    close instead of Friday's real close, splitting one weekend gap into two
    much smaller ones and silently undercounting qualifying days. Dropping it
    roughly doubled the in-sample trade counts for both pairs (see
    scripts/research_gap_fade.py's sanity-check printout): GBP/USD then
    lands within ~5% of the paper's own Table 7 counts at every threshold
    (strong pipeline confidence), while EUR/USD still runs ~2.5x above the
    paper's counts for reasons not fully diagnosed (checked: not an early-
    history data-quality artifact -- the extra gap-days are spread evenly
    across 2003-2015, not concentrated pre-2005). Treat EUR/USD's in-sample
    replication as directionally right but not a precise match; GBP/USD's
    match is the stronger evidence the gap-detection logic itself is sound.
    Dropped here so `shift(1)` lands on the last real trading day.
    """
    d = daily.rename(columns=str.lower).sort_index().copy()
    d = d[d.index.dayofweek != 6]  # drop the Dukascopy Sunday-reopen sliver
    d["prev_close"] = d["close"].shift(1)
    d["gap_pct"] = (d["open"] - d["prev_close"]) / d["prev_close"] * 100

    signal = d["gap_pct"] >= threshold_pct
    trades = d.loc[signal, ["open", "close", "gap_pct"]].copy()
    if trades.empty:
        return trades.assign(gross_pnl_pct=pd.Series(dtype=float), pnl_pct=pd.Series(dtype=float))

    gross_pnl_pct = (trades["open"] - trades["close"]) / trades["open"] * 100  # short: down = profit
    cost_pct = spread_bps / 100.0  # round-trip; spread_bps=1.0 -> 0.01% total cost
    trades["gross_pnl_pct"] = gross_pnl_pct
    trades["pnl_pct"] = gross_pnl_pct - cost_pct
    trades.index.name = "entry_date"
    return trades


def summarize(trades: pd.DataFrame, pnl_col: str = "pnl_pct") -> dict:
    """One-sample t-test of per-trade pnl against zero, one-sided (H1: mean > 0)."""
    if trades.empty:
        return {"n_trades": 0, "win_rate_pct": np.nan, "mean_pnl_pct": np.nan,
                "total_pnl_pct": np.nan, "t_stat": np.nan, "p_one_sided": np.nan}
    pnl = trades[pnl_col]
    n = len(pnl)
    mean = pnl.mean()
    std = pnl.std(ddof=1) if n > 1 else np.nan
    if n > 1 and std > 0:
        t_stat, p_two = stats.ttest_1samp(pnl, 0.0)
        p_one = p_two / 2 if mean > 0 else 1 - p_two / 2
    else:
        t_stat, p_one = np.nan, np.nan
    return {
        "n_trades": n,
        "win_rate_pct": round((pnl > 0).mean() * 100, 1),
        "mean_pnl_pct": round(mean, 4),
        "total_pnl_pct": round(pnl.sum(), 2),
        "t_stat": round(t_stat, 2) if not np.isnan(t_stat) else np.nan,
        "p_one_sided": round(p_one, 4) if not np.isnan(p_one) else np.nan,
    }


def yearly_breakdown(trades: pd.DataFrame, pnl_col: str = "pnl_pct") -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame(columns=["trades", "total_pnl_pct", "win_rate_pct"])
    rows = []
    for year, grp in trades.groupby(trades.index.year):
        pnl = grp[pnl_col]
        rows.append({
            "year": int(year),
            "trades": len(pnl),
            "total_pnl_pct": round(pnl.sum(), 2),
            "win_rate_pct": round((pnl > 0).mean() * 100, 1),
        })
    return pd.DataFrame(rows).set_index("year")


def threshold_sweep(daily: pd.DataFrame, thresholds=(0.05, 0.10, 0.15, 0.20, 0.25),
                     spread_bps: float = 0.0) -> pd.DataFrame:
    """Trade count is independent of spread_bps (only pnl is affected) -- default
    0.0 here so this reproduces the paper's own gross Table 7 shape directly."""
    rows = []
    for th in thresholds:
        trades = compute_gap_trades(daily, th, spread_bps=spread_bps)
        rows.append({"threshold_pct": th, **summarize(trades)})
    return pd.DataFrame(rows)
