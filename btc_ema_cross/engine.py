"""BTC/USDT EMA9/21 long-flat crossover - core simulation engine, factored
out of scripts/research_ema_9_21_cross_btc.py (2026-08-14/15 research
thread) so the Streamlit dashboard and the research script share one
implementation instead of two copies drifting apart.

Origin: "The Backtest Machine" cheat sheet (Miles Deutscher Finance) - EMA9
crosses EMA21 -> long, crosses back under -> flat, no leverage, no fixed
take-profit (crossover itself is the exit). The sheet's own strategy has no
stop-loss; `simulate_risk_sized` adds an ATR(14)x2.0 stop as a disclosed
extension to make risk-percentage-based position sizing meaningful.

All three simulate_* functions share the same `sim_from` warmup contract:
pass the FULL available price history (not a pre-sliced IS/OOS window) so
EMA/ATR are computed with proper lookback; `sim_from` then restricts the
simulation loop (and, for simulate_risk_sized, resets the account to a
fresh `capital` at that boundary) to the window actually being reported.
Slicing the DataFrame BEFORE computing indicators - as an earlier version
of this code did - restarts EMA/ATR cold at the window boundary and was
found to measurably bias results (see the research script's docstring)."""

import pandas as pd

from strategy.indicators import compute_atr

COMMISSION = 0.001  # 0.1% per side, matches the sheet's Pine Script spec
ATR_PERIOD = 14
ATR_STOP_MULT = 2.0


def simulate_ema_cross(df: pd.DataFrame, fast: int, slow: int, sim_from: pd.Timestamp | None = None) -> dict:
    """Long-flat state machine, no position sizing (100%-of-equity return
    series). Signal evaluated on bar i-1's close, filled at bar i's open."""
    close = df["close"]
    open_ = df["open"]
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    above = ema_fast > ema_slow
    go_long = (above & ~above.shift(1).fillna(False)).to_numpy()
    go_flat = (~above & above.shift(1).fillna(False)).to_numpy()

    start_i = max(df.index.searchsorted(sim_from) if sim_from is not None else 1, 1)

    position = 0
    entry_price = None
    daily_returns = []
    trade_returns = []
    for i in range(start_i, len(df)):
        ret = 0.0
        if position == 0 and go_long[i - 1]:
            position = 1
            entry_price = open_.iloc[i] * (1 + COMMISSION)
            ret = close.iloc[i] / entry_price - 1
        elif position == 1 and go_flat[i - 1]:
            exit_price = open_.iloc[i] * (1 - COMMISSION)
            ret = exit_price / close.iloc[i - 1] - 1
            trade_returns.append(exit_price / entry_price - 1)
            position = 0
        elif position == 1:
            ret = close.iloc[i] / close.iloc[i - 1] - 1
        daily_returns.append(ret)

    daily_returns = pd.Series(daily_returns, index=df.index[start_i:])
    equity = (1 + daily_returns).cumprod()

    n_years = (df.index[-1] - df.index[start_i]).days / 365.25
    total_return = equity.iloc[-1] - 1
    cagr = equity.iloc[-1] ** (1 / n_years) - 1 if n_years > 0 else float("nan")
    max_dd = (equity / equity.cummax() - 1).min()

    wins = [t for t in trade_returns if t > 0]
    losses = [t for t in trade_returns if t <= 0]
    win_rate = len(wins) / len(trade_returns) if trade_returns else float("nan")
    profit_factor = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else float("nan")

    return {
        "fast": fast, "slow": slow, "n_trades": len(trade_returns),
        "win_rate": win_rate, "profit_factor": profit_factor,
        "total_return": total_return, "cagr": cagr, "max_dd": max_dd, "equity": equity,
    }


