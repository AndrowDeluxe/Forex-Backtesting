"""CLS Practical Playbook (EUR/USD, M5 entries) - user's mentor's discretionary
framework (source: CLS_Praxis_Playbook.pdf, Smartmoneyhour/SMT Macro Desk,
uploaded 2026-08-10), rebuilt as a quantitative ruleset per the spec agreed
with the user in that conversation (2026-08-11). NOT a validated strategy
from the source - the source deck is explicitly training/journaling material
(a "Fake Charts" practice exercise, a 10-day live testsheet), not a system
the mentor has himself backtested. Every numeric threshold below is OUR
invented translation of the deck's discretionary color-coded checks, not a
number the source material gives - flagged inline, meant to be swept/
validated, not trusted as-is.

Timing (Europe/Berlin, unchanged from strategy/cls_advanced.py, which this
module reuses for the structural half of the decision):
- Asia Range: 00:00-06:00 (ASIA_START/ASIA_END)
- Settle window (break forms here): 06:00-09:00 (ASIA_END/SETTLE_END)
- Acceptance/quality check: 09:15 close (TEST_HOUR) -> holds_0915
- Post-settle/entry window: 09:30 (ENTRY_HOUR) through entry_cutoff (12:00)

Three filters, ALL must agree (AND, not majority - "kein Trade bei nicht
eindeutigen Regeln, Trend oder Filter-Ergebnissen", per the user):
- Trend: daily SMA(sma_window) on EUR/USD's own close (exact Gold-ASB
  convention), prior-day value only, no lookahead.
- Crosses: strategy.cls_advanced.compute_cross_confirmation - EUR/USD's
  06:00-09:00 move vs. the other 5 majors' average (broad-dollar move vs.
  isolated move). Reused as-is, per the user's choice.
- Rates: cls_practical.rates - BUND/USTBOND CFD "Ampel", a disclosed
  LONG-END duration proxy (see rates.py docstring), not the source's
  front-end/2y signal (no free intraday source for that exists).

Continuation: break holds at 09:15 + trend aligned with the break + rates
grün + crosses confirmed -> from 09:30, wait for the first confirmed M5
fractal AGAINST the break direction (the "pullback"), then a resting stop
order at that fractal bar's own high/low (long: buy back above the
pullback's high; short: sell back below its low) - the "pullback that
holds, then continuation" entry. SL = the pullback fractal's own extreme.

Reversal: break FAILS to hold at 09:15 + trend against the break + rates
rot + crosses NOT confirmed -> from 09:30, wait for price to close back
inside the Asia range ("Rückkehr"), then the first confirmed M5 fractal
AGAINST the original break direction ("Structure Shift"), then a resting
stop order breaking that fractal further in the reversal direction (the
"Retest" - price returns to test/break that fresh structure level; folding
retest+entry into one causal stop-order trigger is a disclosed
simplification, same idea as presettle_breakout's wick-fill convention).
SL = the original Settle-window sweep extreme ("SL über Sweep").

Anything else (any filter unclear/contradicting) -> No Trade.

Take-profit: two modes to compare, per the user's own instruction to test
ADR first -
- "adr": 0.35 x ADR(14) (identical calibration to
  asian_range_breakout/cls_settle.py's adr_mult, reused deliberately since
  the user asked for that same value here).
- "fixed_r": rr_fixed x the trade's own SL distance (e.g. 1:2).

Position sizing: account_size x risk_pct, divided by the trade's SL
distance in price, giving EUR notional units (EUR/USD: USD is the quote
currency, so this is a direct USD-per-price-unit conversion, no cross-rate
needed). Assumes account currency = USD - a disclosed assumption, not
given explicitly by the user. A trade whose structural SL distance is
tighter than min_sl_atr_mult x ATR(M5) is dropped entirely, not sized -
found 2026-08-11 that a 0.5-pip fractal separation (sub-noise, not a real
structural level) implied ~100 standard lots on a 100k account at 0.5%
risk, an unrealistic leverage the fixed-$-risk formula alone doesn't guard
against.

Costs: half round-trip spread charged on entry and exit (spread_bps, same
convention as strategy/backtest.py and presettle_breakout/engine.py).
"""

