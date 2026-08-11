"""First test of the CLS Practical Playbook rebuild (cls_practical/) - EUR/USD
M5 entries, per the ruleset agreed with the user (2026-08-11): Trend (SMA200
on EUR/USD) + Rates-Ampel (BUND/USTBOND long-end proxy) + Crosses
(cls_advanced's existing broad-dollar check) must ALL agree for a
Continuation or Reversal setup, else No Trade. Account 100,000 (assumed USD),
risk 0.5%/trade. TP tested as 0.35xADR(14) first, per the user's own
instruction, before comparing to a fixed 1:2 R.

Fetch window starts 2018-12 because that's where the USTBOND CFD feed (the
rates proxy - see cls_practical/rates.py) itself begins on Dukascopy,
checked 2026-08-11 - the "full history" this strategy can be tested over is
therefore ~7.5 years, not the ~10 years most other strategies in this repo
use. SMA(200) and the rates z-score's own 60-day rolling window both need
warmup on top of that, so the first few months of trades tested are
effectively suppressed (rates_ampel stays "gelb" - no signal - until the
z-score window has enough history).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from cls_practical.data import fetch_major_m15_berlin, fetch_rate_instrument_m5_berlin
from cls_practical.engine import simulate_cls_practical
from presettle_breakout.data import fetch_m5_berlin
from strategy.cls_advanced import PAIRS
from strategy.metrics import trade_stats

START, END = "2018-12-01", "2026-08-11"
OTHER_MAJORS = [p for p in PAIRS if p != "EURUSD"]

COLS = [
    "date", "setup", "direction", "entry_time", "exit_time", "entry_price", "sl", "tp",
    "exit_price", "exit_reason", "trend_bias", "rates_ampel", "cross_confirmed",
    "units_eur", "pnl_usd", "return_pct",
]


def main():
    print(f"Fetching EUR/USD M5 (Berlin tz) {START} -> {END} ...")
    eurusd_m5 = fetch_m5_berlin("EURUSD", START, END)
    print(f"{len(eurusd_m5)} bars.")

    print(f"Fetching other 5 majors M15 ({', '.join(OTHER_MAJORS)}) ...")
    other_majors_m15 = {p: fetch_major_m15_berlin(p, START, END) for p in OTHER_MAJORS}

    print("Fetching BUND/USTBOND CFD M5 (rates proxy) ...")
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)
    print(f"BUND: {len(bund_m5)} bars, USTBOND: {len(ustbond_m5)} bars.")

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 25)

    for tp_mode in ("adr", "fixed_r"):
        print(f"\n{'=' * 20} tp_mode={tp_mode} {'=' * 20}")
        trades = simulate_cls_practical(
            eurusd_m5, other_majors_m15, bund_m5, ustbond_m5, tp_mode=tp_mode,
        )
        print(f"{len(trades)} trades (full fetch window, incl. SMA/rates warmup period).")
        if trades.empty:
            print("No trades - either no clean setups, or filters never aligned in this window.")
            continue
        print(trades[COLS].to_string(index=False))
        print("\n--- Stats ---")
        for k, v in trade_stats(trades).items():
            print(f"  {k}: {v}")
        print(f"  total_pnl_usd: {trades['pnl_usd'].sum():.2f}")
        print(f"  setup breakdown: {trades['setup'].value_counts().to_dict()}")


if __name__ == "__main__":
    main()
