"""Entry-timeframe comparison for cls_practical (2026-08-11 user request):
M3 (resampled from real M1), M5 (current default), M15 - both for the full
pipeline (Continuation+Reversal) and the Reversal-only variant. The daily
decision layer (Asia range, Settle-window break, trend/rates/cross filters)
is unchanged across timeframes - only the fractal-trigger entry mechanics
run on different bar sizes. Note: ATR(14)/min_sl_atr_mult's absolute meaning
shifts with the timeframe (14 M15 bars = 3.5h of history vs 14 M3 bars = 42
min), so comparisons should focus on win-rate/PF shape, not assume the SL
floor is "the same" stop across rows.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from cls_practical.data import fetch_eurusd_entry_tf_berlin, fetch_major_m15_berlin, fetch_rate_instrument_m5_berlin
from cls_practical.engine import simulate_cls_practical
from strategy.cls_advanced import PAIRS
from strategy.metrics import summarize

START, END = "2018-12-01", "2026-08-11"
OTHER_MAJORS = [p for p in PAIRS if p != "EURUSD"]
TIMEFRAMES = ["M1", "M3", "M5", "M15"]


def run(eurusd_tf, other_majors_m15, bund_m5, ustbond_m5, label, **overrides):
    trades = simulate_cls_practical(eurusd_tf, other_majors_m15, bund_m5, ustbond_m5, **overrides)
    s = summarize(trades, eurusd_tf.index)
    return {
        "variant": label,
        "n_trades": s["n_trades"],
        "win_rate": s["win_rate"],
        "profit_factor": s["profit_factor"],
        "sharpe": s["sharpe"],
        "calmar": s["calmar"],
        "max_drawdown": s["max_drawdown"],
        "total_pnl_usd": trades["pnl_usd"].sum() if not trades.empty else 0.0,
        "setup_breakdown": trades["setup"].value_counts().to_dict() if not trades.empty else {},
    }


def main():
    other_majors_m15 = {p: fetch_major_m15_berlin(p, START, END) for p in OTHER_MAJORS}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 25)

    rows = []
    for tf in TIMEFRAMES:
        print(f"Fetching EUR/USD {tf} ...")
        eurusd_tf = fetch_eurusd_entry_tf_berlin(tf, START, END)
        print(f"  {len(eurusd_tf)} bars.")
        rows.append(run(eurusd_tf, other_majors_m15, bund_m5, ustbond_m5, f"{tf} - Voll (Cont.+Rev.)"))
        rows.append(run(eurusd_tf, other_majors_m15, bund_m5, ustbond_m5, f"{tf} - Reversal-Only", allowed_setups=("reversal",)))

    print("\n" + pd.DataFrame(rows).drop(columns=["setup_breakdown"]).to_string(index=False))
    print("\nSetup-Aufschlüsselung:")
    for row in rows:
        print(f"  {row['variant']}: {row['setup_breakdown']}")


if __name__ == "__main__":
    main()