import numpy as np
import pandas as pd

from asian_range_breakout.cls_settle import compute_adr
from cls_practical.rates import classify_rates_ampel, compute_rate_support_score
from strategy.cls_advanced import (
    ASIA_END,
    ENTRY_HOUR,
    SETTLE_END,
    compute_cross_confirmation,
    compute_daily_features,
    to_berlin,
)
from strategy.indicators import compute_atr


def _minutes_of(hhmm: str) -> int:
    t = pd.Timestamp(hhmm)
    return t.hour * 60 + t.minute


def trend_bias(daily_close: pd.Series, sma_window: int = 200) -> pd.Series:
    """+1/-1 per day: prior day's close above/below its own prior SMA(sma_window)
    - exact Gold-ASB convention (asian_range_breakout/filters.py::attach_trend_bias),
    ported here since that helper filters an existing trades frame post-hoc,
    while this needs to gate the entry DECISION itself. NaN before sma_window
    days of history exist."""
    sma = daily_close.rolling(sma_window).mean()
    prior_close = daily_close.shift(1)
    prior_sma = sma.shift(1)
    bias = pd.Series(np.nan, index=daily_close.index)
    bias[prior_close > prior_sma] = 1
    bias[prior_close <= prior_sma] = -1
    return bias


def _day_segments(dates_arr: np.ndarray) -> list[tuple[object, int, int]]:
    """[(day, start_i, end_i_exclusive), ...] in one O(n) pass."""
    n = len(dates_arr)
    if n == 0:
        return []
    change = np.where(dates_arr[1:] != dates_arr[:-1])[0] + 1
    starts = np.concatenate(([0], change))
    ends = np.concatenate((change, [n]))
    return list(zip(dates_arr[starts], starts, ends))


def _first_fractal(high, low, minutes, i_start, i_end_excl, cutoff_min, kind):
    """First confirmed 3-bar M5 fractal of `kind` ("high"/"low") at index
    j in [i_start, i_end_excl), confirmed once bar j+1 closes (no lookahead).
    Returns (pivot_i, confirm_i) or (None, None)."""
    j = max(i_start, 1)
    while j < i_end_excl - 1 and minutes[j] < cutoff_min:
        if j - 1 >= i_start:
            if kind == "high" and high[j] > high[j - 1] and high[j] > high[j + 1]:
                return j, j + 1
            if kind == "low" and low[j] < low[j - 1] and low[j] < low[j + 1]:
                return j, j + 1
        j += 1
    return None, None


def _continuation_trigger(high, low, minutes, i_start, i_end_excl, cutoff_min, direction, asia_high, asia_low):
    """Pullback fractal must still hold OUTSIDE the broken Asia-range level
    (deck: "Break hält außerhalb der Range" / DO: "Break außerhalb halten
    lassen") - a fractal that only forms after price has already retraced
    all the way back past the broken level doesn't count as "a pullback
    that holds", it's a failed break wearing a pullback's clothes. Keep
    searching later fractals within the same day until one qualifies."""
    fractal_kind = "low" if direction == 1 else "high"
    search_start = i_start
    while True:
        pivot_i, confirm_i = _first_fractal(high, low, minutes, search_start, i_end_excl, cutoff_min, fractal_kind)
        if pivot_i is None:
            return None
        still_outside = (low[pivot_i] > asia_high) if direction == 1 else (high[pivot_i] < asia_low)
        if still_outside:
            break
        search_start = pivot_i + 1

    trigger_level = high[pivot_i] if direction == 1 else low[pivot_i]
    sl_level = low[pivot_i] if direction == 1 else high[pivot_i]

    j = confirm_i
    while j < i_end_excl and minutes[j] < cutoff_min:
        if direction == 1 and high[j] >= trigger_level:
            return j, trigger_level, sl_level, pivot_i, None
        if direction == -1 and low[j] <= trigger_level:
            return j, trigger_level, sl_level, pivot_i, None
        j += 1
    return None


