"""Stage 2 - head-to-head comparison of the four entry mechanics
(ny_open_orb/engine.py) with a fixed, simple default exit (ATR(14,M15) stop,
4R target - the chart example the user shared), so this stage isolates the
ENTRY question before Stage 3 tunes exits/indicator filters. IS/OOS split
matches the house convention already used by app_pages/orb_strategy.py for
the same SP500/2016-2026 window (SPLIT_DATE="2021-07-28") - the honest
number is the OOS half, not the pooled one.
"""

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from ny_open_orb.data import fetch_sp500_m15, fetch_sp500_m5
from ny_open_orb.engine import ENTRY_TYPES, build_frame, find_entries, simulate
from strategy.metrics import summarize

warnings.filterwarnings("ignore")
pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

START, END = "2016-07-28", "2026-07-28"
SPLIT_DATE = "2021-07-28"


def run(range_bars: int):
    print(f"\n{'=' * 30} range_bars={range_bars} ({15 * range_bars} min range) {'=' * 30}")
    m15 = fetch_sp500_m15(START, END)
    m5 = fetch_sp500_m5(START, END)
    frame = build_frame(m15, m5, range_bars=range_bars)
    split_ts = pd.Timestamp(SPLIT_DATE, tz=frame.index.tz)

    header = f"{'entry_type':>18} {'period':>6} {'n':>4} {'sharpe':>7} {'pf':>6} {'win':>7} {'avg_r':>7} {'cagr':>8} {'maxdd':>8}"
    print(header)
    for entry_type in ENTRY_TYPES:
        entries = find_entries(frame, entry_type)
        trades = simulate(frame, entries)
        if trades.empty:
            print(f"{entry_type:>18} keine Trades")
            continue
        for label, mask in [("full", pd.Series(True, index=trades.index)), ("IS", trades["entry_time"] < split_ts), ("OOS", trades["entry_time"] >= split_ts)]:
            sub = trades[mask]
            if sub.empty:
                print(f"{entry_type:>18} {label:>6} keine Trades")
                continue
            idx = frame.index if label == "full" else (frame.index[frame.index < split_ts] if label == "IS" else frame.index[frame.index >= split_ts])
            s = summarize(sub, idx)
            pf = s.get("profit_factor", float("nan"))
            print(
                f"{entry_type:>18} {label:>6} {s['n_trades']:>4} {s['sharpe']:>7.2f} {pf:>6.2f} "
                f"{s['win_rate']:>6.1%} {sub['r_multiple'].mean():>7.2f} {s['cagr']:>7.1%} {s['max_drawdown']:>7.1%}"
            )


def main():
    for range_bars in (1, 2):
        run(range_bars)


if __name__ == "__main__":
    main()
