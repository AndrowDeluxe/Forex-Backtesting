"""asia_ote signal engine (chat 2026-08-21). Produces the signal/prev_high/
prev_low/atr/vwap/session contract for strategy.backtest.simulate_trades
(same pattern as gold_smc_htf_ltf), from the Asia-range Fibonacci/premium-
discount mechanics in levels.py.

Entry variants (`entry_variant`):
  "fib_limit"       - resting limit at a Fib ratio (premium_ratio for
                       sells, 1-premium_ratio for buys), fires the first
                       bar (within the active window after 06:00) whose
                       wick reaches that price - the closest vectorised
                       approximation of a real limit fill available
                       without a dedicated pending-order engine.
  "candle_reaction"  - only the 06:00 candle's OWN close is checked
                        against the ratio; fires immediately (next bar's
                        open) if it already qualifies, no waiting.
  "range_breakout"   - CLOSE beyond asia_high/asia_low (confirmed close,
                        not just a wick) - the "starke Asia Session,
                        direkter Ausbruch" case, ASB-style.

Direction (`direction_mode`):
  "trend_strength" - gold_smc_htf_ltf.trend indicator on `trend_df`
                      (H1/H4 EURUSD, timeframe-agnostic), sampled as-of
                      each day's 06:00 bar.
  "prev_asia"       - yesterday's own Asia-session bias (c0600_ratio vs
                       0.5 the PRIOR day) - a disclosed interpretation of
                       "vorherige Asia Session" (chat 2026-08-21), not the
                       only possible reading.

Target (`target_mode`):
  "untested_asia"  - nearest previous day's un-mitigated Asia high/low.
  "monthly_pivot"  - nearest un-mitigated monthly pivot level (PP/R1/R2
                      for buys, PP/S1/S2 for sells).

Caveat shared with continuation.py/reversal_cascade.py: the chosen target
price is forward-filled across the M15 index (not frozen at entry) - a
trade that holds into the NEXT day's own setup will see that day's target
instead, a disclosed approximation, not a bug. Cap max_hold_bars to limit
how much this can matter."""

import numpy as np
import pandas as pd

from gold_smc_htf_ltf.trend import TREND_INDICATORS
from strategy.indicators import compute_adx

from .levels import ASIA_END, compute_daily_asia_levels, compute_monthly_pivots, daily_pivot_levels, fib_price, untested_asia_targets

_TREND_KWARGS = {
    "ema_cross": lambda fast, slow, adx_min: dict(fast=fast, slow=slow),
    "adx_di": lambda fast, slow, adx_min: dict(adx_min=adx_min),
    "donchian": lambda fast, slow, adx_min: dict(),
    "ema_adx_combo": lambda fast, slow, adx_min: dict(fast=fast, slow=slow, adx_min=adx_min),
}


def _nearest_pivot_above(entry_price: float, piv_row: pd.Series) -> float:
    candidates = [piv_row[k] for k in ("pp", "r1", "r2") if pd.notna(piv_row[k]) and piv_row[k] > entry_price]
    return min(candidates) if candidates else np.nan


def _nearest_pivot_below(entry_price: float, piv_row: pd.Series) -> float:
    candidates = [piv_row[k] for k in ("pp", "s1", "s2") if pd.notna(piv_row[k]) and piv_row[k] < entry_price]
    return max(candidates) if candidates else np.nan


def _direction_by_day_trend(daily_index, trend_df, m15_tz, trend_indicator, trend_fast, trend_slow, trend_adx_min) -> pd.Series:
    trend_fn = TREND_INDICATORS[trend_indicator]
    kwargs = _TREND_KWARGS[trend_indicator](trend_fast, trend_slow, trend_adx_min)
    trend_series = trend_fn(trend_df, **kwargs)
    trend_series.index = trend_df.index
    trend_sorted = trend_series.sort_index()

    out = pd.Series(index=daily_index, dtype=float)
    for day in daily_index:
        ts = pd.Timestamp(day).tz_localize(m15_tz) + pd.Timedelta(hours=6)
        pos = trend_sorted.index.searchsorted(ts, side="right") - 1
        out[day] = trend_sorted.iloc[pos] if pos >= 0 else 0
    return out


