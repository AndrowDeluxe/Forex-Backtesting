"""Re-test the checklist strategy (baseline, no regime filter - already
shown to be too thin to trust at M15) across M15/H1/H4, EUR/USD, to see
whether a coarser bar frequency changes the picture. Same yearly
walk-forward methodology as the other research_*.py scripts.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import dukascopy_python
import pandas as pd

from checklist_strategy.backtest import simulate_checklist_trades
from checklist_strategy.pipeline import run_checklist_pipeline
from strategy.metrics import summarize
from strategy.real_data import fetch_pair_history

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

YEARS = list(range(2017, 2026))
TIMEFRAMES = {
    "M15": dukascopy_python.INTERVAL_MIN_15,
    "H1": dukascopy_python.INTERVAL_HOUR_1,
    "H4": dukascopy_python.INTERVAL_HOUR_4,
}
# Expiry windows were chosen as "~8 bars" against M15 (~2h). Keep the same
# *bar count* by default (matches exactly re-testing "the whole thing"
# unchanged at a coarser resolution) - flagged separately if that turns out
# to matter.


def run_one(df: pd.DataFrame, label: str):
    signaled = run_checklist_pipeline(df)
    trades = simulate_checklist_trades(signaled)

    print(f"\n{'=' * 10} {label} ({len(df)} bars) {'=' * 10}")
    print(f"Total trades: {len(trades)}")
    if trades.empty:
        return
    print("Exit reason breakdown:\n", trades["exit_reason"].value_counts())

    full_summary = summarize(trades, signaled.index)
    print("\nFull-period summary:")
    for k, v in full_summary.items():
        if k != "exit_reason_counts":
            print(f"  {k}: {v}")

    rows = []
    for year in YEARS:
        yr_df = signaled[signaled.index.year == year]
        if yr_df.empty:
            continue
        yr_trades = trades[trades["entry_time"].dt.year == year]
        if yr_trades.empty:
            rows.append({"year": year, "n_trades": 0})
            continue
        s = summarize(yr_trades, yr_df.index)
        rows.append(
            {
                "year": year, "n_trades": s["n_trades"], "win_rate": s["win_rate"],
                "avg_return_bps": s["avg_return_pct"] * 1e4, "sharpe": s["sharpe"],
            }
        )
    yearly = pd.DataFrame(rows).set_index("year")
    print("\nYearly walk-forward:\n", yearly)
    active = yearly[yearly["n_trades"] > 0]
    if not active.empty:
        print(f"Mean Sharpe across active years: {active['sharpe'].mean():.2f}")
        print(f"Years with positive avg return: {(active['avg_return_bps'] > 0).sum()}/{len(active)}")


def main():
    for tf_name, interval in TIMEFRAMES.items():
        print(f"\nLoading EUR/USD {tf_name} history (cached after first run)...")
        df = fetch_pair_history("EURUSD", "2016-07-28", "2026-07-28", interval=interval)
        run_one(df, f"EUR/USD {tf_name}, baseline (no regime filter)")


if __name__ == "__main__":
    main()
