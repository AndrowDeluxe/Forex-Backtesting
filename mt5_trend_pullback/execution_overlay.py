"""Execution-Overlay adaptation for the MT5 Trend+Pullback bot replication,
per Zarattini & Pagani (2026) "Improving Performance with Fast Alphas" (see
execution_overlay/engine.py and, closer in spirit, asian_range_breakout/
execution_overlay.py - a trend-continuation breakout, the same family as
this strategy). NOT part of the live bot - a research-only entry-timing
experiment.

Idea: once the real signal fires (EMA150 trend + RSI14 pullback-cross, on
the SIGNAL bar i), don't fill at the next bar's open like the live bot does.
Instead wait for the first subsequent bar whose CLOSE moves AGAINST the
trade direction (a down-close bar, since this strategy is long-only) - the
bar-close stand-in for the paper's fast, mean-reverting "streak-reversal"
micro-signal (this repo has no finer intrabar/tick feed at H1/H4, same
disclosed resolution downgrade as the ASB port) - then fill AT THAT BAR'S
CLOSE. If no such bar appears within `max_wait_bars`, the signal is skipped
entirely (the paper's own disclosed risk: this can miss entries during
strong, pullback-free trends) - `max_wait_bars` stands in for the ASB
version's natural "session end" cutoff, which this always-on strategy has no
equivalent of, so a bar count is used instead and is a real, disclosed
adaptation choice, not a validated parameter.

Everything else is UNCHANGED from strategy.backtest.simulate_trades's ATR-
stop/R-multiple-target mechanics, and the stop distance is deliberately
anchored to the SIGNAL bar's own ATR (not the delayed entry bar's), matching
the ASB overlay's "only entry timing changes, risk definition doesn't" rule
- so any difference in results vs. the non-overlay backtest is attributable
solely to the entry-timing change.
"""

import numpy as np
import pandas as pd

from strategy.backtest import BacktestConfig


def simulate_trades_overlay(df: pd.DataFrame, config: BacktestConfig = BacktestConfig(), max_wait_bars: int = 5) -> pd.DataFrame:
    required = {"open", "close", "atr", "signal"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"simulate_trades_overlay: missing columns {missing}")

    n = len(df)
    close = df["close"].to_numpy()
    atr = df["atr"].to_numpy()
    signal = df["signal"].to_numpy()
    times = df.index

    half_cost_frac = config.spread_bps / 10_000 / 2
    trades = []
    i = 0
    while i < n - 1:
        sig = signal[i]
        if sig != 1 or np.isnan(atr[i]) or atr[i] < config.min_atr:
            i += 1
            continue

        entry_i = None
        max_k = min(i + max_wait_bars, n - 1)
        k = i + 1
        while k <= max_k:
            if close[k] < close[k - 1]:  # long-only: counter-bar = down-close
                entry_i = k
                break
            k += 1

        if entry_i is None:
            i += 1  # overlay: no counter-bar within the wait window - signal skipped entirely
            continue

        raw_entry = close[entry_i]
        entry_price = raw_entry + raw_entry * half_cost_frac

        initial_risk = config.stop_atr_mult * atr[i]  # anchored to the SIGNAL bar's ATR, not entry_i's
        stop_level = entry_price - initial_risk

        exit_i, exit_reason = None, None
        j = entry_i
        while j < n:
            favor = close[j] - entry_price
            if close[j] < stop_level:
                exit_i, exit_reason = j, "stop"
                break
            if config.take_profit_r is not None and initial_risk > 0 and favor >= config.take_profit_r * initial_risk:
                exit_i, exit_reason = j, "target"
                break
            j += 1
        if exit_i is None:
            exit_i, exit_reason = n - 1, "data_end"

        raw_exit = close[exit_i]
        exit_price = raw_exit - raw_exit * half_cost_frac

        ret = (exit_price - entry_price) / entry_price
        r_multiple = (exit_price - entry_price) / initial_risk if initial_risk > 0 else float("nan")

        trades.append({
            "signal_time": times[i],
            "entry_time": times[entry_i],
            "exit_time": times[exit_i],
            "direction": 1,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "return_pct": ret,
            "exit_reason": exit_reason,
            "hold_bars": exit_i - entry_i,
            "wait_bars": entry_i - i,
            "adx_at_entry": df["adx"].iloc[entry_i] if "adx" in df.columns else np.nan,
            "atr_at_entry": atr[i],
            "initial_risk": initial_risk,
            "r_multiple": r_multiple,
        })
        i = exit_i + 1

    return pd.DataFrame(trades)
