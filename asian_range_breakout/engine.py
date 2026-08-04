"""Gold (XAUUSD) Asian-Range Breakout - state machine + trade simulator.

Source: user-supplied TradeStation EasyLanguage spec
(Gold_Asian_Breakout_Strategy.txt, 2026-08-04). Rules: build the Asian-
session high/low range (range_start-range_end, NY local time, wraps
midnight); the moment the window closes, arm a resting Buy-Stop at the
range high and Sell-Stop at the range low (OCO - first touched wins, the
other is never taken); stop distance = stop_frac x range width; NO
take-profit, the position rides until exit_time (flat-by, NY local time)
or the stop. One trade per window.

Deliberately a bespoke bar-by-bar engine, not strategy.backtest.simulate_trades
(that engine is single-bar-signal / one-shot SL-TP, doesn't model a resting
OCO order pair that can sit unfilled for hours, nor an overnight session
that spans midnight) - same reasoning as auction_playbook/checklist_strategy's
own bespoke engines elsewhere in this repo.

Fidelity choices, disclosed:
- Same-bar ambiguity (both stop levels touched within one bar's H-L range)
  is skipped, not resolved - the order stays resting for the next bar.
  Same convention as orb_strategy.py's "ambiguous bar" handling.
- Entries fill at the literal stop level once touched (not the bar's
  open), matching the EasyLanguage code's own "next bar at rHi stop"
  resting-order semantics.
- The flat-by time exit is approximated as filling at the CLOSE of the
  first bar whose NY-local time is >= exit_time (the EasyLanguage code's
  own "next bar at market" would fill one bar later, at that bar's open -
  a minor, disclosed simplification).
- A same-bar stop-out on the fill bar itself (rare: the fill bar's
  opposite extreme also breaches the freshly-set stop) is checked and
  resolved conservatively as an immediate stop, not ignored.
- Costs: half the round-trip spread is charged against both entry and
  exit price; slippage_price is charged additionally on stop/time-exit
  fills only (not on the range-level entry, which the source strategy's
  own "no gap between level and armed order" argument treats as precise).
"""

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


