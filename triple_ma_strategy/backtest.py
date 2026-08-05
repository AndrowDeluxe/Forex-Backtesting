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


def simulate_trades_with_risk(
    df: pd.DataFrame, position: pd.Series, initial_equity: float = 10_000.0,
    risk_pct: float = 0.01, atr_window: int = 14, atr_mult_sl: float = 2.5,
    rr: float | None = None, cost_bps: float = 0.0,
) -> tuple[pd.DataFrame, pd.Series]:
    """Bar-by-bar state machine, same shape as ema_strategy/backtest.py's
    simulate_trades - fixed-risk sizing (risk_pct of equity per trade)
    instead of simulate_trend_trades' 100%-equity compounding, so a real
    ATR stop-loss (and optional take-profit) can be attached.

    Entry: on the bar `position` flips 0 -> 1, fill at the *next* bar's
    Open (matching this module's no-lookahead convention) with
    SL = entry - atr_mult_sl * ATR(atr_window). Exit: whichever of
    SL / TP (if `rr` is set, `rr` * initial risk above entry) / the
    underlying trend signal flipping back to 0 (at that bar's Close)
    happens first - so this still rides the same TEMA/TSMA trend, just
    with a hard downside cut added on top instead of relying solely on
    the (slower) signal-based exit.

    Returns (trades, equity) with the same trades schema as
    ema_strategy/backtest.py (entry_time/exit_time/direction/entry/exit/
    sl/tp/pnl/reason + r_multiple) so ema_strategy.metrics.compute_metrics
    can be reused as-is instead of re-deriving R-multiple stats here.
    """
    df = df.reindex(position.index)
    n = len(df)
    atr = (df["High"] - df["Low"]).rolling(atr_window).mean()

    dates = position.index
    pos_arr = position.to_numpy()
    open_, high, low, close = (df[c].to_numpy() for c in ("Open", "High", "Low", "Close"))
    atr_arr = atr.to_numpy()

    equity = initial_equity
    equity_curve = np.full(n, np.nan)
    trades = []

    in_pos = False
    entry_price = sl = tp = entry_idx = None
    pos_size = 0.0

    for i in range(n):
        equity_curve[i] = equity

        if in_pos:
            exit_price = reason = None
            if low[i] <= sl:
                exit_price, reason = sl, "SL"
            elif tp is not None and high[i] >= tp:
                exit_price, reason = tp, "TP"
            elif pos_arr[i] == 0.0:
                exit_price, reason = close[i], "Signal-Exit"

            if exit_price is not None:
                cost = pos_size * (entry_price + exit_price) * (cost_bps / 1e4)
                pnl = pos_size * (exit_price - entry_price) - cost
                equity += pnl
                trades.append({
                    "entry_time": dates[entry_idx], "exit_time": dates[i],
                    "direction": "LONG", "entry": entry_price, "exit": exit_price,
                    "sl": sl, "tp": tp, "pnl": pnl, "reason": reason,
                })
                in_pos = False
            continue

        if i < 1 or np.isnan(atr_arr[i]):
            continue
        if pos_arr[i] == 1.0 and pos_arr[i - 1] == 0.0:
            entry_idx = i + 1
            if entry_idx >= n:
                continue
            entry_price = open_[entry_idx]
            sl = entry_price - atr_mult_sl * atr_arr[i]
            risk_per_unit = entry_price - sl
            if risk_per_unit <= 0:
                continue
            tp = entry_price + rr * risk_per_unit if rr else None
            pos_size = (equity * risk_pct) / risk_per_unit
            in_pos = True

    trades_df = pd.DataFrame(trades)
    if not trades_df.empty:
        trades_df["r_multiple"] = trades_df["pnl"] / (initial_equity * risk_pct)
    eq = pd.Series(equity_curve, index=dates, name="equity")
    return trades_df, eq
