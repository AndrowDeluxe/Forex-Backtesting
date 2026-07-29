"""Multi-position trade simulator: unlike strategy/backtest.py and
ema_strategy/backtest.py, trades here are independent of each other rather
than one-at-a-time - the checklist's own rules allow overlapping positions,
so each signal is walked forward to its own exit without blocking on
whether an earlier trade is still open.

Fidelity choices, consistent with the rest of the project:
- Execution lag: signal known at bar i's close -> fills at bar i+1's open.
- SL/TP fills use the level itself (not the bar's close), matching
  ema_strategy/backtest.py's convention.
- Same-bar ambiguity (break-even trigger and the pre-move stop both
  touched within one bar's range) is resolved conservatively: the
  breakeven move is checked first, so a bar that reaches 1R favourable
  and then reverses hard within the same bar scratches at breakeven
  rather than banking the original stop distance - probably a rare edge
  case, but the pessimistic assumption of the two.
"""

import numpy as np
import pandas as pd


def simulate_checklist_trades(
    df: pd.DataFrame,
    spread_bps: float = 0.3,
    stop_atr_mult: float = 2.5,
    rr_target: float = 2.0,
    breakeven_at_r: float = 1.0,
    max_hold_bars: int | None = None,
    min_atr: float = 1e-12,
) -> pd.DataFrame:
    required = {"open", "high", "low", "close", "atr", "signal"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"simulate_checklist_trades: missing columns {missing}")

    n = len(df)
    open_ = df["open"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    atr = df["atr"].to_numpy()
    signal = df["signal"].to_numpy()
    times = df.index

    half_cost_frac = spread_bps / 10_000 / 2
    trades = []

    for i in np.nonzero(signal)[0]:
        entry_i = i + 1
        if entry_i >= n or np.isnan(atr[i]) or atr[i] < min_atr:
            continue

        direction = int(signal[i])
        raw_entry = open_[entry_i]
        cost = raw_entry * half_cost_frac
        entry_price = raw_entry - cost if direction == -1 else raw_entry + cost

        risk_per_unit = stop_atr_mult * atr[i]
        sl = entry_price + risk_per_unit if direction == -1 else entry_price - risk_per_unit
        tp = (
            entry_price - rr_target * risk_per_unit
            if direction == -1
            else entry_price + rr_target * risk_per_unit
        )
        be_trigger = (
            entry_price - breakeven_at_r * risk_per_unit
            if direction == -1
            else entry_price + breakeven_at_r * risk_per_unit
        )

        moved_to_be = False
        exit_i, exit_reason = None, None
        j = entry_i
        while j < n:
            # Check this bar's stop/target against the SL as it stood at the
            # *start* of the bar, before considering a same-bar breakeven
            # move - otherwise a single bar that runs from favourable (past
            # the breakeven trigger) all the way to the target would be
            # misread as a breakeven stop-out, since the freshly-moved SL
            # would then sit inside that same bar's range too. The breakeven
            # move itself is only applied for bars *after* this one.
            if direction == -1:
                if high[j] >= sl:
                    exit_i, exit_reason = j, "breakeven" if moved_to_be else "stop"
                    break
                if low[j] <= tp:
                    exit_i, exit_reason = j, "target"
                    break
                if not moved_to_be and low[j] <= be_trigger:
                    sl, moved_to_be = entry_price, True
            else:
                if low[j] <= sl:
                    exit_i, exit_reason = j, "breakeven" if moved_to_be else "stop"
                    break
                if high[j] >= tp:
                    exit_i, exit_reason = j, "target"
                    break
                if not moved_to_be and high[j] >= be_trigger:
                    sl, moved_to_be = entry_price, True
            if max_hold_bars is not None and (j - entry_i) >= max_hold_bars:
                exit_i, exit_reason = j, "max_hold"
                break
            j += 1
        if exit_i is None:
            exit_i, exit_reason = n - 1, "data_end"

        if exit_reason in ("stop", "breakeven"):
            raw_exit = sl
        elif exit_reason == "target":
            raw_exit = tp
        else:
            raw_exit = close[exit_i]
        cost = raw_exit * half_cost_frac
        exit_price = raw_exit + cost if direction == -1 else raw_exit - cost

        ret = (
            (entry_price - exit_price) / entry_price
            if direction == -1
            else (exit_price - entry_price) / entry_price
        )

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
                "moved_to_be": moved_to_be,
            }
        )

    return pd.DataFrame(trades)
