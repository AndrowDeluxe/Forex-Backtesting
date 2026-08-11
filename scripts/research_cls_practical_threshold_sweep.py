"""Threshold sweep for cls_practical, per user request (2026-08-11): SMA
window (trend filter), rates z-score threshold, and ADR-TP multiplier - are
the first-guess defaults (200 / 0.5 / 0.35) anywhere near a robust choice,
or did we just get lucky/unlucky on one config? Univariate sweeps (hold the
other two at their default) rather than a full grid, to keep each swept
value's effect readable - a full grid is easy to add later if a promising
interaction shows up here."""

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

DEFAULTS = dict(sma_window=200, rates_z_threshold=0.5, adr_mult=0.35)
SMA_WINDOWS = [50, 100, 150, 200, 250]
Z_THRESHOLDS = [0.0, 0.25, 0.5, 0.75, 1.0, 1.5]
ADR_MULTS = [0.10, 0.15, 0.20, 0.25, 0.35, 0.50]


def run(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5, **overrides):
    params = {**DEFAULTS, **overrides}
    trades = simulate_cls_practical(
        eurusd_m5, other_majors_m15, bund_m5, ustbond_m5, tp_mode="adr",
        sma_window=params["sma_window"], rates_z_threshold=params["rates_z_threshold"],
        adr_mult=params["adr_mult"],
    )
    s = trade_stats(trades)
    return {
        **params,
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

    print("=== SMA-Fenster (Trend-Filter), Rest auf Default ===")
    rows = [run(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5, sma_window=w) for w in SMA_WINDOWS]
    print(pd.DataFrame(rows).to_string(index=False))

    print("\n=== Rates-Z-Score-Schwelle, Rest auf Default ===")
    rows = [run(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5, rates_z_threshold=z) for z in Z_THRESHOLDS]
    print(pd.DataFrame(rows).to_string(index=False))

    print("\n=== ADR-TP-Multiplikator, Rest auf Default ===")
    rows = [run(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5, adr_mult=m) for m in ADR_MULTS]
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
