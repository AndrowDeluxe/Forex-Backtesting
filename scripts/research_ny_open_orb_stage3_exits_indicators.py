"""Stage 3 - exit/indicator grid on top of the entry types that showed any
promise in Stage 2 (stop_breakout was the clear standout, OOS Sharpe 0.84 on
the 15-min range; confirmed_retest and fractal_reversal were marginal but
positive OOS; limit_in_range was net negative in 3 of 4 IS/OOS x range_bars
slices and is not carried forward here). All sweeps report OOS only
(>=2021-07-28, matching Stage 2's split) - the honest half, not pooled.

Grid:
- stop_atr_mult x target_r_mult (fixed R-multiple target).
- target_mode="range_multiple" (multiple of the opening-range width itself,
  the "High-Low-Range-Indikator" the user asked for) vs. the R-multiple target.
- ADX filter (>=25 at entry, same threshold orb_strategy/pipeline.py's
  confirmed Nasdaq/SP500 finding already uses).
- Relative-Volume-at-Time entry filter (>= threshold) and early-exit
  (< threshold), the new indicator in ny_open_orb/indicators.py.
"""

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

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
    oos_index = frame.index[frame.index >= split_ts]
    s = summarize(oos_trades, oos_index)
    s["avg_r"] = oos_trades["r_multiple"].mean()
    return s


def _print_row(label: str, s: dict | None):
    if s is None:
        print(f"{label:>42} keine Trades (OOS)")
        return
    print(
        f"{label:>42} n={s['n_trades']:>4} sharpe={s['sharpe']:>6.2f} pf={s['profit_factor']:>5.2f} "
        f"win={s['win_rate']:>6.1%} avg_r={s['avg_r']:>6.2f} cagr={s['cagr']:>7.1%} maxdd={s['max_drawdown']:>7.1%}"
    )


def filter_by_adx(entries: pd.DataFrame, frame: pd.DataFrame, adx_min: float) -> pd.DataFrame:
    adx_at_entry = frame.loc[entries["entry_time"], "adx"].to_numpy()
    return entries[adx_at_entry >= adx_min]


def filter_by_rvol(entries: pd.DataFrame, frame: pd.DataFrame, rvol_min: float) -> pd.DataFrame:
    rvol_at_entry = frame.loc[entries["entry_time"], "rvol_at_time"].to_numpy()
    return entries[rvol_at_entry >= rvol_min]


def sweep_entry_type(frame: pd.DataFrame, entry_type: str, split_ts: pd.Timestamp):
    print(f"\n--- {entry_type} ---")
    base_entries = find_entries(frame, entry_type)

    print("\n  stop_atr_mult x target_r_mult (structural stop off, ADX/RVOL filters off):")
    for stop_atr_mult in (1.0, 1.5, 2.0):
        for target_r_mult in (2.0, 3.0, 4.0, 6.0):
            trades = simulate(frame, base_entries, stop_atr_mult=stop_atr_mult, target_mode="r_multiple", target_r_mult=target_r_mult)
            _print_row(f"stop={stop_atr_mult}x atr, target={target_r_mult}R", oos_summary(frame, trades, split_ts))

    print("\n  target_mode=range_multiple (High-Low-Range-Indikator) x target_range_mult (stop=1.5x atr):")
    for target_range_mult in (1.0, 2.0, 3.0, 4.0):
        trades = simulate(frame, base_entries, stop_atr_mult=1.5, target_mode="range_multiple", target_range_mult=target_range_mult)
        _print_row(f"target={target_range_mult}x orb_width", oos_summary(frame, trades, split_ts))

    print("\n  stop_mode=structural (opposite ORB boundary, falls back to ATR) x target_r_mult:")
    for target_r_mult in (2.0, 3.0, 4.0):
        trades = simulate(frame, base_entries, stop_mode="structural", stop_atr_mult=1.5, target_mode="r_multiple", target_r_mult=target_r_mult)
        _print_row(f"structural stop, target={target_r_mult}R", oos_summary(frame, trades, split_ts))

    print("\n  ADX entry filter (best fixed exit so far: stop=1.5x atr, target=4R):")
    for adx_min in (None, 20.0, 25.0, 30.0):
        entries = base_entries if adx_min is None else filter_by_adx(base_entries, frame, adx_min)
        trades = simulate(frame, entries, stop_atr_mult=1.5, target_mode="r_multiple", target_r_mult=4.0)
        _print_row(f"adx_min={adx_min}", oos_summary(frame, trades, split_ts))

    print("\n  RVOL@time entry filter (same fixed exit):")
    for rvol_min in (None, 0.8, 1.0, 1.2):
        entries = base_entries if rvol_min is None else filter_by_rvol(base_entries, frame, rvol_min)
        trades = simulate(frame, entries, stop_atr_mult=1.5, target_mode="r_multiple", target_r_mult=4.0)
        _print_row(f"rvol_min={rvol_min}", oos_summary(frame, trades, split_ts))

    print("\n  RVOL@time early-exit (same fixed exit + entry, exit if RVOL@time drops below threshold):")
    for rvol_exit_min in (None, 0.3, 0.5, 0.7):
        trades = simulate(frame, base_entries, stop_atr_mult=1.5, target_mode="r_multiple", target_r_mult=4.0, rvol_exit_min=rvol_exit_min)
        _print_row(f"rvol_exit_min={rvol_exit_min}", oos_summary(frame, trades, split_ts))


def main():
    m15 = fetch_sp500_m15(START, END)
    m5 = fetch_sp500_m5(START, END)
    frame = build_frame(m15, m5, range_bars=1)
    split_ts = pd.Timestamp(SPLIT_DATE, tz=frame.index.tz)

    for entry_type in ("stop_breakout", "confirmed_retest", "fractal_reversal"):
        sweep_entry_type(frame, entry_type, split_ts)


if __name__ == "__main__":
    main()
