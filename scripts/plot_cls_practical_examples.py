"""Visual sanity check for cls_practical's fractal-trigger mechanics (see
cls_practical/chart.py) - renders one Continuation and one Reversal example
trade as PNGs, before trusting the numeric backtest over a longer period."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cls_practical.chart import plot_trade_example
from cls_practical.data import fetch_major_m15_berlin, fetch_rate_instrument_m5_berlin
from cls_practical.engine import simulate_cls_practical
from presettle_breakout.data import fetch_m5_berlin
from strategy.cls_advanced import PAIRS, compute_daily_features

START, END = "2025-08-01", "2026-08-11"
OTHER_MAJORS = [p for p in PAIRS if p != "EURUSD"]
OUT_DIR = Path(__file__).resolve().parents[1] / "data_cache" / "cls_practical" / "example_charts"


def main():
    eurusd_m5 = fetch_m5_berlin("EURUSD", START, END)
    other_majors_m15 = {p: fetch_major_m15_berlin(p, START, END) for p in OTHER_MAJORS}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)

    trades = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5, tp_mode="adr")
    daily = compute_daily_features(eurusd_m5)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    continuation = trades[trades["setup"] == "continuation"]
    reversal = trades[trades["setup"] == "reversal"]

    examples = []
    if not continuation.empty:
        examples.append(("continuation", continuation.iloc[0]))
    if not reversal.empty:
        examples.append(("reversal", reversal.iloc[0]))

    for label, trade in examples:
        row = daily.loc[trade["date"]]
        out_path = OUT_DIR / f"{label}_{trade['date']}.png"
        plot_trade_example(eurusd_m5, trade, row["asia_high"], row["asia_low"], str(out_path))
        print(f"{label}: {trade['date']} -> {out_path}")


if __name__ == "__main__":
    main()
