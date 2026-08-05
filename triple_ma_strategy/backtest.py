"""Trade simulation for the Triple Moving Average strategy.

Unlike most other backtest engines in this repo, this strategy has no
stop-loss / take-profit - it is a pure long/flat trend-follower that rides
whatever the MA/crossover signal says (matching the paper, which only ever
plots a portfolio-value curve against Buy & Hold, no per-trade risk sizing).
So instead of a fixed-risk position-sizer, equity simply compounds the
asset's own daily return while `position` == 1, and sits flat otherwise.

Execution timing: `position` is computed from information available at each
bar's close (e.g. "Close > TEMA"). Acting on it at that same bar's close
would be lookahead - the earliest honest fill is the *next* bar, so
`position` is shifted by one bar before being applied to returns.
"""

import numpy as np
import pandas as pd


def simulate_trend_trades(
    df: pd.DataFrame, position: pd.Series, initial_equity: float = 10_000.0, cost_bps: float = 0.0,
) -> tuple[pd.DataFrame, pd.Series]:
    """`df` needs a "Close" column aligned to `position`'s index.
    `cost_bps`: round-trip-style cost charged on each position *change*
    (0 -> 1 or 1 -> 0), in basis points of notional.
    Returns (trades, equity) - equity is a full daily curve (incl. flat
    bars), trades is one row per contiguous long block for display/logging.
    """
    close = df["Close"].reindex(position.index)
    daily_ret = close.pct_change().fillna(0.0)
    held = position.shift(1).fillna(0.0)
    turnover = held.diff().abs()
    turnover.iloc[0] = held.iloc[0]
    cost = turnover * (cost_bps / 1e4)
    strat_ret = held * daily_ret - cost

    equity = initial_equity * (1.0 + strat_ret).cumprod()
    equity.name = "equity"

    trades = []
    block_id = (held != held.shift()).cumsum()
    for _, block in held.groupby(block_id):
        if block.iloc[0] != 1.0:
            continue
        start_loc = held.index.get_loc(block.index[0])
        end_ts = block.index[-1]
        if start_loc > 0:
            entry_time = held.index[start_loc - 1]
            entry_price = close.iloc[start_loc - 1]
        else:
            entry_time = block.index[0]
            entry_price = close.iloc[start_loc]
        exit_price = close.loc[end_ts]
        pnl_pct = exit_price / entry_price - 1.0
        trades.append({
            "entry_time": entry_time, "exit_time": end_ts,
            "entry_price": entry_price, "exit_price": exit_price,
            "hold_days": (end_ts - entry_time).days,
            "pnl_pct": pnl_pct,
        })

    trades_df = pd.DataFrame(trades)
    return trades_df, equity