def simulate_ema_cross_ls(df: pd.DataFrame, fast: int, slow: int, allow_short: bool,
                           sim_from: pd.Timestamp | None = None) -> dict:
    """Same fill logic as simulate_ema_cross, generalized to a long/short (or
    long/flat, if allow_short=False) state machine: short instead of flat
    while EMA9 < EMA21. Finding (2026-08-14): allow_short=True consistently
    underperforms allow_short=False on BTC (worse PF/CAGR/MaxDD, both IS and
    OOS) - kept here for the dashboard's comparison table, not recommended."""
    close = df["close"]
    open_ = df["open"]
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    above = ema_fast > ema_slow

    start_i = max(df.index.searchsorted(sim_from) if sim_from is not None else 1, 1)

    side = 0  # 0 flat, 1 long, -1 short
    entry_price = None
    daily_returns = []
    trade_returns = []
    for i in range(start_i, len(df)):
        ret = 0.0
        target = 1 if above.iloc[i - 1] else (-1 if allow_short else 0)
        if target != side:
            if side != 0:
                exit_price = open_.iloc[i] * (1 - COMMISSION if side == 1 else 1 + COMMISSION)
                trade_returns.append(side * (exit_price / entry_price - 1))
                ret += side * (exit_price / close.iloc[i - 1] - 1)
            if target != 0:
                entry_price = open_.iloc[i] * (1 + COMMISSION if target == 1 else 1 - COMMISSION)
                ret += target * (close.iloc[i] / entry_price - 1)
            side = target
        elif side != 0:
            ret = side * (close.iloc[i] / close.iloc[i - 1] - 1)
        daily_returns.append(ret)

    daily_returns = pd.Series(daily_returns, index=df.index[start_i:])
    equity = (1 + daily_returns).cumprod()

    n_years = (df.index[-1] - df.index[start_i]).days / 365.25
    total_return = equity.iloc[-1] - 1
    cagr = equity.iloc[-1] ** (1 / n_years) - 1 if n_years > 0 else float("nan")
    max_dd = (equity / equity.cummax() - 1).min()

    wins = [t for t in trade_returns if t > 0]
    losses = [t for t in trade_returns if t <= 0]
    win_rate = len(wins) / len(trade_returns) if trade_returns else float("nan")
    profit_factor = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else float("nan")

    return {
        "n_trades": len(trade_returns), "win_rate": win_rate,
        "profit_factor": profit_factor, "total_return": total_return,
        "cagr": cagr, "max_dd": max_dd, "equity": equity,
    }