def run_pipeline(
    m15_df: pd.DataFrame,
    d1_df: pd.DataFrame,
    trend_df: pd.DataFrame | None = None,
    entry_variant: str = "fib_limit",
    premium_ratio: float = 0.718,
    direction_mode: str = "trend_strength",
    trend_indicator: str = "ema_adx_combo",
    trend_fast: int = 20,
    trend_slow: int = 50,
    trend_adx_min: float = 20.0,
    target_mode: str = "untested_asia",
    min_target_distance_atr: float = 1.0,
    entry_window_end_hour: float = 12.0,
    atr_n: int = 14,
) -> pd.DataFrame:
    daily = compute_daily_asia_levels(m15_df)
    monthly_piv = compute_monthly_pivots(d1_df)
    piv_by_day = daily_pivot_levels(daily.index, monthly_piv)
    untested = untested_asia_targets(daily)

    if direction_mode == "trend_strength":
        if trend_df is None:
            raise ValueError("direction_mode='trend_strength' braucht trend_df")
        direction_by_day = _direction_by_day_trend(daily.index, trend_df, m15_df.index.tz, trend_indicator, trend_fast, trend_slow, trend_adx_min)
    elif direction_mode == "prev_asia":
        prev_ratio = daily["c0600_ratio"].shift(1)
        direction_by_day = pd.Series(np.where(prev_ratio > 0.5, 1, np.where(prev_ratio < 0.5, -1, 0)), index=daily.index)
    else:
        raise ValueError(f"unknown direction_mode {direction_mode!r}")

    discount_ratio = 1.0 - premium_ratio

    setup_rows = []
    for day in daily.index:
        d = int(direction_by_day.get(day, 0) or 0)
        if d == 0:
            continue
        row = daily.loc[day]
        asia_low, asia_high = row["asia_low"], row["asia_high"]

        if d == 1:
            stop = asia_low
            trigger = fib_price(asia_low, asia_high, discount_ratio) if entry_variant in ("fib_limit", "candle_reaction") else asia_high
        else:
            stop = asia_high
            trigger = fib_price(asia_low, asia_high, premium_ratio) if entry_variant in ("fib_limit", "candle_reaction") else asia_low

        if target_mode == "untested_asia":
            target = untested.loc[day, "untested_high"] if d == 1 else untested.loc[day, "untested_low"]
        elif target_mode == "monthly_pivot":
            piv_row = piv_by_day.loc[day]
            target = _nearest_pivot_above(trigger, piv_row) if d == 1 else _nearest_pivot_below(trigger, piv_row)
        else:
            raise ValueError(f"unknown target_mode {target_mode!r}")

        setup_rows.append({"date": day, "direction": d, "stop": stop, "trigger": trigger, "target": target})

    setups = pd.DataFrame(setup_rows).set_index("date") if setup_rows else pd.DataFrame(columns=["direction", "stop", "trigger", "target"])

    m15 = m15_df.copy()
    m15 = compute_adx(m15, n=atr_n)
    # KEIN taeglicher Session-Reset (anders als cls_advanced.py) - Setups
    # koennen mehrtaegig halten (Ziel = entfernter Pivot/untested-Level,
    # nicht ein Intraday-Zeitfenster), max_hold_bars steuert die Laufzeit.
    m15["session"] = 0

    idx = m15.index
    berlin_idx = idx.tz_convert("Europe/Berlin") if idx.tz is not None else idx
    date_key = pd.Series(berlin_idx.date, index=idx)
    hour = berlin_idx.hour + berlin_idx.minute / 60.0

    m15["_direction"] = date_key.map(setups["direction"]) if not setups.empty else np.nan
    m15["_stop"] = date_key.map(setups["stop"]) if not setups.empty else np.nan
    m15["_trigger"] = date_key.map(setups["trigger"]) if not setups.empty else np.nan
    m15["_target"] = date_key.map(setups["target"]) if not setups.empty else np.nan
    m15["_direction"] = m15["_direction"].fillna(0)

    active_window = (hour >= ASIA_END) & (hour < entry_window_end_hour)
    has_target = m15["_target"].notna()
    valid_dist = (m15["_target"] - m15["_trigger"]).abs() >= min_target_distance_atr * m15["atr"]

    if entry_variant == "fib_limit":
        touch_long = (m15["_direction"] == 1) & (m15["low"] <= m15["_trigger"])
        touch_short = (m15["_direction"] == -1) & (m15["high"] >= m15["_trigger"])
        fire = active_window & has_target & valid_dist & (touch_long | touch_short)
    elif entry_variant == "candle_reaction":
        is_0600_bar = (hour >= ASIA_END) & (hour < ASIA_END + 0.25)
        qualifies_long = (m15["_direction"] == 1) & (m15["close"] <= m15["_trigger"])
        qualifies_short = (m15["_direction"] == -1) & (m15["close"] >= m15["_trigger"])
        fire = is_0600_bar & has_target & valid_dist & (qualifies_long | qualifies_short)
    elif entry_variant == "range_breakout":
        break_long = (m15["_direction"] == 1) & (m15["close"] > m15["_trigger"])
        break_short = (m15["_direction"] == -1) & (m15["close"] < m15["_trigger"])
        fire = active_window & has_target & valid_dist & (break_long | break_short)
    else:
        raise ValueError(f"unknown entry_variant {entry_variant!r}")

    # Nur das ERSTE Feuern pro Tag zaehlt (Setup danach verbraucht).
    fire_np = fire.to_numpy().copy()
    date_np = date_key.to_numpy()
    seen = set()
    for i in range(len(fire_np)):
        if fire_np[i]:
            if date_np[i] in seen:
                fire_np[i] = False
            else:
                seen.add(date_np[i])
    fire = pd.Series(fire_np, index=m15.index)

    m15["signal"] = np.where(fire, m15["_direction"], 0).astype(int)

    m15["prev_low"] = m15["_stop"].where(m15["signal"] == 1).shift(1)
    m15["prev_high"] = m15["_stop"].where(m15["signal"] == -1).shift(1)
    m15["vwap"] = m15["_target"].ffill()

    return m15.drop(columns=["_direction", "_stop", "_trigger", "_target"])
