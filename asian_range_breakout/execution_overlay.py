"""Execution-Overlay applied to the Gold Asian-Range Breakout, per Zarattini
& Pagani (2026), "Improving Performance with Fast Alphas": a signal that is
unprofitable to trade on its own can still carry genuine short-horizon
directional information usable purely as an EXECUTION TIMING filter on an
already-independently-profitable strategy - it doesn't touch signal
selection (still the same Asian-range breakout trigger), only WHEN the
already-decided trade actually fills.

Adaptation to M15 bars (the paper uses 5-min SPY bars + a separate 15-min
execution grid; we have neither a finer intrabar feed nor tick data here,
so the M15 bar itself stands in for both the "fast alpha" signal and the
execution grid - a disclosed resolution downgrade, not a like-for-like
replication):

  1. Detect the breakout trigger exactly like engine.py's entry_mode="wick"
     (first bar whose High/Low touches the range level).
  2. Do NOT fill there. Instead wait for the first subsequent bar that
     CLOSES against the breakout direction (a down-bar after a long
     trigger, an up-bar after a short trigger) - the M15-resolution stand-in
     for the paper's 5-min "streak-reversal" fast-alpha signal.
  3. Fill at that confirming bar's close.
  4. If no confirming bar appears before the session's exit_time, the trade
     is SKIPPED entirely (not filled at the original level) - the paper's
     own disclosed risk ("can miss entries in very strong, pullback-free
     trends"), carried over explicitly rather than silently falling back to
     the original wick fill.

Stop distance (sd) stays anchored to the original range width, same
convention as engine.py's entry_mode="close". Everything else (BE-move, TP,
time-exit, cost model) is copied unchanged from asian_range_breakout.engine
so any difference in results is attributable ONLY to the entry-timing
change, not to a drifted cost/exit model."""

import numpy as np
import pandas as pd

from strategy.indicators import compute_adx


def _ny_minutes(index: pd.DatetimeIndex) -> np.ndarray:
    return (index.hour * 60 + index.minute).to_numpy()


def _minutes_of(hhmm: str) -> int:
    t = pd.Timestamp(hhmm)
    return t.hour * 60 + t.minute


def _in_window(minutes: np.ndarray, start_min: int, end_min: int) -> np.ndarray:
    if start_min < end_min:
        return (minutes >= start_min) & (minutes < end_min)
    return (minutes >= start_min) | (minutes < end_min)


def simulate_asian_breakout_overlay(
    df: pd.DataFrame,
    range_start: str = "21:00",
    range_end: str = "01:00",
    exit_time: str = "11:00",
    stop_frac: float = 1.0,
    tp_r_mult: float | None = None,
    be_trigger_r: float | None = None,
    spread_price: float = 0.30,
    slippage_price: float = 0.10,
) -> pd.DataFrame:
    required = {"open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"simulate_asian_breakout_overlay: missing columns {missing}")

    start_min = _minutes_of(range_start)
    end_min = _minutes_of(range_end)
    exit_min = _minutes_of(exit_time)

    minutes = _ny_minutes(df.index)
    in_window = _in_window(minutes, start_min, end_min)

    adx_series = compute_adx(df)["adx"].to_numpy()

    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    times = df.index
    n = len(df)

    half_spread = spread_price / 2

    trades = []
    i = 0
    while i < n:
        while i < n and not in_window[i]:
            i += 1
        if i >= n:
            break
        window_start = i
        while i < n and in_window[i]:
            i += 1
        window_end = i
        if window_end >= n:
            break

        r_hi = high[window_start:window_end].max()
        r_lo = low[window_start:window_end].min()
        rng = r_hi - r_lo
        if rng <= 0:
            continue
        sd = stop_frac * rng

        # --- stage 1: detect the breakout trigger (identical to wick mode) ---
        trig_i, direction = None, 0
        j = window_end + 1
        while j < n:
            if minutes[j] >= exit_min:
                break
            broke_up = high[j] >= r_hi
            broke_down = low[j] <= r_lo
            if broke_up and not broke_down:
                trig_i, direction = j, 1
                break
            if broke_down and not broke_up:
                trig_i, direction = j, -1
                break
            j += 1

        if trig_i is None:
            i = window_end
            continue  # no breakout at all this window

        # --- stage 2: wait for the first counter-direction CLOSE after the trigger ---
        entry_i = None
        k = trig_i + 1
        while k < n:
            if minutes[k] >= exit_min:
                break
            is_counter_bar = (close[k] < close[k - 1]) if direction == 1 else (close[k] > close[k - 1])
            if is_counter_bar:
                entry_i = k
                break
            k += 1

        if entry_i is None:
            i = window_end
            continue  # no pullback confirmation before session end - overlay skips this trade entirely

        raw_entry = close[entry_i]
        entry_price = raw_entry + half_spread if direction == 1 else raw_entry - half_spread
        sl = raw_entry - sd if direction == 1 else raw_entry + sd
        current_sl = sl
        be_moved = False
        be_trigger_price = None
        if be_trigger_r is not None:
            be_trigger_price = raw_entry + be_trigger_r * sd if direction == 1 else raw_entry - be_trigger_r * sd
        tp = None
        if tp_r_mult is not None:
            tp = raw_entry + tp_r_mult * sd if direction == 1 else raw_entry - tp_r_mult * sd

        exit_i, exit_price, exit_reason = None, None, None
        m = entry_i
        while m < n:
            if not be_moved and be_trigger_price is not None:
                reached_be = (high[m] >= be_trigger_price) if direction == 1 else (low[m] <= be_trigger_price)
                if reached_be:
                    current_sl = entry_price
                    be_moved = True

            hit_stop = (low[m] <= current_sl) if direction == 1 else (high[m] >= current_sl)
            hit_tp = tp is not None and ((high[m] >= tp) if direction == 1 else (low[m] <= tp))
            at_exit_time = minutes[m] >= exit_min
            if hit_stop:
                exit_price = current_sl - half_spread - slippage_price if direction == 1 else current_sl + half_spread + slippage_price
                exit_i, exit_reason = m, "breakeven" if be_moved else "stop"
                break
            if hit_tp:
                exit_price = tp - half_spread if direction == 1 else tp + half_spread
                exit_i, exit_reason = m, "take_profit"
                break
            if at_exit_time:
                exit_price = close[m] - half_spread - slippage_price if direction == 1 else close[m] + half_spread + slippage_price
                exit_i, exit_reason = m, "time_exit"
                break
            m += 1

        if exit_i is None:
            exit_price = close[n - 1] - half_spread if direction == 1 else close[n - 1] + half_spread
            exit_i, exit_reason = n - 1, "data_end"

        return_pct = (
            (exit_price - entry_price) / entry_price
            if direction == 1
            else (entry_price - exit_price) / entry_price
        )
        trades.append(
            {
                "window_start": times[window_start],
                "window_end": times[window_end],
                "trigger_time": times[trig_i],
                "entry_time": times[entry_i],
                "exit_time": times[exit_i],
                "direction": "long" if direction == 1 else "short",
                "entry_price": entry_price,
                "exit_price": exit_price,
                "adx_at_entry": adx_series[window_end],
                "sl": sl,
                "be_moved": be_moved,
                "stop_distance": sd,
                "range_high": r_hi,
                "range_low": r_lo,
                "range_width": rng,
                "return_pct": return_pct,
                "hold_bars": exit_i - entry_i,
                "wait_bars": entry_i - trig_i,
                "exit_reason": exit_reason,
            }
        )
        i = exit_i + 1

    return pd.DataFrame(trades)