def simulate_asian_breakout(
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
    """tp_r_mult: optional take-profit, expressed as a multiple of the stop
    distance (R) - e.g. 1.5 means TP = entry +/- 1.5 x (stop distance). None
    (default) = no take-profit, matching the source strategy's literal
    "rides to time exit" rule. Added 2026-08-04 to test whether locking in
    profit earlier improves on the literal no-TP rule - NOT part of the
    original spec.

    be_trigger_r: optional break-even move, expressed as a multiple of the
    stop distance (R) - once the trade is up be_trigger_r x R, the stop
    moves to the entry price (same convention as the OU-Modell live bot's
    be_trigger_r and checklist_strategy's breakeven_at_r). None (default) =
    no break-even move, matching the source strategy's literal "fixed stop,
    never moved" rule - also NOT part of the original spec. Same-bar
    ambiguity (BE trigger reached, then price reverses hard within that
    same bar) is resolved conservatively: BE is checked/applied first, so
    such a bar scratches at breakeven rather than banking the wider
    original stop distance - same convention as checklist_strategy."""
    required = {"open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"simulate_asian_breakout: missing columns {missing}")

    start_min = _minutes_of(range_start)
    end_min = _minutes_of(range_end)
    exit_min = _minutes_of(exit_time)

    minutes = _ny_minutes(df.index)
    in_window = _in_window(minutes, start_min, end_min)

    # ADX on the M15 series itself, sampled at window_end (the bar the range
    # just closed on, i.e. the decision point BEFORE the order is armed) -
    # attached per trade for a post-hoc regime filter, no lookahead.
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
        window_end = i  # exclusive - first bar NOT in window (range just closed here)
        if window_end >= n:
            break

        r_hi = high[window_start:window_end].max()
        r_lo = low[window_start:window_end].min()
        rng = r_hi - r_lo
        if rng <= 0:
            continue
        sd = stop_frac * rng

        # --- wait for a clean single-direction fill, from window_end+1 onward ---
        entry_i, direction = None, 0
        j = window_end + 1
        while j < n:
            if minutes[j] >= exit_min:
                break  # order expired unfilled this window
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
            continue  # no trade this window - order expired unfilled

        raw_entry = r_hi if direction == 1 else r_lo
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

        # --- manage the open position from entry_i onward ---
        # Order per bar: BE trigger first (moves current_sl to entry_price),
        # then stop (against the possibly just-moved current_sl - a bar that
        # reaches BE and reverses hard within the same bar scratches at
        # breakeven, doesn't bank the wider original stop), then tp, then
        # time exit - same conservative convention as checklist_strategy.
        exit_i, exit_price, exit_reason = None, None, None
        k = entry_i
        while k < n:
            if not be_moved and be_trigger_price is not None:
                reached_be = (high[k] >= be_trigger_price) if direction == 1 else (low[k] <= be_trigger_price)
                if reached_be:
                    current_sl = entry_price
                    be_moved = True

            hit_stop = (low[k] <= current_sl) if direction == 1 else (high[k] >= current_sl)
            hit_tp = tp is not None and ((high[k] >= tp) if direction == 1 else (low[k] <= tp))
            at_exit_time = minutes[k] >= exit_min
            if hit_stop:
                exit_price = current_sl - half_spread - slippage_price if direction == 1 else current_sl + half_spread + slippage_price
                exit_i, exit_reason = k, "breakeven" if be_moved else "stop"
                break
            if hit_tp:
                exit_price = tp - half_spread if direction == 1 else tp + half_spread
                exit_i, exit_reason = k, "take_profit"
                break
            if at_exit_time:
                exit_price = close[k] - half_spread - slippage_price if direction == 1 else close[k] + half_spread + slippage_price
                exit_i, exit_reason = k, "time_exit"
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
        trades.append(
            {
                "window_start": times[window_start],
                "window_end": times[window_end],
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
                "exit_reason": exit_reason,
            }
        )
        i = exit_i + 1

    return pd.DataFrame(trades)


def get_latest_setup(
    df: pd.DataFrame,
    range_start: str = "21:00",
    range_end: str = "01:00",
    exit_time: str = "11:00",
    stop_frac: float = 1.0,
) -> dict | None:
    """Finds the MOST RECENT Asian-range window in df and reports its
    levels + current status (still waiting for a fill, filled and open, or
    expired unfilled) - a "what would the bot do right now" reading, kept
    separate from simulate_asian_breakout() which only returns fully closed
    historical trades. Returns None if df has no complete window yet."""

    start_min = _minutes_of(range_start)
    end_min = _minutes_of(range_end)
    exit_min = _minutes_of(exit_time)
    minutes = _ny_minutes(df.index)
    in_window = _in_window(minutes, start_min, end_min)

    window_end = None
    for i in range(len(df) - 1, 0, -1):
        if not in_window[i] and in_window[i - 1]:
            window_end = i
            break
    if window_end is None:
        return None

    window_start = window_end
    while window_start > 0 and in_window[window_start - 1]:
        window_start -= 1

    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    r_hi = float(high[window_start:window_end].max())
    r_lo = float(low[window_start:window_end].min())
    sd = stop_frac * (r_hi - r_lo)

    status, direction, entry_price = "wartet auf Füllung", None, None
    for j in range(window_end + 1, len(df)):
        if minutes[j] >= exit_min:
            status = "abgelaufen (kein Fill)"
            break
        broke_up = high[j] >= r_hi
        broke_down = low[j] <= r_lo
        if broke_up and not broke_down:
            direction, entry_price, status = "long", r_hi, "gefüllt (Long)"
            break
        if broke_down and not broke_up:
            direction, entry_price, status = "short", r_lo, "gefüllt (Short)"
            break

    return {
        "window_start": df.index[window_start],
        "window_end": df.index[window_end],
        "range_high": r_hi,
        "range_low": r_lo,
        "stop_distance": sd,
        "status": status,
        "direction": direction,
        "entry_price": entry_price,
        "last_bar_time": df.index[-1],
        "last_price": float(close[-1]),
    }
