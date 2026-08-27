"""Does checking the stop against the bar's HIGH/LOW (intrabar) instead of
only its CLOSE fix the mechanism identified as the common root cause behind
two independent negative findings this session - the Kelly blowup
(research_orb_kelly_sizing.py: OOS avg_loss_r = -1.54R/-1.16R, well past the
nominal -1R) and the failed drawdown throttle (research_orb_drawdown_
adaptive_sizing.py: the worst drawdown happens too fast for a reactive
throttle to catch)?

strategy/backtest.py::simulate_trades checks `close[j] > stop_level` (short)
/ `close[j] < stop_level` (long) bar-by-bar - a fast M15 bar can open below
open, gap or spike through the stop intrabar, and close back above it
without the stop ever firing that bar; the position then keeps riding,
sometimes into a materially worse loss before a LATER bar's close finally
confirms the breach. Checking `high[j]`/`low[j]` instead would catch the
breach the moment it happens, at the cost of being a more optimistic fill
(no slippage modelled beyond the existing spread convention, same
simplification used everywhere else in this project).

This is a standalone reimplementation of simulate_trades's exact loop
(entry lag, session-rollover exit, cost model) with only the stop-check
mechanism swapped - NOT a change to strategy/backtest.py itself, which is
shared by many other strategies in this repo. Promoting this to the shared
engine (e.g. an `intrabar_stop: bool` field on BacktestConfig) would only
make sense after seeing whether it actually helps here.

Grid: stop_atr_mult in {1.0, 1.5, 2.0 (current), 2.5, 3.0} x
{close-only, intrabar} stop-check, on the confirmed baseline (long_only +
ADX>=25 + per-asset weekday filter), Out-of-Sample (2021-2026) only - that
is the honest half, and the one where the R-multiple overshoot problem was
actually found."""

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from combined_strategy.data import fetch_timeframe
from orb_strategy.pipeline import run_orb_pipeline
from research_orb_kelly_sizing import capital_demo, kelly_stats
from strategy.metrics import summarize

warnings.filterwarnings("ignore")
pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

START, END = "2016-07-28", "2026-07-28"
SPLIT = "2021-07-28"
WEEKDAY_FILTER = {"NASDAQ": "Thursday", "SP500": "Monday"}


def _lower_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})


def simulate_trades_custom(df: pd.DataFrame, spread_bps: float, stop_atr_mult: float, intrabar_stop: bool, min_atr: float = 1e-12) -> pd.DataFrame:
    """Mirrors strategy/backtest.py::simulate_trades exactly (entry lag,
    session-rollover exit, spread cost model), with ONE change: when
    intrabar_stop=True, the stop is checked against high[j]/low[j] instead
    of close[j], and an intrabar-triggered stop fills AT the stop level
    (not at that bar's close) - everything else (session_end/data_end exits
    still fill at close) is unchanged."""
    required = {"open", "high", "low", "close", "vwap", "atr", "prev_high", "prev_low", "signal", "session"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"missing columns {missing}")

    n = len(df)
    open_, high, low, close = (df[c].to_numpy() for c in ("open", "high", "low", "close"))
    atr = df["atr"].to_numpy()
    prev_high, prev_low = df["prev_high"].to_numpy(), df["prev_low"].to_numpy()
    signal = df["signal"].to_numpy()
    session_codes = pd.factorize(df["session"].to_numpy())[0]
    times = df.index

    half_cost_frac = spread_bps / 10_000 / 2
    trades = []
    i = 0
    while i < n - 1:
        sig = signal[i]
        if sig == 0 or np.isnan(atr[i]) or atr[i] < min_atr:
            i += 1
            continue

        direction = int(sig)
        entry_i = i + 1
        entry_session = session_codes[entry_i]

        raw_entry = open_[entry_i]
        cost = raw_entry * half_cost_frac
        entry_price = raw_entry - cost if direction == -1 else raw_entry + cost

        trigger_level = prev_high[entry_i] if direction == -1 else prev_low[entry_i]
        stop_level = trigger_level + stop_atr_mult * atr[entry_i] if direction == -1 else trigger_level - stop_atr_mult * atr[entry_i]

        exit_i, exit_reason, fill_price = None, None, None
        j = entry_i
        while j < n:
            if session_codes[j] != entry_session:
                exit_i, exit_reason = max(j - 1, entry_i), "session_end"
                break
            if intrabar_stop:
                if direction == -1 and high[j] > stop_level:
                    exit_i, exit_reason, fill_price = j, "stop", stop_level
                    break
                if direction == 1 and low[j] < stop_level:
                    exit_i, exit_reason, fill_price = j, "stop", stop_level
                    break
            else:
                if direction == -1 and close[j] > stop_level:
                    exit_i, exit_reason = j, "stop"
                    break
                if direction == 1 and close[j] < stop_level:
                    exit_i, exit_reason = j, "stop"
                    break
            j += 1
        if exit_i is None:
            exit_i, exit_reason = n - 1, "data_end"

        raw_exit = fill_price if fill_price is not None else close[exit_i]
        cost = raw_exit * half_cost_frac
        exit_price = raw_exit + cost if direction == -1 else raw_exit - cost

        ret = (entry_price - exit_price) / entry_price if direction == -1 else (exit_price - entry_price) / entry_price

        trades.append({
            "entry_time": times[entry_i], "exit_time": times[exit_i], "direction": direction,
            "entry_price": entry_price, "exit_price": exit_price, "return_pct": ret,
            "exit_reason": exit_reason, "hold_bars": exit_i - entry_i,
            "atr_at_entry": atr[entry_i],
        })
        i = exit_i + 1

    return pd.DataFrame(trades)


