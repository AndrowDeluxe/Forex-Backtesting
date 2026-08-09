"""Execution-Overlay: fast-alpha (5-min streak-reversal) as a timing filter
for an ATR-breakout session-trend strategy. Zarattini & Pagani (2026),
"Improving Performance with Fast Alphas" -- see
app_pages/execution_overlay_writeup.py for the paper writeup.

Baseline (the trend strategy being timed):
  1. ATR(14) on daily bars, shifted one day (no lookahead) -> half-width
     band around today's session open: upper = open + 0.5*ATR,
     lower = open - 0.5*ATR.
  2. At each 15-minute execution mark (:00/:15/:30/:45) within the session,
     if flat and the most recent 5-min bar's close is beyond a band, enter
     in that direction.
  3. Stop = session open. Flatten at the session's last bar -- no overnight
     exposure, no exceptions.

Overlay: both the entry and the stop-exit are delayed until the first
5-minute bar moving AGAINST the just-triggered direction appears (N=1
streak-reversal), then executed at the next 15-minute mark after that bar.
If no such bar appears before the session ends, an entry signal is simply
missed for that day (never happens for an exit -- the EOD flatten always
fires as the backstop).
"""

import numpy as np
import pandas as pd
from scipy import stats

from strategy.indicators import compute_atr

EXEC_MINUTES = {0, 15, 30, 45}


def _session_groups(intraday_5m: pd.DataFrame):
    d = intraday_5m.rename(columns=str.lower).sort_index()
    for date, day_df in d.groupby(d.index.date):
        yield date, day_df.sort_index()


def _atr_by_date(daily: pd.DataFrame) -> pd.Series:
    """ATR(14) indexed by date, shifted 1 day: TODAY's bands use
    YESTERDAY's completed ATR, never today's own not-yet-known range."""
    d = daily.rename(columns=str.lower).sort_index()
    atr = compute_atr(d, n=14).shift(1)
    atr.index = pd.to_datetime(atr.index).date
    return atr


def _open_trade(date, direction, ts, price) -> dict:
    return {"entry_date": date, "direction": direction, "entry_time": ts, "entry_price": price}


def _close_trade(position: dict, ts, price, reason: str) -> dict:
    out = dict(position)
    out["exit_time"] = ts
    out["exit_price"] = price
    out["exit_reason"] = reason
    return out


def simulate(intraday_5m: pd.DataFrame, daily: pd.DataFrame, use_overlay: bool,
             spread_bps: float = 1.0) -> pd.DataFrame:
    """One row per completed trade. `direction`: 1=long, -1=short.
    `pnl_pct`/`gross_pnl_pct` are the trade's own return (already sign-
    adjusted for direction), spread_bps a round-trip cost in the same
    "basis points of price" convention as strategy/backtest.py."""
    atr_by_date = _atr_by_date(daily)
    trades: list[dict] = []

    for date, day in _session_groups(intraday_5m):
        atr = atr_by_date.get(date, np.nan)
        if pd.isna(atr) or day.empty:
            continue

        session_open = day["open"].iloc[0]
        upper, lower = session_open + 0.5 * atr, session_open - 0.5 * atr
        bar_times = list(day.index)

        position: dict | None = None
        pending_dir: int | None = None

        for i, ts in enumerate(bar_times):
            bar = day.loc[ts]
            is_last_bar = i == len(bar_times) - 1

            if position is not None:
                stop_state = position.get("stop_state", "none")
                if stop_state == "confirmed":
                    if ts.minute in EXEC_MINUTES:
                        trades.append(_close_trade(position, ts, bar["close"], "stop_overlay"))
                        position = None
                elif stop_state == "pending":
                    counter_bar = (
                        (position["direction"] == 1 and bar["close"] < bar["open"])
                        or (position["direction"] == -1 and bar["close"] > bar["open"])
                    )
                    if counter_bar:
                        position["stop_state"] = "confirmed"
                else:
                    hit_stop = (
                        (position["direction"] == 1 and bar["close"] <= session_open)
                        or (position["direction"] == -1 and bar["close"] >= session_open)
                    )
                    if hit_stop:
                        if use_overlay:
                            position["stop_state"] = "pending"
                        else:
                            trades.append(_close_trade(position, ts, bar["close"], "stop"))
                            position = None

                if position is not None and is_last_bar:
                    trades.append(_close_trade(position, ts, bar["close"], "eod"))
                    position = None
                continue

            if pending_dir is None:
                if ts.minute in EXEC_MINUTES:
                    if bar["close"] > upper:
                        breakout_dir = 1
                    elif bar["close"] < lower:
                        breakout_dir = -1
                    else:
                        breakout_dir = None
                    if breakout_dir is not None:
                        if use_overlay:
                            pending_dir = breakout_dir
                        else:
                            position = _open_trade(date, breakout_dir, ts, bar["close"])
                continue

            counter_bar = (
                (pending_dir == 1 and bar["close"] < bar["open"])
                or (pending_dir == -1 and bar["close"] > bar["open"])
            )
            if counter_bar:
                for j in range(i + 1, len(bar_times)):
                    entry_ts = bar_times[j]
                    if entry_ts.minute in EXEC_MINUTES:
                        entry_bar = day.loc[entry_ts]
                        position = _open_trade(date, pending_dir, entry_ts, entry_bar["close"])
                        break
                pending_dir = None  # confirmed-and-entered, or no exec mark left today: either way, done

    result = pd.DataFrame(trades)
    if result.empty:
        return result
    result["gross_pnl_pct"] = (
        result["direction"] * (result["exit_price"] - result["entry_price"]) / result["entry_price"] * 100
    )
    return apply_cost(result, spread_bps)


def apply_cost(trades: pd.DataFrame, spread_bps: float) -> pd.DataFrame:
    """Re-price an already-simulated trade set at a different round-trip
    cost, without re-running the (expensive) bar-by-bar simulation -- entries
    and exits never depend on spread_bps, only pnl_pct does."""
    if trades.empty:
        return trades
    out = trades.copy()
    out["pnl_pct"] = out["gross_pnl_pct"] - spread_bps / 100.0
    return out


def summarize(trades: pd.DataFrame, pnl_col: str = "pnl_pct") -> dict:
    if trades.empty:
        return {"n_trades": 0, "win_rate_pct": np.nan, "mean_pnl_pct": np.nan,
                "total_pnl_pct": np.nan, "profit_factor": np.nan,
                "t_stat": np.nan, "p_one_sided": np.nan}
    pnl = trades[pnl_col]
    n = len(pnl)
    wins, losses = pnl[pnl > 0], pnl[pnl <= 0]
    gross_win, gross_loss = wins.sum(), -losses.sum()
    mean, std = pnl.mean(), pnl.std(ddof=1) if n > 1 else np.nan
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
        "profit_factor": round(gross_win / gross_loss, 2) if gross_loss > 0 else np.nan,
        "t_stat": round(t_stat, 2) if not np.isnan(t_stat) else np.nan,
        "p_one_sided": round(p_one, 4) if not np.isnan(p_one) else np.nan,
    }
