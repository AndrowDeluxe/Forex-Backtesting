"""Event-driven reconstruction of the Fabio Valentini Auction Market
Playbook, rebuilt to track the source PDF's own framing as closely as
possible: **one** underlying phenomenon - price breaking out of the
reference balance (the previous calendar day's value area) - that forks
into two complementary outcomes:

- The breakout **fails and reclaims** back inside balance quickly -> Setup 2,
  Mean Reversion (fade back toward the balance POC).
- The breakout **holds and extends** -> Setup 1, Trend Continuation (ride it
  toward... the *same* balance POC as a continuation target, per the
  source's own Step 5 for both setups).

This replaces the first draft's separate, ATR-displacement-based "is the
market in balance" heuristic for the Trend setup - the source never gives
such a formula, and re-deriving both setups from one shared value-area
breakout is both simpler and textually closer to how the PDF presents them
as two sides of the same coin, not two independently-triggered systems.

Every remaining numeric choice not given in the source is called out where
it's used below. Two are structural and worth flagging up front:
- **Aggression** is read from real per-candle taker buy/sell volume
  (Binance, see data.py), not tick-by-tick footprint reading as the source
  describes - a disclosed data-availability compromise, not a modelling
  choice.
- **"1-2 tick" stop buffer**: Binance's actual BTCUSDT tick size is $0.01 -
  literally 1-2 ticks on a $60-100k instrument is economically meaningless
  (no real slippage protection). The source's tick sizing is calibrated to
  ES/NASDAQ futures, where a tick is a meaningful fraction of a typical
  stop distance. An ATR-scaled buffer is used instead as the crypto
  equivalent of "a small deliberate buffer beyond the level", not a literal
  unit conversion.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from auction_playbook.indicators import build_daily_reference_cache, lvn_prices, tag_sessions, volume_profile
from strategy.indicators import compute_atr


@dataclass
class PlaybookConfig:
    reclaim_window: int = 24         # bars allowed for a breakout to reclaim before it's treated as "holding" (Trend candidate)
    impulse_extension_grace: int = 6  # bars with no new extreme before an extending impulse leg is considered "done" and frozen
    max_leg_bars: int = 96           # hard cap on how long an extending impulse is tracked before forcing a freeze
    retest_window: int = 24          # bars to watch for the LVN retest once a leg is frozen
    aggression_z: float = 1.5        # delta must exceed this many std-devs to count as "aggression" / a "big print"
    delta_std_window: int = 96
    stop_buffer_atr_mult: float = 0.1  # crypto-equivalent of the source's "1-2 tick buffer" - see module docstring
    breakeven_delta_z: float = 2.0   # cumulative in-trade CVD pressure (Trend setup only, per the source) that moves the stop to breakeven
    max_hold_bars: int = 48          # safety time-exit (source gives no explicit time cap)
    risk_per_trade: float = 0.0025   # 0.25%, the source's low end
    num_bins: int = 24


def _prepare(df: pd.DataFrame, cfg: PlaybookConfig) -> pd.DataFrame:
    out = df.copy()
    out["atr"] = compute_atr(out, n=14)
    out = out.join(tag_sessions(out.index))
    out["delta_std"] = out["delta"].rolling(cfg.delta_std_window, min_periods=cfg.delta_std_window // 2).std()
    out["date"] = out.index.date
    return out


def _aggression_ok(delta: float, delta_std: float, direction: int, cfg: PlaybookConfig) -> bool:
    if pd.isna(delta_std) or delta_std <= 0:
        return False
    z = delta / delta_std
    return (direction == 1 and z >= cfg.aggression_z) or (direction == -1 and z <= -cfg.aggression_z)


def _touches(price_level: float, low: float, high: float) -> bool:
    return low <= price_level <= high


def _simulate_exit(
    direction, entry_i, entry_price, stop, target, high, low, close, delta, delta_std, n, cfg,
    allow_breakeven: bool, counter_aggression_exit: bool,
):
    """Bar-by-bar exit walk.

    `allow_breakeven`: the source only mentions moving the stop to
    breakeven on strong CVD pressure for the Trend setup - Mean Reversion
    is instead explicit that the stop should *never* widen (breakeven
    isn't technically a widening, but the source simply doesn't describe
    it there, so it's left out to avoid inventing a rule).

    `target`: a fixed price target (Mean Reversion's balance POC), or
    `None` when there isn't one (Trend Continuation - see module docstring
    and `counter_aggression_exit` below).

    `counter_aggression_exit`: Trend Continuation only. The source's own
    worked example exits not at a fixed POC (which the user confirmed,
    after this was flagged as contradicting Setup 1's "seek NEW balance"
    framing, should NOT be used as the exit rule) but when opposing
    aggression appears ("sellers appear with aggression... trade is
    exited to protect profits") - implemented as the same per-bar
    aggression z-score check used for entries, now checked against the
    *opposite* direction.
    """
    exit_i, exit_reason = None, None
    stop_level = stop
    moved_to_breakeven = False
    cum_delta = 0.0
    j = entry_i
    limit = min(n, entry_i + cfg.max_hold_bars)
    while j < limit:
        if allow_breakeven and not moved_to_breakeven and j > entry_i:
            cum_delta += delta[j - 1]
            bars_in_trade = j - entry_i
            std_j = delta_std[j] if not np.isnan(delta_std[j]) else delta_std[entry_i]
            if std_j and std_j > 0:
                agg_z = cum_delta / (std_j * np.sqrt(bars_in_trade))
                if (direction == 1 and agg_z >= cfg.breakeven_delta_z) or (direction == -1 and agg_z <= -cfg.breakeven_delta_z):
                    candidate = entry_price
                    if (direction == 1 and candidate > stop_level) or (direction == -1 and candidate < stop_level):
                        stop_level = candidate
                        moved_to_breakeven = True

        if direction == 1 and low[j] <= stop_level:
            exit_i, exit_reason = j, "breakeven_stop" if moved_to_breakeven else "stop"
            break
        if direction == -1 and high[j] >= stop_level:
            exit_i, exit_reason = j, "breakeven_stop" if moved_to_breakeven else "stop"
            break

        if target is not None:
            if direction == 1 and high[j] >= target:
                exit_i, exit_reason = j, "target"
                break
            if direction == -1 and low[j] <= target:
                exit_i, exit_reason = j, "target"
                break

        if counter_aggression_exit and j > entry_i and _aggression_ok(delta[j], delta_std[j], -direction, cfg):
            exit_i, exit_reason = j, "counter_aggression"
            break

        j += 1
    if exit_i is None:
        exit_i, exit_reason = min(n - 1, entry_i + cfg.max_hold_bars - 1), "max_hold"

    if "stop" in exit_reason:
        exit_price = stop_level
    elif exit_reason == "target":
        exit_price = target
    else:
        exit_price = close[exit_i]  # counter_aggression or max_hold
    ret = (exit_price - entry_price) / entry_price if direction == 1 else (entry_price - exit_price) / entry_price
    risk_frac = abs(entry_price - stop) / entry_price
    r_multiple = ret / risk_frac if risk_frac > 0 else float("nan")
    return exit_i, exit_reason, exit_price, ret, r_multiple


def generate_playbook_trades(df: pd.DataFrame, cfg: PlaybookConfig = PlaybookConfig()) -> pd.DataFrame:
    """Single unified state machine. States: `idle` (price inside the
    reference value area) -> `tracking` (price broke out, watching whether
    it reclaims or holds) -> `awaiting_retest` (leg frozen, watching for the
    LVN pullback + aggression trigger). Session filters (NY for Trend,
    London for Reversion) are applied at the entry-trigger bar, matching
    "use this setup when..." - the point a trader would actually be
    watching for the confluence, not at breakout detection.
    """
    d = _prepare(df, cfg)
    n = len(d)
    open_, high, low, close, atr = (d[c].to_numpy() for c in ("open", "high", "low", "close", "atr"))
    delta, delta_std = d["delta"].to_numpy(), d["delta_std"].to_numpy()
    in_ny, in_london = d["in_ny_session"].to_numpy(), d["in_london_session"].to_numpy()
    dates = d["date"].to_numpy()
    daily_ref_cache = build_daily_reference_cache(d)

    trades = []
    state = "idle"
    excursion_start = None
    breakout_dir = 0
    leg_extreme_i = None
    awaiting = None  # {"mode": "trend"|"reversion", "lvns": [...], "target": float, "direction": int, "failed_extreme": float|None, "wait_start": int}
    i = cfg.delta_std_window

    while i < n - 1:
        prior_day = (pd.Timestamp(dates[i]) - pd.Timedelta(days=1)).date()
        ref = daily_ref_cache.get(prior_day)
        if ref is None:
            state, excursion_start, breakout_dir, awaiting = "idle", None, 0, None
            i += 1
            continue
        va_low, va_high, poc = ref["va_low"], ref["va_high"], ref["poc"]

        if state == "idle":
            if high[i] > va_high:
                excursion_start, breakout_dir, leg_extreme_i, state = i, 1, i, "tracking"
            elif low[i] < va_low:
                excursion_start, breakout_dir, leg_extreme_i, state = i, -1, i, "tracking"
            i += 1
            continue

        if state == "tracking":
            if breakout_dir == 1 and high[i] > high[leg_extreme_i]:
                leg_extreme_i = i
            elif breakout_dir == -1 and low[i] < low[leg_extreme_i]:
                leg_extreme_i = i

            reclaimed = (breakout_dir == 1 and close[i] <= va_high) or (breakout_dir == -1 and close[i] >= va_low)
            bars_elapsed = i - excursion_start

            if reclaimed and bars_elapsed <= cfg.reclaim_window:
                reclaim_leg = d.iloc[excursion_start : i + 1]
                failed_extreme = high[leg_extreme_i] if breakout_dir == 1 else low[leg_extreme_i]
                lvns = lvn_prices(volume_profile(reclaim_leg, cfg.num_bins))
                if lvns:
                    awaiting = {
                        "mode": "reversion", "lvns": lvns, "target": poc, "direction": -breakout_dir,
                        "failed_extreme": failed_extreme, "wait_start": i,
                    }
                    state = "awaiting_retest"
                else:
                    state, breakout_dir = "idle", 0
                i += 1
                continue

            if not reclaimed:
                stalled = (i - leg_extreme_i) >= cfg.impulse_extension_grace and bars_elapsed > cfg.reclaim_window
                capped = bars_elapsed >= cfg.max_leg_bars
                if stalled or capped:
                    leg = d.iloc[excursion_start : i + 1]
                    lvns = lvn_prices(volume_profile(leg, cfg.num_bins))
                    if lvns:
                        awaiting = {
                            "mode": "trend", "lvns": lvns, "target": poc, "direction": breakout_dir,
                            "failed_extreme": None, "wait_start": i,
                        }
                        state = "awaiting_retest"
                    else:
                        state, breakout_dir = "idle", 0
                elif bars_elapsed >= cfg.max_leg_bars * 2:
                    state, breakout_dir = "idle", 0  # safety valve - never froze into a valid leg
                i += 1
                continue

            # reclaimed but past the reclaim window without having been caught above (edge case) - drop it
            state, breakout_dir = "idle", 0
            i += 1
            continue

        # state == "awaiting_retest"
        if i - awaiting["wait_start"] > cfg.retest_window:
            state, awaiting = "idle", None
            continue

        mode, direction, lvns, target = awaiting["mode"], awaiting["direction"], awaiting["lvns"], awaiting["target"]
        session_ok = in_ny[i] if mode == "trend" else in_london[i]
        touched = session_ok and any(_touches(lvn, low[i], high[i]) for lvn in lvns)

        if touched and _aggression_ok(delta[i], delta_std[i], direction, cfg):
            if mode == "trend":
                stop_ref = min(lvns, key=lambda p: abs(p - close[i]))
            else:
                stop_ref = awaiting["failed_extreme"]
            stop = stop_ref - cfg.stop_buffer_atr_mult * atr[i] if direction == 1 else stop_ref + cfg.stop_buffer_atr_mult * atr[i]

            entry_i = i + 1
            entry_price = open_[entry_i]
            stop_valid = (direction == 1 and stop < entry_price) or (direction == -1 and stop > entry_price)
            # Trend Continuation has no fixed price target (see module docstring: the source's own
            # "target the previous balance POC" is behind the trade once a continuation leg has
            # actually formed, and the user confirmed to follow the worked example's counter-
            # aggression exit instead). Mean Reversion keeps its POC target, which doesn't have
            # this problem (reclaiming back toward the balance center is the fade direction).
            entry_target = target if mode == "reversion" else None
            target_favorable = mode == "trend" or (direction == 1 and target > entry_price) or (direction == -1 and target < entry_price)
            if not (stop_valid and target_favorable):
                state, awaiting = "idle", None
                i += 1
                continue

            exit_i, exit_reason, exit_price, ret, r_multiple = _simulate_exit(
                direction, entry_i, entry_price, stop, entry_target, high, low, close, delta, delta_std, n, cfg,
                allow_breakeven=(mode == "trend"), counter_aggression_exit=(mode == "trend"),
            )
            trades.append(
                {
                    "setup": "trend_continuation" if mode == "trend" else "mean_reversion",
                    "entry_time": d.index[entry_i], "exit_time": d.index[exit_i], "direction": direction,
                    "entry_price": entry_price, "exit_price": exit_price, "stop": stop, "target": target,
                    "return_pct": ret, "r_multiple": r_multiple, "exit_reason": exit_reason, "hold_bars": exit_i - entry_i,
                }
            )
            i = exit_i + 1
            state, awaiting = "idle", None
            continue
        i += 1

    return pd.DataFrame(trades)