def _r_multiples(trades: pd.DataFrame, stop_atr_mult: float) -> np.ndarray:
    stop_frac = stop_atr_mult * trades["atr_at_entry"] / trades["entry_price"]
    return (trades["return_pct"] / stop_frac).to_numpy()


def run_asset(name: str, df: pd.DataFrame):
    print(f"\n{'=' * 22} {name} {'=' * 22}")
    # atr_mult=1.0 threshold + baseline entry filters, shared across the whole grid -
    # only the STOP mechanism/distance varies below.
    signaled = run_orb_pipeline(df, atr_n=14, atr_mult=1.0, long_only=True, adx_min=25.0, exclude_weekday=WEEKDAY_FILTER[name])
    split_ts = pd.Timestamp(SPLIT, tz=signaled.index.tz)
    oos_signaled = signaled[signaled.index >= split_ts]

    print(f"\n{'stop_atr_mult':>13} {'check':>10} {'n':>4} {'sharpe':>7} {'pf':>6} {'win':>7} {'avg_win_R':>10} {'avg_loss_R':>11} {'payoff_b':>9} {'kelly_f':>8} {'half_kelly_end':>15}")
    for stop_atr_mult in [1.0, 1.5, 2.0, 2.5, 3.0]:
        for check_label, intrabar in [("close", False), ("intrabar", True)]:
            trades = simulate_trades_custom(signaled, spread_bps=0.3, stop_atr_mult=stop_atr_mult, intrabar_stop=intrabar)
            oos_trades = trades[trades["entry_time"] >= split_ts] if not trades.empty else trades
            if oos_trades.empty:
                print(f"{stop_atr_mult:>13.1f} {check_label:>10}   keine Trades")
                continue
            s = summarize(oos_trades, oos_signaled.index)
            r = _r_multiples(oos_trades, stop_atr_mult)
            k = kelly_stats(r)
            # half-Kelly capital demo needs the SAME stop_atr_mult used to derive r - capital_demo() from
            # research_orb_kelly_sizing.py hardcodes STOP_ATR_MULT=2.0, so only run it for that grid point.
            half_kelly_end = "-"
            if stop_atr_mult == 2.0 and k["half_kelly_f"] == k["half_kelly_f"] and k["half_kelly_f"] > 0:
                half_kelly_end = f"{capital_demo(oos_trades, k['half_kelly_f'])['end_equity']:,.0f}"
            print(
                f"{stop_atr_mult:>13.1f} {check_label:>10} {s['n_trades']:>4} {s['sharpe']:>7.2f} {s['profit_factor']:>6.2f} "
                f"{s['win_rate']:>6.1%} {k['avg_win_r']:>10.2f} {k['avg_loss_r']:>11.2f} {k['payoff_ratio_b']:>9.2f} "
                f"{k['kelly_f']:>7.1%} {half_kelly_end:>15}"
            )


def main():
    print("Loading NASDAQ + SP500 M15 ...")
    run_asset("NASDAQ", _lower_ohlcv(fetch_timeframe("NASDAQ", "M15", START, END)))
    run_asset("SP500", _lower_ohlcv(fetch_timeframe("SP500", "M15", START, END)))


if __name__ == "__main__":
    main()
