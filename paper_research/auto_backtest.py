"""Generic backtest executor for `complexity == "simple_signal"` specs only.

Deliberately NOT a reuse of `strategy/backtest.py::simulate_trades` -- that
engine's stop/target logic (prev-session-extreme trigger, VWAP target) is
specific to the ADX-VWAP paper's own thesis, not a generic shape that fits an
arbitrary extracted indicator-threshold strategy. Since the paper's exact
stop/target rule arrives as unstructured free text (`exit_rule_text`), not a
structured field, this module uses an explicitly-labelled generic ATR
stop/target instead of pretending to reconstruct the paper's real exit -- an
honest approximation, not the paper's literal rule.

`stateful` specs (anything needing multi-bar state beyond single-bar
indicator conditions) are NOT run here -- see spec.py's docstring. Forcing
those through this generic engine would silently misrepresent the paper.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from strategy.indicators import compute_adx, compute_vwap_and_deviation
from paper_research.spec import StrategySpec, StructuredCondition

SUPPORTED_INDICATORS = {"open", "high", "low", "close", "atr", "adx", "vwap", "deviation"}


class UnsupportedSpecError(ValueError):
    """Raised when a spec can't be run through this generic engine -- e.g.
    stateful complexity, ambiguous direction, or a condition referencing an
    indicator this repo doesn't compute. Callers should catch this and store
    it as `backtest_error` rather than let it propagate."""


@dataclass
class GenericBacktestConfig:
    stop_atr_mult: float = 1.0
    target_r_multiple: float = 2.0  # target = stop distance * this multiple
    max_hold_bars: int = 50
    spread_bps: float = 0.3


def build_indicator_columns(df: pd.DataFrame) -> pd.DataFrame:
    """OHLCV (lowercase columns, datetime index) -> OHLCV + vwap/deviation/atr/adx.
    Reuses strategy.indicators unmodified -- same VWAP/ADX/ATR computation as
    every other strategy module in this repo."""
    df = compute_vwap_and_deviation(df)
    df = compute_adx(df)
    return df


def _evaluate_condition(df: pd.DataFrame, cond: StructuredCondition) -> pd.Series:
    if cond.indicator not in SUPPORTED_INDICATORS or cond.indicator not in df.columns:
        raise UnsupportedSpecError(f"condition references unsupported indicator '{cond.indicator}'")
    series = df[cond.indicator]

    if cond.op in ("<", "<=", ">", ">="):
        try:
            threshold = float(cond.value)
        except ValueError as exc:
            raise UnsupportedSpecError(
                f"condition op '{cond.op}' needs a numeric value, got '{cond.value}'"
            ) from exc
        return {
            "<": series < threshold,
            "<=": series <= threshold,
            ">": series > threshold,
            ">=": series >= threshold,
        }[cond.op]

    # crosses_above / crosses_below: value is either a numeric level or another indicator column
    try:
        level = float(cond.value)
        other = pd.Series(level, index=df.index)
    except ValueError:
        if cond.value not in SUPPORTED_INDICATORS or cond.value not in df.columns:
            raise UnsupportedSpecError(
                f"crossing condition references unsupported indicator '{cond.value}'"
            )
        other = df[cond.value]

    prev_series, prev_other = series.shift(1), other.shift(1)
    if cond.op == "crosses_above":
        return (prev_series <= prev_other) & (series > other)
    return (prev_series >= prev_other) & (series < other)  # crosses_below


def generate_signal(df: pd.DataFrame, spec: StrategySpec) -> pd.Series:
    """AND-combines all entry_conditions; +1/-1 per `spec.direction`.
    Only "long" or "short" are supported -- "both" would need separate
    long/short condition sets the extraction schema doesn't carry, so it's
    treated the same as an unsupported indicator: flagged, not guessed."""
    if spec.direction not in ("long", "short"):
        raise UnsupportedSpecError(f"direction '{spec.direction}' not supported by the generic engine")
    if not spec.entry_conditions:
        raise UnsupportedSpecError("simple_signal spec has no entry_conditions to evaluate")

    trigger = pd.Series(True, index=df.index)
    for cond in spec.entry_conditions:
        trigger &= _evaluate_condition(df, cond)

    direction_value = 1 if spec.direction == "long" else -1
    return pd.Series(np.where(trigger, direction_value, 0), index=df.index)


def simulate_generic_trades(
    df: pd.DataFrame, signal: pd.Series, config: GenericBacktestConfig = GenericBacktestConfig()
) -> pd.DataFrame:
    """One-at-a-time, next-bar-open entry, symmetric ATR stop/target, time
    exit fallback. See module docstring for why this isn't `strategy.backtest.simulate_trades`."""
    n = len(df)
    open_, close, atr = df["open"].to_numpy(), df["close"].to_numpy(), df["atr"].to_numpy()
    sig = signal.to_numpy()
    times = df.index
    half_cost_frac = config.spread_bps / 10_000 / 2

    trades = []
    i = 0
    while i < n - 1:
        direction = int(sig[i])
        if direction == 0 or np.isnan(atr[i]) or atr[i] <= 0:
            i += 1
            continue

        entry_i = i + 1
        raw_entry = open_[entry_i]
        cost = raw_entry * half_cost_frac
        entry_price = raw_entry - cost if direction == -1 else raw_entry + cost

        stop_dist = config.stop_atr_mult * atr[entry_i]
        target_dist = stop_dist * config.target_r_multiple
        stop_level = entry_price - direction * stop_dist
        target_level = entry_price + direction * target_dist

        exit_i, exit_reason = None, None
        j = entry_i
        while j < n:
            if direction == 1 and close[j] <= stop_level:
                exit_i, exit_reason = j, "stop"
                break
            if direction == -1 and close[j] >= stop_level:
                exit_i, exit_reason = j, "stop"
                break
            if direction == 1 and close[j] >= target_level:
                exit_i, exit_reason = j, "target"
                break
            if direction == -1 and close[j] <= target_level:
                exit_i, exit_reason = j, "target"
                break
            if (j - entry_i) >= config.max_hold_bars:
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
            }
        )
        i = exit_i + 1

    return pd.DataFrame(trades)


def run_auto_backtest(
    raw_df: pd.DataFrame, spec: StrategySpec, config: GenericBacktestConfig = GenericBacktestConfig()
) -> pd.DataFrame:
    """raw_df: OHLCV, lowercase columns, datetime index. Raises UnsupportedSpecError
    if the spec can't honestly be run through this generic engine -- callers
    should catch that and record it as `backtest_error`, not swallow it."""
    if spec.complexity != "simple_signal":
        raise UnsupportedSpecError(f"complexity '{spec.complexity}' requires manual reconstruction")

    df = build_indicator_columns(raw_df)
    signal = generate_signal(df, spec)
    return simulate_generic_trades(df, signal, config)
