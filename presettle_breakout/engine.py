"""Pre-Settle Range Breakout (EUR/USD, M5) - user's own manual observation
(2026-08-10), tested here for the first time. Rules as specified by the
user, not derived from a paper:

- Range = highest high / lowest low from 06:00 Europe/Berlin (the
  "pre-settle" window already documented in strategy/cls_advanced.py's CLS
  Advanced framework) through the first local M5 swing high/low ("fractal")
  that forms AT OR AFTER 07:00 - a 3-bar pivot (high[j] > both neighbours,
  or low[j] < both neighbours), confirmed only once the following bar
  closes (no lookahead: at real time j+1, we can tell bar j was a local
  extremum). One trade per calendar day - if no such pivot forms before the
  entry cutoff, no trade that day. Matches the user's own chart illustration
  (2026-08-10): Pre-Settle range breaks, price forms its own local
  high/low in the following Settle window, and THAT point becomes the
  range's closing boundary.
- The instant the pivot is confirmed, arm a resting Buy-Stop at the range
  high and a Sell-Stop at the range low - whichever fills first wins, the
  other is never taken (same OCO convention as asian_range_breakout/engine.py).
- Stop-loss = 2x ATR(14) on M5, measured at the moment the range closes (the
  pivot's confirmation bar) - no lookahead, same snapshot convention as
  asian_range_breakout/cls_settle.py's ATR handling.
- Take-profit = fixed 1:2 risk/reward, i.e. 2x the stop distance.
- An order that hasn't filled by 12:00 Berlin is invalidated - no trade for
  that day, not carried over or filled late.

A fixed-clock-window mode (range_end_mode="fixed", the previous behavior)
is kept available for comparison - see range_end_mode below.

Deliberately a bespoke bar-by-bar engine, not strategy.backtest.simulate_trades
- same reasoning as every other resting-order breakout in this repo
  (asian_range_breakout/engine.py, asian_range_breakout/cls_settle.py):
  a resting OCO pair that can sit unfilled for hours isn't a single-bar
  signal with a one-shot SL/TP.

Fidelity choices, disclosed:
- Same-bar ambiguity (a bar's H-L range touches both the buy-stop and
  sell-stop level) is skipped, not resolved - the order pair stays resting
  for the next bar. Same convention as orb_strategy.py / asian_range_breakout.
- Entries fill at the literal stop level once touched (wick fill), not at
  the bar's open.
- A same-bar stop-out on the fill bar itself is checked and resolved
  conservatively as an immediate stop, not ignored (stop is checked before
  take-profit each bar).
- Costs: half the round-trip spread is charged against both entry and exit
  price (spread_bps, same round-trip-basis-points convention as
  strategy/backtest.py's BacktestConfig), applied on the correct side of
  the market.
- Pivot detection ("first_pivot" mode) never looks across a calendar-day
  boundary - a streak still trending at day end simply produces no trade
  that day, rather than borrowing the next day's bars as its confirmation.
"""

import numpy as np
import pandas as pd

from strategy.indicators import compute_atr


def _minutes(index: pd.DatetimeIndex) -> np.ndarray:
    return (index.hour * 60 + index.minute).to_numpy()


def _minutes_of(hhmm: str) -> int:
    t = pd.Timestamp(hhmm)
    return t.hour * 60 + t.minute


def _resolve_window(
    high: np.ndarray, low: np.ndarray, close: np.ndarray, times: pd.DatetimeIndex,
    minutes: np.ndarray, atr: np.ndarray,
    window_start: int, window_end: int, r_hi: float, r_lo: float,
    cutoff_min: int, atr_mult: float, rr: float, spread_bps: float, slippage_bps: float,
) -> tuple[dict, int] | None:
    """Shared fill + position-management logic for a single day's range
    (window_start..window_end already decided by the caller, either via a
    fixed clock window or the first-local-pivot search). Returns
    (trade_dict, exit_i) or None if no trade resulted."""
    n = len(times)
    if r_hi - r_lo <= 0:
        return None

    atr_val = atr[window_end]
    if np.isnan(atr_val) or atr_val <= 0:
        return None  # not enough M5 history yet for a real ATR(14)
    sl_dist = atr_mult * atr_val

    # --- wait for a clean single-direction fill, order invalidated at entry_cutoff ---
    entry_i, direction = None, 0
    j = window_end + 1
    while j < n:
        if minutes[j] >= cutoff_min:
            break  # unfilled by the cutoff - order invalidated, no trade today
        broke_up = high[j] >= r_hi
        broke_down = low[j] <= r_lo
        if broke_up and not broke_down:
            entry_i, direction = j, 1
            break
        if broke_down and not broke_up:
            entry_i, direction = j, -1
            break
        j += 1

    if entry_i is None:
        return None

    raw_entry = r_hi if direction == 1 else r_lo
    half_spread = raw_entry * spread_bps / 10_000 / 2
    slip = raw_entry * slippage_bps / 10_000
    entry_price = raw_entry + half_spread if direction == 1 else raw_entry - half_spread
    sl = raw_entry - sl_dist if direction == 1 else raw_entry + sl_dist
    tp = raw_entry + rr * sl_dist if direction == 1 else raw_entry - rr * sl_dist

    # --- manage the open position from entry_i onward: stop checked before tp ---
    exit_i, exit_price, exit_reason = None, None, None
    k = entry_i
    while k < n:
        hit_stop = (low[k] <= sl) if direction == 1 else (high[k] >= sl)
        hit_tp = (high[k] >= tp) if direction == 1 else (low[k] <= tp)
        if hit_stop:
            exit_price = sl - half_spread - slip if direction == 1 else sl + half_spread + slip
            exit_i, exit_reason = k, "stop"
            break
        if hit_tp:
            exit_price = tp - half_spread if direction == 1 else tp + half_spread
            exit_i, exit_reason = k, "take_profit"
            break
        k += 1

    if exit_i is None:
        exit_price = close[n - 1] - half_spread if direction == 1 else close[n - 1] + half_spread
        exit_i, exit_reason = n - 1, "data_end"

    return_pct = (
        (exit_price - entry_price) / entry_price
        if direction == 1
        else (entry_price - exit_price) / entry_price
    )
    trade = {
        "window_start": times[window_start],
        "window_end": times[window_end],
        "entry_time": times[entry_i],
        "exit_time": times[exit_i],
        "direction": "long" if direction == 1 else "short",
        "entry_price": entry_price,
        "exit_price": exit_price,
        "sl": sl,
        "tp": tp,
        "range_high": r_hi,
        "range_low": r_lo,
        "range_width": r_hi - r_lo,
        "atr_m5_at_entry": atr_val,
        "sl_distance": sl_dist,
        "return_pct": return_pct,
        "hold_bars": exit_i - entry_i,
        "exit_reason": exit_reason,
    }
    return trade, exit_i


