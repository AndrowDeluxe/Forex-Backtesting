"""First test of the user's Pre-Settle Range Breakout observation
(presettle_breakout/) - EUR/USD M5, range 06:00 Berlin through the first
confirmed local M5 swing high/low at or after 07:00, breakout traded
thereafter, SL = 2x ATR(14) M5, TP = fixed 1:2 RR, entries after 12:00
invalidated. Scoped to July + August 2026 first, per user request, before
running the full history."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from presettle_breakout.data import fetch_m5_berlin
from presettle_breakout.engine import simulate_presettle_breakout
from strategy.metrics import trade_stats

# A few days of lookback before July starts so ATR(14) on M5 is warmed up by
# the time the first trading day's range closes - trivial in wall-clock terms
# (14 M5 bars = 70 minutes) but fetched as whole days since Dukascopy data is
# pulled by calendar day.
FETCH_START, FETCH_END = "2026-06-25", "2026-08-11"
MONTHS = [("2026-07-01", "2026-08-01"), ("2026-08-01", "2026-09-01")]

COLS = [
    "window_start", "entry_time", "exit_time", "direction",
    "entry_price", "sl", "tp", "exit_price", "exit_reason",
    "return_pct", "hold_bars",
]


def main():
    print(f"Fetching EUR/USD M5 (Berlin tz) {FETCH_START} -> {FETCH_END} ...")
    df = fetch_m5_berlin("EURUSD", FETCH_START, FETCH_END)
    print(f"{len(df)} bars fetched.")

    trades = simulate_presettle_breakout(df)

    pd.set_option("display.width", 160)
    pd.set_option("display.max_columns", 20)

    for month_start, month_end in MONTHS:
        label = month_start[:7]
        month_trades = trades[(trades["entry_time"] >= month_start) & (trades["entry_time"] < month_end)]
        print(f"\n{'=' * 20} {label} ({len(month_trades)} trades) {'=' * 20}")
        if month_trades.empty:
            print("No trades.")
            continue
        print(month_trades[COLS].to_string(index=False))
        print(f"\n--- Stats ({label}) ---")
        for k, v in trade_stats(month_trades).items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
