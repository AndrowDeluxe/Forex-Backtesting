"""Multi-position trade simulator (chat 2026-08-19: "hebe die Regel nur
ein Trade gleichzeitig auf. Damit sollte es auch moeglich sein einen
langen Move mehrmals zu reentern").

strategy.backtest.simulate_trades is shared infrastructure used by many
other strategies in this repo, and its "single position at a time, new
signals while a trade is open are ignored" behaviour (Sec. 5.3-equivalent
framing, see its own docstring) is relied upon elsewhere - it is
deliberately NOT modified here. This module is a sibling simulator (same
convention as mt5_trend_pullback/execution_overlay.py's simulate_trades_
overlay): identical per-trade mechanics (entry at next bar's open, same
stop/breakeven/trailing/target/max_hold exit precedence, same spread-cost
model), but every signal bar opens its OWN independent position instead
of being skipped while an earlier one is still open - so a persistent
move can be re-entered multiple times.

Capital-accounting simplification (stated explicitly, not hidden): each
concurrent position is treated as its own full-notional bet, same as a
single strategy.backtest.simulate_trades position - overlapping trades
are NOT capital-constrained against each other. Combined via
strategy.backtest.trades_to_daily_returns (unmodified, reused as-is: it
compounds same-day EXITS together and doesn't care whether trades
overlapped while open) - a real account would need per-trade position
sizing to avoid over-leveraging when several positions are open at once;
this module surfaces WHETHER re-entry helps at the signal-quality level,
not a funded-account sizing answer."""

import heapq

import numpy as np
import pandas as pd

from strategy.backtest import BacktestConfig