def simulate_presettle_breakout(
    df: pd.DataFrame,
    range_start: str = "06:00",
    range_end: str = "08:30",
    range_end_mode: str = "first_pivot",
    pivot_after: str = "07:00",
    entry_cutoff: str = "12:00",
    atr_period: int = 14,
    atr_mult: float = 2.0,
    rr: float = 2.0,
    spread_bps: float = 0.3,
    slippage_bps: float = 0.0,
) -> pd.DataFrame:
    """df: M5 OHLC bars (lower-case columns), Europe/Berlin-local tz-aware
    index (see presettle_breakout/data.py::fetch_m5_berlin).

    range_end_mode: "first_pivot" (default) - range runs from range_start
    until the first confirmed local M5 swing high/low at or after
    pivot_after (see module docstring). "fixed" - the previous behavior,
    range runs from range_start until the fixed clock time range_end.
    """
    required = {"open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"simulate_presettle_breakout: missing columns {missing}")
    if range_end_mode not in ("first_pivot", "fixed"):
        raise ValueError(f"range_end_mode must be 'first_pivot' or 'fixed', got {range_end_mode!r}")

    start_min = _minutes_of(range_start)
    cutoff_min = _minutes_of(entry_cutoff)
    minutes = _minutes(df.index)

    atr = compute_atr(df, n=atr_period).to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    times = df.index
    n = len(df)

    trades = []

    if range_end_mode == "fixed":
        end_min = _minutes_of(range_end)
        in_window = (minutes >= start_min) & (minutes < end_min)
        i = 0
        while i < n:
            while i < n and not in_window[i]:
                i += 1
            if i >= n:
                break
            window_start = i
            while i < n and in_window[i]:
                i += 1
            window_end = i  # exclusive - first bar NOT in window (range just closed)
            if window_end >= n:
                break

            r_hi = high[window_start:window_end].max()
            r_lo = low[window_start:window_end].min()
            result = _resolve_window(
                high, low, close, times, minutes, atr,
                window_start, window_end, r_hi, r_lo,
                cutoff_min, atr_mult, rr, spread_bps, slippage_bps,
            )
            if result is None:
                continue
            trade, exit_i = result
            trades.append(trade)
            i = exit_i + 1
        return pd.DataFrame(trades)

    # --- range_end_mode == "first_pivot" ---
    pivot_after_min = _minutes_of(pivot_after)
    dates = df.index.date
    after_start = minutes >= start_min

    i = 0
    while i < n:
        while i < n and not after_start[i]:
            i += 1
        if i >= n:
            break
        window_start = i
        day = dates[window_start]
        day_end = window_start
        while day_end < n and dates[day_end] == day:
            day_end += 1  # exclusive end of this calendar day's bars

        # scan for the first confirmed local pivot (3-bar fractal) at/after
        # pivot_after - confirmed once the following bar (j+1) closes, so a
        # pivot at j is only usable once j+1 < day_end (never borrows the
        # next day's bars) and minutes[j] < cutoff_min (still worth arming
        # an order afterward).
        pivot_i, window_end = None, None
        j = window_start
        while j < day_end and minutes[j] < cutoff_min:
            if minutes[j] >= pivot_after_min and j - 1 >= window_start and j + 1 < day_end:
                is_high = high[j] > high[j - 1] and high[j] > high[j + 1]
                is_low = low[j] < low[j - 1] and low[j] < low[j + 1]
                if is_high or is_low:
                    pivot_i, window_end = j, j + 1
                    break
            j += 1

        if pivot_i is None:
            i = day_end
            continue

        r_hi = high[window_start : pivot_i + 1].max()
        r_lo = low[window_start : pivot_i + 1].min()
        result = _resolve_window(
            high, low, close, times, minutes, atr,
            window_start, window_end, r_hi, r_lo,
            cutoff_min, atr_mult, rr, spread_bps, slippage_bps,
        )
        if result is not None:
            trades.append(result[0])
        i = day_end  # one range/trade per day, regardless of outcome

    return pd.DataFrame(trades)
