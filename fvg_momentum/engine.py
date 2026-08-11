"""Multi-Asset A/A+ Momentum Fair Value Gap strategy - honest rebuild against
REAL Dukascopy price data (see app_pages/fvg_momentum_writeup.py for why:
the source paper, Bindra 2025, discloses in its own Appendix A that its
"Trade Simulator ... simulates outcomes via deterministic hashing" applying
a pre-set win probability - NOT a real price-path simulation. Every one of
its 473 reported trades resolves to exactly +1.0R or -1.0R despite the
strategy's own spec including a TP2/runner-extension target that should
produce a spread of R-multiples. This module implements the same RULES
(momentum leg -> Fair Value Gap -> HTF confluence -> grading -> SL/TP) but
resolves every trade against actual M5 OHLC price action, the only way to
know whether the described edge is real.

Rule source: paper sections 2.2-2.6. Deliberate, disclosed resolutions of
ambiguities the source leaves underspecified:
- Setup grading (2.5) states A+ needs body-ratio >=0.70 while A only needs
  >=0.52 - but momentum-leg detection (2.2) ALREADY requires >=0.70 for
  every candle in the leg, so no trade could ever be gated at the >=0.52
  level. Grade is therefore assigned purely by HTF confluence presence
  (A+ = confluence, A = no confluence), the only reading consistent with
  2.2's own gate.
- Entry mechanics: the FVG midpoint is treated as a resting limit order,
  valid for the remainder of the 2-hour (24-bar) forward window from the
  momentum leg's close - if price never retraces into the gap, no trade
  (the source doesn't specify a fill mechanism either).
- Exit mechanics: SL at entry +/- 9 pips; once price reaches +9 pips (1R,
  matching the source's own "TP1 9 pips (Trail 1:1)"), stop moves to
  breakeven; target is TP2 (35 pips A+/20 pips A). No separate "Runner
  Extension" leg beyond TP2 is modelled - the source's own description of
  it is too vague to implement precisely, and TP2 already defines a
  concrete target.
- max_hold_bars is a disclosed safety cap (not part of the source spec) so
  a trade that never resolves doesn't hang open for days.
"""

import numpy as np
import pandas as pd

_ASIAN_START_UTC, _ASIAN_END_UTC = 0.0, 7.0  # matches the source's own session table (2.7)


def _utc_hour(index: pd.DatetimeIndex) -> np.ndarray:
    return (index.hour + index.minute / 60.0).to_numpy()


def _session_label(hour: float) -> str:
    if 8.0 <= hour < 11.0:
        return "London"
    if 13.0 <= hour < 15.0:
        return "Overlap"
    if 15.0 <= hour < 16.0:
        return "New York"
    if 0.0 <= hour < 7.0:
        return "Asian"
    return "Other"


def _htf_confluence(fvg_time, fvg_price: float, h1_levels: pd.DataFrame, pip_size: float, tolerance_pips: float) -> bool:
    pos = h1_levels.index.searchsorted(fvg_time, side="right") - 1
    if pos < 0:
        return False
    row = h1_levels.iloc[pos]
    tol = tolerance_pips * pip_size
    for level in (row["ema20"], row["ema50"], row["poc"]):
        if pd.notna(level) and abs(fvg_price - level) <= tol:
            return True
    return False