def _reversal_trigger(high, low, close, minutes, i_start, i_end_excl, cutoff_min, original_direction, asia_high, asia_low, sweep_level):
    """"Rückkehr in die Range" must be a genuine close back BETWEEN both
    Asia-range boundaries, not merely past the swept one - a close that
    only crosses the swept boundary can already be miles past the FAR
    boundary too (a runaway move straight through the whole range), which
    is a failed reversal / still-running continuation, not a "swept, came
    back, structure shift, retest" pattern. If price blows through to the
    opposite boundary before ever closing back inside, invalidate (no
    trade) rather than trigger on that already-extreme bar."""
    j = i_start
    return_i = None
    while j < i_end_excl and minutes[j] < cutoff_min:
        if asia_low < close[j] < asia_high:
            return_i = j
            break
        if original_direction == 1 and close[j] < asia_low:
            return None  # blew straight through to the far side - not a clean return
        if original_direction == -1 and close[j] > asia_high:
            return None
        j += 1
    if return_i is None:
        return None

    # 2. Structure Shift: first confirmed fractal against the original break
    fractal_kind = "low" if original_direction == 1 else "high"
    pivot_i, confirm_i = _first_fractal(high, low, minutes, return_i, i_end_excl, cutoff_min, fractal_kind)
    if pivot_i is None:
        return None
    trigger_level = low[pivot_i] if original_direction == 1 else high[pivot_i]

    # 3. Retest + entry: resting stop order breaking that fractal further
    j = confirm_i
    while j < i_end_excl and minutes[j] < cutoff_min:
        if original_direction == 1 and low[j] <= trigger_level:
            return j, trigger_level, sweep_level, pivot_i, return_i
        if original_direction == -1 and high[j] >= trigger_level:
            return j, trigger_level, sweep_level, pivot_i, return_i
        j += 1
    return None


