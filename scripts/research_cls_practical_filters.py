"""Two more knobs on top of the Reversal-Only finding (2026-08-11, the
clear win-rate winner from research_cls_practical_standard.py):
1. min_sl_atr_mult sweep - is 1.0x the right structural-stop floor, or does
   the win-rate/PF trade-off keep improving further out?
2. Execution-overlay (Zarattini & Pagani "Fast Alpha" timing filter, ported
   from asian_range_breakout/execution_overlay.py) - does waiting for a
   confirming counter-close before filling help here too?
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
MIN_SL_MULTS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0]


def run(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5, **overrides):
    trades = simulate_cls_practical(
        eurusd_m5, other_majors_m15, bund_m5, ustbond_m5,
        allowed_setups=("reversal",), **overrides,
    )
    s = trade_stats(trades)
    return {
        **overrides,
        "n_trades": s["n_trades"],
        "win_rate": s["win_rate"],
        "profit_factor": s["profit_factor"],
        "total_pnl_usd": trades["pnl_usd"].sum() if not trades.empty else 0.0,
    }


def main():
    eurusd_m5 = fetch_m5_berlin("EURUSD", START, END)
    other_majors_m15 = {p: fetch_major_m15_berlin(p, START, END) for p in OTHER_MAJORS}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)

    pd.set_option("display.width", 160)
    pd.set_option("display.max_columns", 20)

    print("=== min_sl_atr_mult-Sweep (Reversal-Only) ===")
    rows = [run(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5, min_sl_atr_mult=m) for m in MIN_SL_MULTS]
    print(pd.DataFrame(rows).to_string(index=False))

    print("\n=== Execution-Overlay an/aus (Reversal-Only, min_sl_atr_mult=1.0) ===")
    rows = [
        run(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5, use_execution_overlay=False),
        run(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5, use_execution_overlay=True),
    ]
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
