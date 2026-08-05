"""Bollinger Band mean-reversion backtest engine (paper section 4.1).

Rules:
- Entry: close < lower band -> long; close > upper band -> short. Only when flat.
- Exit: close crosses back over the moving average, OR a 2-sigma (vs. entry-day std)
  stop-loss is hit, OR the trade has been held >= MAX_HOLDING_DAYS.
- Decisions are evaluated once per day at the close (paper's own stated limitation).

Per ticker this produces a daily return series (0 while flat) plus a trade list;
the caller aggregates across tickers into one equal-weighted portfolio.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

import config


@dataclass
class TickerBacktestResult:
    ticker: str
    daily_return: pd.Series
    active: pd.Series
    trades: list[dict] = field(default_factory=list)


def backtest_ticker(
    price: pd.Series,
    start: str,
    end: str,
    lookback: int = config.BB_LOOKBACK,
    k: float = config.BB_K,
    max_hold: int = config.MAX_HOLDING_DAYS,
    stop_sigma: float = config.STOP_LOSS_SIGMA,
) -> TickerBacktestResult | None:
    price = price.dropna()
    ma = price.rolling(lookback).mean()
    std = price.rolling(lookback).std()
    upper = ma + k * std
    lower = ma - k * std

    idx = price.index
    in_window = (idx >= pd.Timestamp(start)) & (idx <= pd.Timestamp(end))
    if not in_window.any():
        return None
    window_positions = np.flatnonzero(in_window)
    start_i, end_i = window_positions[0], window_positions[-1]
    if start_i == 0:
        start_i = 1  # need i-1 for daily returns

    close = price.values
    ma_v, upper_v, lower_v, std_v = ma.values, upper.values, lower.values, std.values
    n = len(close)

    daily_ret = np.zeros(n)
    active = np.zeros(n, dtype=bool)
    trades = []

    state = 0  # 0 flat, 1 long, -1 short
    entry_price = entry_std = entry_i = None

    for i in range(start_i, end_i + 1):
        if np.isnan(ma_v[i]) or np.isnan(std_v[i]) or std_v[i] == 0:
            continue

        if state == 0:
            if close[i] < lower_v[i]:
                state, entry_price, entry_std, entry_i = 1, close[i], std_v[i], i
            elif close[i] > upper_v[i]:
                state, entry_price, entry_std, entry_i = -1, close[i], std_v[i], i
            continue

        prev_close = close[i - 1]
        daily_ret[i] = (close[i] / prev_close - 1) if state == 1 else -(close[i] / prev_close - 1)
        active[i] = True

        days_held = i - entry_i
        exit_now, reason = False, None
        if state == 1:
            stop_price = entry_price - stop_sigma * entry_std
            if close[i] <= stop_price:
                exit_now, reason = True, "stop_loss"
            elif close[i] >= ma_v[i]:
                exit_now, reason = True, "mean_revert"
            elif days_held >= max_hold:
                exit_now, reason = True, "max_holding"
        else:
            stop_price = entry_price + stop_sigma * entry_std
            if close[i] >= stop_price:
                exit_now, reason = True, "stop_loss"
            elif close[i] <= ma_v[i]:
                exit_now, reason = True, "mean_revert"
            elif days_held >= max_hold:
                exit_now, reason = True, "max_holding"

        if exit_now:
            pnl = (close[i] / entry_price - 1) if state == 1 else (entry_price / close[i] - 1)
            trades.append(
                {
                    "ticker": price.name,
                    "direction": "long" if state == 1 else "short",
                    "entry_date": idx[entry_i],
                    "exit_date": idx[i],
                    "entry_price": entry_price,
                    "exit_price": close[i],
                    "days_held": days_held,
                    "pnl": pnl,
                    "reason": reason,
                }
            )
            state, entry_price, entry_std, entry_i = 0, None, None, None

    sl = slice(start_i, end_i + 1)
    return TickerBacktestResult(
        ticker=price.name,
        daily_return=pd.Series(daily_ret[sl], index=idx[sl]),
        active=pd.Series(active[sl], index=idx[sl]),
        trades=trades,
    )


def backtest_universe(panel: pd.DataFrame, tickers: list[str], start: str, end: str) -> dict:
    results = {}
    for t in tickers:
        if t not in panel.columns:
            continue
        s = panel[t].dropna()
        s.name = t
        r = backtest_ticker(s, start, end)
        if r is not None:
            results[t] = r
    return results


def aggregate_portfolio(results: dict) -> tuple[pd.Series, list[dict]]:
    """Equal-weight, across tickers with an open position that day; 0 (cash) if none."""
    ret_df = pd.concat({t: r.daily_return for t, r in results.items()}, axis=1)
    active_df = pd.concat({t: r.active for t, r in results.items()}, axis=1)
    masked = ret_df.where(active_df, np.nan)
    n_active = active_df.sum(axis=1)
    portfolio_ret = masked.mean(axis=1).fillna(0.0)
    portfolio_ret = portfolio_ret.where(n_active > 0, 0.0)
    all_trades = [tr for r in results.values() for tr in r.trades]
    return portfolio_ret, all_trades