def simulate_fvg_momentum(
    m5: pd.DataFrame,
    h1_levels: pd.DataFrame,
    pip_size: float,
    body_ratio_min: float = 0.70,
    swing_lookback: int = 10,
    fvg_window_bars: int = 24,
    htf_tolerance_pips: float = 12.0,
    sl_pips: float = 9.0,
    tp2_pips_a: float = 20.0,
    tp2_pips_aplus: float = 35.0,
    max_hold_bars: int = 96,
) -> pd.DataFrame:
    required = {"Open", "High", "Low", "Close"}
    missing = required - set(m5.columns)
    if missing:
        raise ValueError(f"simulate_fvg_momentum: missing columns {missing}")

    open_ = m5["Open"].to_numpy()
    high = m5["High"].to_numpy()
    low = m5["Low"].to_numpy()
    close = m5["Close"].to_numpy()
    times = m5.index
    n = len(m5)

    body_ratio = np.abs(close - open_) / np.maximum(high - low, 1e-12)
    candle_dir = np.sign(close - open_)
    hour = _utc_hour(times)
    asian_excluded = (hour >= _ASIAN_START_UTC) & (hour < _ASIAN_END_UTC)

    sl_dist = sl_pips * pip_size

    trades = []
    streak_start = None
    streak_dir = 0
    i = 0
    while i < n:
        strong = body_ratio[i] >= body_ratio_min and candle_dir[i] != 0 and not asian_excluded[i]
        if not strong:
            streak_start, streak_dir = None, 0
            i += 1
            continue

        d = candle_dir[i]
        if streak_dir != d:
            streak_start, streak_dir = i, d
        streak_len = i - streak_start + 1

        if streak_len < 2:
            i += 1
            continue

        lb_start = max(0, streak_start - swing_lookback)
        lb_end = streak_start
        if lb_end <= lb_start:
            i += 1
            continue
        swing_high = high[lb_start:lb_end].max()
        swing_low = low[lb_start:lb_end].min()
        breached = (close[i] > swing_high) if d == 1 else (close[i] < swing_low)
        if not breached:
            i += 1
            continue

        # --- momentum leg confirmed at i; scan forward for a matching FVG ---
        leg_end = i
        scan_end = min(n, leg_end + 1 + fvg_window_bars)
        fvg_mid, fvg_idx = None, None
        for k in range(max(leg_end + 1, 2), scan_end):
            if d == 1 and high[k - 2] < low[k]:
                fvg_mid, fvg_idx = (high[k - 2] + low[k]) / 2, k
                break
            if d == -1 and low[k - 2] > high[k]:
                fvg_mid, fvg_idx = (low[k - 2] + high[k]) / 2, k
                break

        if fvg_mid is None:
            streak_start, streak_dir = None, 0
            i += 1
            continue

        # --- resting limit order at the FVG midpoint, valid until scan_end ---
        entry_idx = None
        for m in range(fvg_idx, scan_end):
            if low[m] <= fvg_mid <= high[m]:
                entry_idx = m
                break

        if entry_idx is None:
            streak_start, streak_dir = None, 0
            i = scan_end
            continue

        htf_ok = _htf_confluence(times[fvg_idx], fvg_mid, h1_levels, pip_size, htf_tolerance_pips)
        grade = "A+" if htf_ok else "A"
        tp2_dist = (tp2_pips_aplus if grade == "A+" else tp2_pips_a) * pip_size

        entry_price = fvg_mid
        sl_price = entry_price - d * sl_dist
        be_trigger_price = entry_price + d * sl_dist  # TP1 / 1R, matches source's "Trail 1:1"
        tp2_price = entry_price + d * tp2_dist

        current_sl = sl_price
        be_moved = False
        exit_idx, exit_price, exit_reason = None, None, None
        hold_end = min(n, entry_idx + max_hold_bars)
        for m in range(entry_idx, hold_end):
            if not be_moved:
                reached_be = (high[m] >= be_trigger_price) if d == 1 else (low[m] <= be_trigger_price)
                if reached_be:
                    current_sl = entry_price
                    be_moved = True
            hit_sl = (low[m] <= current_sl) if d == 1 else (high[m] >= current_sl)
            hit_tp2 = (high[m] >= tp2_price) if d == 1 else (low[m] <= tp2_price)
            if hit_sl:
                exit_idx, exit_price, exit_reason = m, current_sl, ("breakeven" if be_moved else "stop")
                break
            if hit_tp2:
                exit_idx, exit_price, exit_reason = m, tp2_price, "tp2"
                break
        if exit_idx is None:
            exit_idx = hold_end - 1
            exit_price = close[exit_idx]
            exit_reason = "time_exit"

        r_multiple = d * (exit_price - entry_price) / sl_dist

        trades.append(
            {
                "leg_start": times[streak_start],
                "leg_end": times[leg_end],
                "fvg_time": times[fvg_idx],
                "entry_time": times[entry_idx],
                "exit_time": times[exit_idx],
                "direction": "long" if d == 1 else "short",
                "grade": grade,
                "htf_aligned": htf_ok,
                "session": _session_label(hour[entry_idx]),
                "entry_price": entry_price,
                "sl_price": sl_price,
                "tp2_price": tp2_price,
                "exit_price": exit_price,
                "exit_reason": exit_reason,
                "r_multiple": r_multiple,
            }
        )
        streak_start, streak_dir = None, 0
        i = exit_idx + 1

    return pd.DataFrame(trades)
