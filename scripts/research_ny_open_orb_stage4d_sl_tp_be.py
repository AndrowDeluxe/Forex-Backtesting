"""Stage 4d - refined SL/TP/breakeven grid on stop_breakout/SP500, OOS-only.
Stage 3 already found stop=1.0xATR/target=4R as the best simple fixed
config; this stage adds the piece Stage 3 didn't test yet: moving the stop
to breakeven once a trade shows some profit (ny_open_orb.engine.simulate's
new `breakeven_trigger_r` field, same convention as
strategy/backtest.py::BacktestConfig), swept jointly with stop/target.
"""

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from ny_open_orb import filters, regime
from ny_open_orb.data import fetch_sp500_m15, fetch_sp500_m5
from ny_open_orb.engine import build_frame, find_entries, simulate
from strategy.metrics import summarize

warnings.filterwarnings("ignore")
pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

START, END = "2016-07-28", "2026-07-28"
SPLIT_DATE = "2021-07-28"


def oos_summary(frame: pd.DataFrame, trades: pd.DataFrame, split_ts: pd.Timestamp) -> dict | None:
    oos_trades = trades[trades["entry_time"] >= split_ts] if not trades.empty else trades
    if oos_trades.empty:
        return None
    s = summarize(oos_trades, frame.index[frame.index >= split_ts])
    return s


def report(label: str, s: dict | None):
    if s is None:
        print(f"{label:>48} keine Trades (OOS)")
        return
    print(f"{label:>48} n={s['n_trades']:>4} sharpe={s['sharpe']:>6.2f} pf={s['profit_factor']:>5.2f} win={s['win_rate']:>6.1%} cagr={s['cagr']:>7.1%} maxdd={s['max_drawdown']:>7.1%}")


def main():
    m15 = fetch_sp500_m15(START, END)
    m5 = fetch_sp500_m5(START, END)
    frame = build_frame(m15, m5, range_bars=1)
    split_ts = pd.Timestamp(SPLIT_DATE, tz=frame.index.tz)
    # Stage 4b2's upgrade (long-only + EMA-neutral) - the new leading config,
    # not the raw Stage 2/3 baseline - SL/TP/BE gets tuned on top of it.
    all_entries = find_entries(frame, "stop_breakout")
    long_entries = filters.filter_by_direction(all_entries, 1)
    bias = regime.ema_trend_bias(m15, frame["session"].unique())
    bias_vals = filters.values_at(long_entries, bias)
    entries = filters.filter_by_category(long_entries, bias_vals, (0.0,))

    print("--- Breakeven-Trigger x (stop=1.0x ATR, target=4R) ---")
    for be_trigger in (None, 0.5, 1.0, 1.5, 2.0):
        trades = simulate(frame, entries, stop_atr_mult=1.0, target_mode="r_multiple", target_r_mult=4.0, breakeven_trigger_r=be_trigger)
        report(f"be_trigger={be_trigger}", oos_summary(frame, trades, split_ts))

    print("\n--- Breakeven-Trigger x stop_atr_mult (target=4R) ---")
    for stop_atr_mult in (1.0, 1.5, 2.0):
        for be_trigger in (None, 1.0, 1.5):
            trades = simulate(frame, entries, stop_atr_mult=stop_atr_mult, target_mode="r_multiple", target_r_mult=4.0, breakeven_trigger_r=be_trigger)
            report(f"stop={stop_atr_mult}x be_trigger={be_trigger}", oos_summary(frame, trades, split_ts))

    print("\n--- Breakeven-Trigger x target_r_mult (stop=1.0x ATR) ---")
    for target_r_mult in (2.0, 3.0, 4.0, 6.0):
        for be_trigger in (None, 1.0):
            trades = simulate(frame, entries, stop_atr_mult=1.0, target_mode="r_multiple", target_r_mult=target_r_mult, breakeven_trigger_r=be_trigger)
            report(f"target={target_r_mult}R be_trigger={be_trigger}", oos_summary(frame, trades, split_ts))

    print("\n--- Feineres stop_atr_mult-Grid um 1.0 herum (target=4R, kein BE) ---")
    for stop_atr_mult in (0.6, 0.8, 1.0, 1.2, 1.4):
        trades = simulate(frame, entries, stop_atr_mult=stop_atr_mult, target_mode="r_multiple", target_r_mult=4.0)
        report(f"stop={stop_atr_mult}x", oos_summary(frame, trades, split_ts))

    print("\n--- Feineres target_r_mult-Grid um 4 herum (stop=1.0x, kein BE) ---")
    for target_r_mult in (3.5, 4.0, 4.5, 5.0, 5.5):
        trades = simulate(frame, entries, stop_atr_mult=1.0, target_mode="r_multiple", target_r_mult=target_r_mult)
        report(f"target={target_r_mult}R", oos_summary(frame, trades, split_ts))


if __name__ == "__main__":
    main()