def simulate_trades_concurrent(df: pd.DataFrame, config: BacktestConfig = BacktestConfig()) -> pd.DataFrame:
    required = {"open", "close", "vwap", "atr", "prev_high", "prev_low", "signal", "session"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"simulate_trades_concurrent: missing columns {missing}")

    n = len(df)
    open_ = df["open"].to_numpy()
    close = df["close"].to_numpy()
    vwap = df["vwap"].to_numpy()
    atr = df["atr"].to_numpy()
    prev_high = df["prev_high"].to_numpy()
    prev_low = df["prev_low"].to_numpy()
    signal = df["signal"].to_numpy()
    session_codes = pd.factorize(df["session"].to_numpy())[0]
    times = df.index

    half_cost_frac = config.spread_bps / 10_000 / 2

    trades = []
    for i in range(n - 1):
        sig = signal[i]
        if sig == 0 or np.isnan(atr[i]) or atr[i] < config.min_atr:
            continue

        direction = int(sig)
        entry_i = i + 1
        entry_session = session_codes[entry_i]

        raw_entry = open_[entry_i]
        cost = raw_entry * half_cost_frac
        entry_price = raw_entry - cost if direction == -1 else raw_entry + cost

        trigger_level = prev_high[entry_i] if direction == -1 else prev_low[entry_i]
        stop_level = (
            trigger_level + config.stop_atr_mult * atr[entry_i]
            if direction == -1
            else trigger_level - config.stop_atr_mult * atr[entry_i]
        )
        initial_risk = abs(entry_price - stop_level)
        be_moved = False
        be_time = None
        best_favor_price = entry_price
        mfe = 0.0
        mae = 0.0

        exit_i, exit_reason = None, None
        j = entry_i
        while j < n:
            if session_codes[j] != entry_session:
                exit_i, exit_reason = max(j - 1, entry_i), "session_end"
                break

            favor = (entry_price - close[j]) if direction == -1 else (close[j] - entry_price)
            mfe = max(mfe, favor)
            mae = min(mae, favor)

            if config.breakeven_trigger_r is not None and not be_moved and initial_risk > 0:
                if favor >= config.breakeven_trigger_r * initial_risk:
                    stop_level = entry_price
                    be_moved = True
                    be_time = times[j]

            if config.trailing_atr_mult is not None:
                if direction == -1:
                    best_favor_price = min(best_favor_price, close[j])
                    stop_level = min(stop_level, best_favor_price + config.trailing_atr_mult * atr[entry_i])
                else:
                    best_favor_price = max(best_favor_price, close[j])
                    stop_level = max(stop_level, best_favor_price - config.trailing_atr_mult * atr[entry_i])

            if direction == -1 and close[j] > stop_level:
                exit_i, exit_reason = j, "stop" if not be_moved else "breakeven"
                break
            if direction == 1 and close[j] < stop_level:
                exit_i, exit_reason = j, "stop" if not be_moved else "breakeven"
                break
            if config.use_vwap_target and direction == -1 and close[j] <= vwap[j]:
                exit_i, exit_reason = j, "target"
                break
            if config.use_vwap_target and direction == 1 and close[j] >= vwap[j]:
                exit_i, exit_reason = j, "target"
                break
            if config.take_profit_r is not None and initial_risk > 0 and favor >= config.take_profit_r * initial_risk:
                exit_i, exit_reason = j, "target"
                break
            if config.max_hold_bars is not None and (j - entry_i) >= config.max_hold_bars:
                exit_i, exit_reason = j, "max_hold"
                break
            j += 1
        if exit_i is None:
            exit_i, exit_reason = n - 1, "data_end"

        raw_exit = close[exit_i]
        cost = raw_exit * half_cost_frac
        exit_price = raw_exit + cost if direction == -1 else raw_exit - cost

        ret = (entry_price - exit_price) / entry_price if direction == -1 else (exit_price - entry_price) / entry_price

        trades.append(
            {
                "entry_time": times[entry_i],
                "exit_time": times[exit_i],
                "direction": direction,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "return_pct": ret,
                "exit_reason": exit_reason,
                "hold_bars": exit_i - entry_i,
                "adx_at_entry": df["adx"].iloc[entry_i] if "adx" in df.columns else np.nan,
                "atr_at_entry": atr[entry_i],
                "moved_to_be": be_moved,
                "be_time": be_time,
                "mfe_r": (mfe / initial_risk) if initial_risk > 0 else float("nan"),
                "mae_r": (mae / initial_risk) if initial_risk > 0 else float("nan"),
                "initial_risk": initial_risk,
                "r_multiple": (direction * (exit_price - entry_price) / initial_risk) if initial_risk > 0 else float("nan"),
                "signal_bar": i,  # kept for overlap diagnostics - not in the single-position simulator
            }
        )
        # NOT skipping ahead to exit_i + 1 - every signal bar gets its own
        # trade, regardless of whether an earlier one is still open. This
        # is the one substantive difference from strategy.backtest.
        # simulate_trades.

    return pd.DataFrame(trades)


