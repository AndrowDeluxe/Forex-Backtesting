"""Re-test the checklist strategy (baseline, no regime/session filter) on
Gold, Oil, S&P 500 and Nasdaq at M15, using the same Dukascopy instrument
mapping already set up for combined_strategy - plus a final Daily (D1)
re-test of the whole checklist for EUR/USD and these other assets.

combined_strategy.data.fetch_timeframe() renames OHLCV to Title Case
(Open/High/Low/Close/Volume) to match ema_strategy's convention; the
checklist_strategy pipeline expects lowercase columns (matching
strategy.real_data's convention), so we rename back here.

At D1, confirm1_expiry_bars=8 / confirm2_expiry_bars=8 mean 8 *days* (not
~2 hours as at M15), and nw_window=500 means ~2 years of daily bars (not
~5 trading days) - same bar-count-preserved-by-default approach as the
earlier M15/H1/H4 re-test, flagged rather than silently reinterpreted.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from checklist_strategy.backtest import simulate_checklist_trades
from checklist_strategy.pipeline import run_checklist_pipeline
from combined_strategy.data import fetch_timeframe
from strategy.metrics import summarize
from strategy.real_data import fetch_pair_history

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

YEARS = list(range(2017, 2027))
OTHER_ASSETS = ["GOLD", "OIL", "SP500", "NASDAQ"]
START, END = "2016-07-28", "2026-07-28"


def _lower_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})


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
    print("\n" + "#" * 20 + " PART 1: OTHER ASSETS, M15, BASELINE " + "#" * 20)

    print("\nLoading EUR/USD M15 (reference, already known result)...")
    eurusd_m15 = fetch_pair_history("EURUSD", START, END)
    run_one(eurusd_m15, "EUR/USD M15, baseline (reference)")

    for key in OTHER_ASSETS:
        print(f"\nLoading {key} M15 (cached after first run)...")
        df = _lower_ohlcv(fetch_timeframe(key, "M15", START, END))
        run_one(df, f"{key} M15, baseline")

    print("\n" + "#" * 20 + " PART 2: DAILY (D1) RE-TEST, ALL ASSETS " + "#" * 20)

    print("\nLoading EUR/USD D1 (cached after first run)...")
    eurusd_d1 = _lower_ohlcv(fetch_timeframe("EURUSD", "D1", START, END))
    run_one(eurusd_d1, "EUR/USD D1, baseline (8 = 8 days, nw_window=500 = ~2yrs)")

    for key in OTHER_ASSETS:
        print(f"\nLoading {key} D1 (cached after first run)...")
        df = _lower_ohlcv(fetch_timeframe(key, "D1", START, END))
        run_one(df, f"{key} D1, baseline")


if __name__ == "__main__":
    main()
