"""Stage 4a's raw weekday breakdown was computed OOS-only, which is exactly
the kind of "try 5 weekdays, keep the best-looking one" search that risks a
coincidental hit (see knowledge/projects/ny-open-orb-sp500.md). This script
applies orb_strategy/pipeline.py's own honest methodology instead: rank
weekdays on the IS half (2016-07-28 to 2021-07-28) alone, then check whether
the weakest IS weekday is STILL a net negative/weak day on the untouched OOS
half (2021-2026) - a real out-of-sample confirmation, not a same-sample scan.
Long-only baseline throughout (Stage 4a's already-confirmed filter).
"""

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from ny_open_orb import filters
from ny_open_orb.data import fetch_sp500_m15, fetch_sp500_m5
from ny_open_orb.engine import build_frame, find_entries, simulate
from strategy.metrics import summarize

warnings.filterwarnings("ignore")
pd.set_option("display.width", 160)

START, END = "2016-07-28", "2026-07-28"
SPLIT_DATE = "2021-07-28"
EXIT_CFG = dict(stop_atr_mult=1.0, target_mode="r_multiple", target_r_mult=4.0)
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")


def summarize_slice(frame, entries, mask, split_ts, side):
    sub = entries[mask] if mask is not None else entries
    trades = simulate(frame, sub, **EXIT_CFG)
    if side == "IS":
        trades = trades[trades["entry_time"] < split_ts]
        idx = frame.index[frame.index < split_ts]
    else:
        trades = trades[trades["entry_time"] >= split_ts]
        idx = frame.index[frame.index >= split_ts]
    if trades.empty:
        return None
    return summarize(trades, idx)


def main():
    m15 = fetch_sp500_m15(START, END)
    m5 = fetch_sp500_m5(START, END)
    frame = build_frame(m15, m5, range_bars=1)
    split_ts = pd.Timestamp(SPLIT_DATE, tz=frame.index.tz)
    entries = filters.filter_by_direction(find_entries(frame, "stop_breakout"), 1)  # long-only, Stage 4a's confirmed filter

    print("IS (2016-07-28 to 2021-07-28) per-weekday ranking:")
    is_pf = {}
    for day in WEEKDAYS:
        day_entries = filters.filter_by_weekday(entries, include_only=[day])
        s = summarize_slice(frame, day_entries, None, split_ts, "IS")
        if s is None:
            print(f"  {day:>10}: keine Trades")
            continue
        is_pf[day] = s["profit_factor"]
        print(f"  {day:>10}: n={s['n_trades']:>3} sharpe={s['sharpe']:>6.2f} pf={s['profit_factor']:>5.2f} win={s['win_rate']:>6.1%}")

    weakest_day = min(is_pf, key=is_pf.get)
    print(f"\nSchwaechster IS-Wochentag: {weakest_day} (PF={is_pf[weakest_day]:.2f})")

    print(f"\nOOS-Bestaetigung: ist '{weakest_day}' auch OOS (2021-2026) schwach?")
    for label, day_filter in [("baseline (alle Tage)", None), (f"nur {weakest_day}", [weakest_day]), (f"ohne {weakest_day}", None)]:
        if label.startswith("nur"):
            day_entries = filters.filter_by_weekday(entries, include_only=day_filter)
        elif label.startswith("ohne"):
            day_entries = filters.filter_by_weekday(entries, exclude=[weakest_day])
        else:
            day_entries = entries
        s = summarize_slice(frame, day_entries, None, split_ts, "OOS")
        if s is None:
            print(f"  {label:>20}: keine Trades")
            continue
        print(f"  {label:>20}: n={s['n_trades']:>4} sharpe={s['sharpe']:>6.2f} pf={s['profit_factor']:>5.2f} win={s['win_rate']:>6.1%} cagr={s['cagr']:>7.1%}")


if __name__ == "__main__":
    main()