def simulate_cls_practical(
    eurusd_m5: pd.DataFrame,
    other_majors_m15: dict[str, pd.DataFrame],
    bund_m5: pd.DataFrame,
    ustbond_m5: pd.DataFrame,
    sma_window: int = 100,
    rates_z_window: int = 60,
    rates_z_threshold: float = 0.0,
    adr_period: int = 14,
    tp_mode: str = "adr",
    adr_mult: float = 0.35,
    rr_fixed: float = 2.0,
    account_size: float = 100_000.0,
    risk_pct: float = 0.005,
    entry_cutoff: str = "12:00",
    spread_bps: float = 0.3,
    slippage_bps: float = 0.0,
    min_sl_atr_mult: float = 1.0,
    be_trigger_r: float | None = None,
    allowed_setups: tuple[str, ...] = ("continuation", "reversal"),
) -> pd.DataFrame:
    """Defaults updated 2026-08-11 after the threshold sweep + SL/TP
    diagnosis (scripts/research_cls_practical_threshold_sweep.py,
    scripts/research_cls_practical_sltp_diagnosis.py):
    - sma_window 200 -> 100: flat effect on win-rate, mildly better PF.
    - rates_z_threshold 0.5 -> 0.0: the magnitude threshold was cutting
      profitable trades without improving win-rate (0.0 strictly beat 0.5
      on trade count, PF, AND total PnL in the sweep) - Rates-Ampel now
      reduces to a pure sign check (grün/rot), no strength gate.
    - min_sl_atr_mult 0.5 -> 1.0: the 0.5 floor only screened out sub-noise
      degenerate stops; the diagnosis found win-rate scales with SL
      distance (eng-tercile 20% vs weit-tercile 42.9%), and 1.0x ATR is
      close to the overall sample's own median SL/ATR ratio (1.10) - a
      first, disclosed attempt to lean the trade selection toward
      "wide enough to be real structure", not degenerate noise avoidance.
    be_trigger_r: optional break-even move (None = disabled, unchanged
    default behavior) - once a trade is up be_trigger_r x its own SL
    distance, the stop moves to entry price. Same convention as
    asian_range_breakout/engine.py's be_trigger_r / checklist_strategy's
    breakeven_at_r. Checked before stop/tp each bar (conservative: a bar
    that reaches BE and reverses hard within the same bar scratches at
    breakeven, doesn't bank the wider original stop).
    allowed_setups: restrict which of "continuation"/"reversal" actually
    trade - e.g. ("reversal",) for the Reversal-only variant the user asked
    to test (diagnosis found reversal's win-rate ~2x continuation's)."""
    if tp_mode not in ("adr", "fixed_r"):
        raise ValueError(f"tp_mode must be 'adr' or 'fixed_r', got {tp_mode!r}")

    # --- daily decision layer ---
    daily = compute_daily_features(eurusd_m5)
    daily_by_pair = {"EURUSD": daily}
    for pair, df in other_majors_m15.items():
        daily_by_pair[pair] = compute_daily_features(df)
    cross_confirm = compute_cross_confirmation(daily_by_pair)["EURUSD"]

    berlin_idx = to_berlin(eurusd_m5.index)
    date_series = pd.Series(berlin_idx.date, index=eurusd_m5.index)
    daily_close = eurusd_m5["close"].groupby(date_series).last()
    trend = trend_bias(daily_close, sma_window=sma_window)

    rate_score = compute_rate_support_score(bund_m5, ustbond_m5)
    rates_ampel = classify_rates_ampel(rate_score, daily["direction"], z_window=rates_z_window, z_threshold=rates_z_threshold)

    adr = compute_adr(eurusd_m5, n=adr_period)
    m5_atr = compute_atr(eurusd_m5, n=adr_period).to_numpy()

    # --- M5 arrays for entry timing ---
    minutes = (eurusd_m5.index.hour * 60 + eurusd_m5.index.minute).to_numpy()
    dates_arr = berlin_idx.date
    high = eurusd_m5["high"].to_numpy()
    low = eurusd_m5["low"].to_numpy()
    close = eurusd_m5["close"].to_numpy()
    times = eurusd_m5.index
    n = len(eurusd_m5)
    cutoff_min = _minutes_of(entry_cutoff)
    entry_hour_min = int(ENTRY_HOUR * 60)

    risk_amount = account_size * risk_pct
    half_asia_end_min, half_settle_end_min = int(ASIA_END * 60), int(SETTLE_END * 60)

    trades = []
    for day, day_start, day_end in _day_segments(dates_arr):
        if day not in daily.index:
            continue
        row = daily.loc[day]
        direction = row["direction"]
        holds = row["holds_0915"]
        if direction == 0 or pd.isna(holds):
            continue

        t_val = trend.get(day, np.nan)
        r_flag = rates_ampel.get(day, "gelb")
        c_val = cross_confirm.get(day, np.nan)
        if pd.isna(t_val) or pd.isna(c_val):
            continue

        setup, setup_direction = None, 0
        if holds and t_val == direction and r_flag == "grün" and bool(c_val):
            setup, setup_direction = "continuation", direction
        elif (not holds) and t_val == -direction and r_flag == "rot" and not bool(c_val):
            setup, setup_direction = "reversal", -direction
        if setup is None or setup not in allowed_setups:
            continue

        entry_start_i = day_start
        while entry_start_i < day_end and minutes[entry_start_i] < entry_hour_min:
            entry_start_i += 1
        if entry_start_i >= day_end:
            continue

        if setup == "continuation":
            result = _continuation_trigger(
                high, low, minutes, entry_start_i, day_end, cutoff_min, setup_direction,
                row["asia_high"], row["asia_low"],
            )
        else:
            settle_mask_start = day_start
            while settle_mask_start < day_end and minutes[settle_mask_start] < half_asia_end_min:
                settle_mask_start += 1
            settle_mask_end = day_start
            while settle_mask_end < day_end and minutes[settle_mask_end] < half_settle_end_min:
                settle_mask_end += 1
            if settle_mask_end <= settle_mask_start:
                continue
            sweep_level = (
                high[settle_mask_start:settle_mask_end].max()
                if direction == 1
                else low[settle_mask_start:settle_mask_end].min()
            )
            result = _reversal_trigger(
                high, low, close, minutes, entry_start_i, day_end, cutoff_min,
                direction, row["asia_high"], row["asia_low"], sweep_level,
            )

        if result is None:
            continue
        entry_i, trigger_level, sl_level, pivot_i, return_i = result
        d = setup_direction
        sl_dist = abs(trigger_level - sl_level)
        atr_val_at_entry = m5_atr[entry_i] if entry_i < len(m5_atr) else np.nan
        min_sl_dist = min_sl_atr_mult * atr_val_at_entry if pd.notna(atr_val_at_entry) else np.nan
        if sl_dist <= 0 or pd.isna(min_sl_dist) or sl_dist < min_sl_dist:
            # a stop tighter than min_sl_atr_mult x ATR(M5) isn't a real
            # structural level - it's sub-noise separation between two
            # bars, and the risk_amount/sl_dist position-sizing formula
            # would blow up into unrealistic leverage for it (found
            # 2026-08-11: a 0.5-pip fractal separation implied ~100
            # standard lots on a 100k account at 0.5% risk).
            continue

        if tp_mode == "adr":
            adr_val = adr[day_start] if day_start < len(adr) else np.nan
            if pd.isna(adr_val) or adr_val <= 0:
                continue
            tp_dist = adr_mult * adr_val
        else:
            tp_dist = rr_fixed * sl_dist

        half_spread = trigger_level * spread_bps / 10_000 / 2
        slip = trigger_level * slippage_bps / 10_000
        entry_price = trigger_level + half_spread if d == 1 else trigger_level - half_spread
        sl = trigger_level - sl_dist if d == 1 else trigger_level + sl_dist
        tp = trigger_level + tp_dist if d == 1 else trigger_level - tp_dist

        current_sl = sl
        be_moved = False
        be_trigger_price = entry_price + be_trigger_r * sl_dist * d if be_trigger_r is not None else None

        exit_i, exit_price, exit_reason = None, None, None
        k = entry_i
        while k < n:
            if be_trigger_price is not None and not be_moved:
                reached_be = (high[k] >= be_trigger_price) if d == 1 else (low[k] <= be_trigger_price)
                if reached_be:
                    current_sl = entry_price
                    be_moved = True

            hit_stop = (low[k] <= current_sl) if d == 1 else (high[k] >= current_sl)
            hit_tp = (high[k] >= tp) if d == 1 else (low[k] <= tp)
            if hit_stop:
                exit_price = current_sl - half_spread - slip if d == 1 else current_sl + half_spread + slip
                exit_i, exit_reason = k, "breakeven" if be_moved else "stop"
                break
            if hit_tp:
                exit_price = tp - half_spread if d == 1 else tp + half_spread
                exit_i, exit_reason = k, "take_profit"
                break
            k += 1
        if exit_i is None:
            exit_price = close[n - 1] - half_spread if d == 1 else close[n - 1] + half_spread
            exit_i, exit_reason = n - 1, "data_end"

        return_pct = (
            (exit_price - entry_price) / entry_price if d == 1 else (entry_price - exit_price) / entry_price
        )
        units = risk_amount / sl_dist
        pnl_usd = units * d * (exit_price - entry_price)

        trades.append(
            {
                "date": day,
                "setup": setup,
                "direction": "long" if d == 1 else "short",
                "pivot_time": times[pivot_i],
                "return_time": times[return_i] if return_i is not None else pd.NaT,
                "entry_time": times[entry_i],
                "exit_time": times[exit_i],
                "entry_price": entry_price,
                "sl": sl,
                "tp": tp,
                "exit_price": exit_price,
                "exit_reason": exit_reason,
                "be_moved": be_moved,
                "sl_distance": sl_dist,
                "tp_mode": tp_mode,
                "trend_bias": t_val,
                "rates_ampel": r_flag,
                "cross_confirmed": bool(c_val),
                "units_eur": units,
                "risk_amount_usd": risk_amount,
                "pnl_usd": pnl_usd,
                "return_pct": return_pct,
                "hold_bars": exit_i - entry_i,
            }
        )

    return pd.DataFrame(trades)