def simulate_account_reentry(
    trades: pd.DataFrame,
    starting_equity: float = 100_000.0,
    risk_pct: float = 0.01,
    max_concurrent: int | None = None,
) -> dict:
    """Dollar-denominated, fixed-fractional-risk account simulation for
    trades on a SINGLE instrument where MULTIPLE positions can be open at
    once - adapted from mt5_trend_pullback/account_simulation.py's
    simulate_account (same time-ordered equity-settlement engine, a heap
    keyed by exit time), but that one caps at ONE position per market;
    here every trade gets its own slot, capped only by `max_concurrent`
    (None = uncapped) - needed because simulate_trades_concurrent's naive
    aggregation via strategy.backtest.trades_to_daily_returns multiplies
    same-day-exiting trades together as if sequential, which is nonsense
    once many positions overlap (produced a literal 4750% CAGR / -88%
    MaxDD on the first attempt here). risk_pct is of CURRENT equity, so
    still compounds correctly even with several open slots."""
    if trades.empty or "r_multiple" not in trades.columns:
        return {"trades": pd.DataFrame(), "equity_curve": pd.DataFrame(columns=["time", "equity"]), "final_equity": starting_equity, "n_taken": 0, "n_skipped": 0}

    pool = trades.dropna(subset=["r_multiple"]).sort_values("entry_time").reset_index(drop=True)
    if pool.empty:
        return {"trades": pd.DataFrame(), "equity_curve": pd.DataFrame(columns=["time", "equity"]), "final_equity": starting_equity, "n_taken": 0, "n_skipped": 0}

    equity = starting_equity
    open_positions: dict[int, tuple] = {}  # trade_id -> (exit_time, risk_dollars, r_multiple)
    exit_heap: list[tuple[pd.Timestamp, int]] = []
    next_id = 0

    accepted_rows = []
    equity_points = [(pool["entry_time"].iloc[0], equity)]
    n_skipped = 0

    def settle_up_to(t: pd.Timestamp) -> None:
        nonlocal equity
        while exit_heap and exit_heap[0][0] <= t:
            exit_time, tid = heapq.heappop(exit_heap)
            if tid not in open_positions:
                continue
            _, risk_dollars, r_multiple = open_positions.pop(tid)
            equity += risk_dollars * r_multiple
            equity_points.append((exit_time, equity))

    blown = False
    for _, row in pool.iterrows():
        t_entry = row["entry_time"]
        settle_up_to(t_entry)

        # BUGFIX (chat 2026-08-19, found via the standout sweep combo
        # showing a self-contradictory Sharpe=+1.28 alongside CAGR=-100%):
        # once equity hits zero, a real account is blown and can't open
        # further positions - continuing to size off a zero/negative
        # equity base flips risk_dollars negative, so a further LOSS
        # multiplies two negatives into a positive pnl, letting the
        # simulated account "recover" from ruin in a way no real broker
        # would ever allow. Halt entries permanently once this happens.
        if blown or equity <= 0:
            blown = True
            n_skipped += 1
            continue

        if max_concurrent is not None and len(open_positions) >= max_concurrent:
            n_skipped += 1
            continue

        risk_dollars = equity * risk_pct
        tid = next_id
        next_id += 1
        open_positions[tid] = (row["exit_time"], risk_dollars, row["r_multiple"])
        heapq.heappush(exit_heap, (row["exit_time"], tid))
        accepted_rows.append({
            "entry_time": t_entry, "exit_time": row["exit_time"],
            "exit_reason": row.get("exit_reason"), "r_multiple": row["r_multiple"],
            "risk_dollars": risk_dollars, "equity_at_entry": equity,
        })

    settle_up_to(pool["exit_time"].max() + pd.Timedelta(days=1))

    taken = pd.DataFrame(accepted_rows)
    if not taken.empty:
        taken["pnl"] = taken["risk_dollars"] * taken["r_multiple"]
    equity_curve = pd.DataFrame(equity_points, columns=["time", "equity"]).drop_duplicates(subset="time", keep="last")

    return {"trades": taken, "equity_curve": equity_curve, "final_equity": equity, "n_taken": len(taken), "n_skipped": n_skipped}


