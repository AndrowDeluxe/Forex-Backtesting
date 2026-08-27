"""NASDAQ-specific calibration, Stage 2+3 combined (entry-type comparison +
exit grid) - Stage 4e showed the SP500-derived filter does NOT generalize to
NASDAQ (OOS Sharpe 0.59 -> 0.13), so NASDAQ needs its own fit rather than
inheriting SP500's config. Starts from scratch: which of the 4 entry types
even wins on NASDAQ (not assumed to be stop_breakout just because it won on
SP500/US30), then a stop/target grid on the winner. Same IS/OOS split
(2021-07-28) and house Phase-6-adjacent conventions as the SP500 work.
"""

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from ny_open_orb.data import fetch_m15, fetch_m5
from ny_open_orb.engine import ENTRY_TYPES, build_frame, find_entries, simulate
from strategy.metrics import summarize

warnings.filterwarnings("ignore")
pd.set_option("display.width", 160)

START, END = "2016-07-28", "2026-07-28"
SPLIT_DATE = "2021-07-28"
INSTRUMENT = "NASDAQ"


def report(label: str, index: pd.DatetimeIndex, trades: pd.DataFrame):
    if trades.empty:
        print(f"{label:>32} keine Trades")
        return
    s = summarize(trades, index)
    print(f"{label:>32} n={s['n_trades']:>4} sharpe={s['sharpe']:>6.2f} pf={s['profit_factor']:>5.2f} win={s['win_rate']:>6.1%} cagr={s['cagr']:>7.1%} maxdd={s['max_drawdown']:>7.1%}")


def main():
    m15 = fetch_m15(INSTRUMENT, START, END)
    m5 = fetch_m5(INSTRUMENT, START, END)
    frame = build_frame(m15, m5, range_bars=1)
    split_ts = pd.Timestamp(SPLIT_DATE, tz=frame.index.tz)

    print(f"--- {INSTRUMENT}: Entry-Typ-Vergleich (Default-Exit: ATR-Stop 1.5x, Target 4R) ---")
    for entry_type in ENTRY_TYPES:
        entries = find_entries(frame, entry_type)
        trades = simulate(frame, entries, stop_atr_mult=1.5, target_mode="r_multiple", target_r_mult=4.0)
        oos = trades[trades["entry_time"] >= split_ts] if not trades.empty else trades
        oos_idx = frame.index[frame.index >= split_ts]
        report(f"{entry_type} (OOS)", oos_idx, oos)

    print(f"\n--- {INSTRUMENT}: stop_breakout Exit-Grid (stop_atr_mult x target_r_mult), OOS ---")
    entries = find_entries(frame, "stop_breakout")
    for stop_atr_mult in (0.6, 0.8, 1.0, 1.5, 2.0):
        for target_r_mult in (2.0, 3.0, 4.0, 6.0):
            trades = simulate(frame, entries, stop_atr_mult=stop_atr_mult, target_mode="r_multiple", target_r_mult=target_r_mult)
            oos = trades[trades["entry_time"] >= split_ts] if not trades.empty else trades
            oos_idx = frame.index[frame.index >= split_ts]
            report(f"stop={stop_atr_mult}x target={target_r_mult}R", oos_idx, oos)

    print(f"\n--- {INSTRUMENT}: range_bars (1-4), stop_breakout, stop=1.0x/target=4R, OOS ---")
    for range_bars in (1, 2, 3, 4):
        frame_rb = build_frame(m15, m5, range_bars=range_bars)
        entries_rb = find_entries(frame_rb, "stop_breakout")
        trades = simulate(frame_rb, entries_rb, stop_atr_mult=1.0, target_mode="r_multiple", target_r_mult=4.0)
        oos = trades[trades["entry_time"] >= split_ts] if not trades.empty else trades
        oos_idx = frame_rb.index[frame_rb.index >= split_ts]
        report(f"range_bars={range_bars}", oos_idx, oos)


if __name__ == "__main__":
    main()