def simulate_risk_sized(df: pd.DataFrame, fast: int, slow: int, capital: float,
                         risk_pct: float, atr_period: int = ATR_PERIOD, atr_stop_mult: float = ATR_STOP_MULT,
                         be_trigger_r: float | None = None, sim_from: pd.Timestamp | None = None) -> dict:
    """Long/flat EMA crossover with dollar position sizing: each entry risks
    `risk_pct` of CURRENT equity against an ATR(atr_period)*atr_stop_mult
    stop, one position at a time, no leverage (position notional capped at
    available equity). Exit is whichever comes first: the EMA crossunder
    (filled at next bar's open) or the ATR stop touched intrabar (checked
    against that bar's low, filled AT the stop price - no slippage/
    gap-through modeled).

    `be_trigger_r`: optional breakeven-stop - once unrealized profit
    (measured off the PRIOR bar's close) reaches be_trigger_r * initial stop
    distance, the stop moves to raw entry price. Finding (2026-08-14): barely
    moves CAGR but cuts win rate hard (many trades that would have recovered
    get stopped at breakeven first) - not recommended as a default."""
    close, open_, low = df["close"], df["open"], df["low"]
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    above = ema_fast > ema_slow
    go_long = (above & ~above.shift(1).fillna(False)).to_numpy()
    go_flat = (~above & above.shift(1).fillna(False)).to_numpy()
    atr = compute_atr(df, atr_period)

    start_i = max(df.index.searchsorted(sim_from) if sim_from is not None else 1, 1)

    cash = capital
    qty = 0.0
    entry_price = None
    raw_entry_price = None
    stop_price = None
    stop_dist_at_entry = None
    trade_risk_dollar = None
    be_moved = False
    in_pos = False
    capped_count = 0
    trades = []
    equity_curve = [capital]
    equity_dates = [df.index[start_i - 1]]

    for i in range(start_i, len(df)):
        exited_today = False

        if in_pos and be_trigger_r is not None and not be_moved:
            unrealized_r = (close.iloc[i - 1] - raw_entry_price) / stop_dist_at_entry
            if unrealized_r >= be_trigger_r:
                stop_price = raw_entry_price
                be_moved = True

        if in_pos and go_flat[i - 1]:
            exit_fill = open_.iloc[i] * (1 - COMMISSION)
            pnl = qty * (exit_fill - entry_price)
            trades.append({"pnl": pnl, "r": pnl / trade_risk_dollar, "stopped_out": False})
            cash += qty * exit_fill
            qty, in_pos, exited_today = 0.0, False, True
        elif in_pos and low.iloc[i] <= stop_price:
            exit_fill = stop_price * (1 - COMMISSION)
            pnl = qty * (exit_fill - entry_price)
            trades.append({"pnl": pnl, "r": pnl / trade_risk_dollar, "stopped_out": True})
            cash += qty * exit_fill
            qty, in_pos, exited_today = 0.0, False, True

        if not in_pos and not exited_today and go_long[i - 1] and pd.notna(atr.iloc[i - 1]):
            raw_entry = open_.iloc[i]
            entry_fill = raw_entry * (1 + COMMISSION)
            stop_dist = atr_stop_mult * atr.iloc[i - 1]
            if stop_dist > 0:
                target_qty = (cash * risk_pct) / stop_dist
                max_qty = cash / entry_fill
                if target_qty > max_qty:
                    target_qty = max_qty
                    capped_count += 1
                qty = target_qty
                entry_price = entry_fill
                raw_entry_price = raw_entry
                stop_price = raw_entry - stop_dist
                stop_dist_at_entry = stop_dist
                trade_risk_dollar = qty * stop_dist
                be_moved = False
                cash -= qty * entry_fill
                in_pos = True

        equity_curve.append(cash + (qty * close.iloc[i] if in_pos else 0.0))
        equity_dates.append(df.index[i])

    equity = pd.Series(equity_curve, index=equity_dates)
    n_years = (equity_dates[-1] - equity_dates[0]).days / 365.25
    total_return = equity.iloc[-1] / capital - 1
    cagr = (equity.iloc[-1] / capital) ** (1 / n_years) - 1 if n_years > 0 else float("nan")
    max_dd = (equity / equity.cummax() - 1).min()

    pnls = [t["pnl"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    win_rate = len(wins) / len(trades) if trades else float("nan")
    profit_factor = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else float("nan")
    avg_r = sum(t["r"] for t in trades) / len(trades) if trades else float("nan")
    n_stopped = sum(1 for t in trades if t["stopped_out"])

    daily_ret = equity.pct_change().fillna(0.0)
    worst_day_pct = daily_ret.min() * 100
    worst_day_date = daily_ret.idxmin()
    target_equity = capital * 1.10
    hit = equity[equity >= target_equity]
    days_to_10pct = (hit.index[0] - equity.index[0]).days if not hit.empty else None

    return {
        "n_trades": len(trades), "win_rate": win_rate, "profit_factor": profit_factor,
        "total_return": total_return, "cagr": cagr, "max_dd": max_dd,
        "end_equity": equity.iloc[-1], "avg_r": avg_r, "n_stopped": n_stopped,
        "n_capped": capped_count, "worst_day_pct": worst_day_pct,
        "worst_day_date": worst_day_date, "breached_3pct_daily_rule": worst_day_pct < -3.0,
        "days_to_10pct_target": days_to_10pct, "equity": equity, "trades": trades,
    }