def simulate_combined_account(
    trades_by_strategy: dict[str, pd.DataFrame],
    risk_pct_by_strategy: dict[str, float],
    max_concurrent_by_strategy: dict[str, int | None] | None = None,
    starting_equity: float = 100_000.0,
) -> dict:
    """Runs MULTIPLE independently-signalled strategies on ONE shared,
    real account equity pool (chat 2026-08-20: portfolio risk-sizing for
    a prop-firm challenge with a single funded balance, not two walled-off
    capital sleeves - "max 1% pro Position" is a rule the firm checks
    against the ONE real account, so each strategy's position size must be
    computed off the SAME live equity, not an independently-compounding
    slice of starting capital).

    Same heap-based time-ordered settlement as simulate_account_reentry,
    generalised to: (a) accept several trade pools at once, each tagged
    with its own risk_pct (this IS the "weighting" knob - a strategy that
    risks more per trade de-facto gets more of the shared risk budget) and
    its own max_concurrent cap (checked per-strategy, so Reversal filling
    its 3 slots never blocks Continuation from opening), and (b) a single
    `blown` halt shared across both once equity <= 0, since it's the same
    real account."""
    max_concurrent_by_strategy = max_concurrent_by_strategy or {}
    pools = []
    for name, trades in trades_by_strategy.items():
        if trades.empty or "r_multiple" not in trades.columns:
            continue
        p = trades.dropna(subset=["r_multiple"])[["entry_time", "exit_time", "r_multiple", "exit_reason"]].copy()
        p["strategy"] = name
        pools.append(p)
    if not pools:
        return {"trades": pd.DataFrame(), "equity_curve": pd.DataFrame(columns=["time", "equity"]), "final_equity": starting_equity, "n_taken": 0, "n_skipped": 0}

    pool = pd.concat(pools, ignore_index=True).sort_values("entry_time").reset_index(drop=True)

    equity = starting_equity
    open_positions: dict[int, tuple] = {}  # trade_id -> (strategy, risk_dollars, r_multiple)
    open_count_by_strategy: dict[str, int] = {name: 0 for name in trades_by_strategy}
    exit_heap: list[tuple[pd.Timestamp, int]] = []
    next_id = 0

    accepted_rows = []
    equity_points = [(pool["entry_time"].iloc[0], equity)]
    n_skipped = 0

    def settle_up_to(t: pd.Timestamp) -> None:
        nonlocal equity
        while exit_heap and exit_heap[0][0] <= t:
            exit_time, tid = heapq.heappop(exit_heap)
            if tid not in open_positions:
                continue
            strategy, risk_dollars, r_multiple = open_positions.pop(tid)
            open_count_by_strategy[strategy] -= 1
            equity += risk_dollars * r_multiple
            equity_points.append((exit_time, equity))

    blown = False
    for _, row in pool.iterrows():
        strategy = row["strategy"]
        t_entry = row["entry_time"]
        settle_up_to(t_entry)

        if blown or equity <= 0:
            blown = True
            n_skipped += 1
            continue

        cap = max_concurrent_by_strategy.get(strategy)
        if cap is not None and open_count_by_strategy[strategy] >= cap:
            n_skipped += 1
            continue

        risk_dollars = equity * risk_pct_by_strategy[strategy]
        tid = next_id
        next_id += 1
        open_positions[tid] = (strategy, risk_dollars, row["r_multiple"])
        open_count_by_strategy[strategy] += 1
        heapq.heappush(exit_heap, (row["exit_time"], tid))
        accepted_rows.append({
            "strategy": strategy, "entry_time": t_entry, "exit_time": row["exit_time"],
            "exit_reason": row.get("exit_reason"), "r_multiple": row["r_multiple"],
            "risk_dollars": risk_dollars, "equity_at_entry": equity,
        })

    settle_up_to(pool["exit_time"].max() + pd.Timedelta(days=1))

    taken = pd.DataFrame(accepted_rows)
    if not taken.empty:
        taken["pnl"] = taken["risk_dollars"] * taken["r_multiple"]
    equity_curve = pd.DataFrame(equity_points, columns=["time", "equity"]).drop_duplicates(subset="time", keep="last")

    return {"trades": taken, "equity_curve": equity_curve, "final_equity": equity, "n_taken": len(taken), "n_skipped": n_skipped}


def equity_curve_to_daily_returns(equity_curve: pd.DataFrame, index_for_span: pd.DatetimeIndex) -> pd.Series:
    """Forward-fills the event-timestamped equity curve to a daily series
    (spanning `index_for_span`'s own full calendar range, matching
    strategy.backtest.trades_to_daily_returns' convention) and returns its
    daily pct-change - feed this into strategy.metrics.annualized_sharpe/
    cagr/max_drawdown directly."""
    span_naive = index_for_span.tz_localize(None) if index_for_span.tz is not None else index_for_span
    days = pd.date_range(span_naive.min().normalize(), span_naive.max().normalize(), freq="D")
    if equity_curve.empty:
        return pd.Series(0.0, index=days)
    curve = equity_curve.set_index("time")["equity"].sort_index()
    curve.index = curve.index.tz_localize(None) if curve.index.tz is not None else curve.index
    daily_equity = curve.reindex(curve.index.union(days)).sort_index().ffill().reindex(days).bfill()
    return daily_equity.pct_change().fillna(0.0)
