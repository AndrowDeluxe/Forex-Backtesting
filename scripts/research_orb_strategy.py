"""First honest test of the ORB (Opening Range Breakout) strategy from
Holmberg, Loennbark & Lundstroem (2013) -- see app_pages/orb_writeup.py.

Baseline only (no regime/volatility filter yet): daily-open-anchored
threshold = open +/- atr_mult x prior-day-ATR(14), first breakout of the
day fires, exit on stop or day-close (session rollover). Tested at M15
across EUR/USD (project reference) + the paper's own asset (crude oil)
+ Gold/SP500/Nasdaq (already-fetchable, for consistency with other
research scripts here). Same yearly walk-forward reporting style as
every other research_*.py script in this project.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from combined_strategy.data import fetch_timeframe
from orb_strategy.pipeline import run_orb_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import summarize
from strategy.real_data import fetch_pair_history

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

YEARS = list(range(2017, 2027))
OTHER_ASSETS = ["OIL", "GOLD", "SP500", "NASDAQ"]
START, END = "2016-07-28", "2026-07-28"


def _lower_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})


def run_one(df: pd.DataFrame, label: str, atr_mult: float = 1.0, stop_atr_mult: float = 1.0):
    signaled = run_orb_pipeline(df, atr_n=14, atr_mult=atr_mult)
    cfg = BacktestConfig(spread_bps=0.3, stop_atr_mult=stop_atr_mult, use_vwap_target=False)
    trades = simulate_trades(signaled, cfg)

    print(f"\n{'=' * 10} {label} ({len(df)} bars) {'=' * 10}")
    print(f"Total trades: {len(trades)}")
    if trades.empty:
        return
    print("Exit reason breakdown:\n", trades["exit_reason"].value_counts())

    full_summary = summarize(trades, signaled.index)
    print("Full-period:", {k: v for k, v in full_summary.items() if k != "exit_reason_counts"})

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
    print("Yearly walk-forward:\n", yearly)
    active = yearly[yearly["n_trades"] > 0]
    if not active.empty:
        print(f"Mean Sharpe across active years: {active['sharpe'].mean():.2f}")
        print(f"Years with positive avg return: {(active['avg_return_bps'] > 0).sum()}/{len(active)}")


def main():
    print("\nLoading EUR/USD M15 (reference)...")
    eurusd = fetch_pair_history("EURUSD", START, END)
    run_one(eurusd, "EUR/USD M15, ORB baseline (atr_mult=1.0, stop=1.0x)")

    for key in OTHER_ASSETS:
        print(f"\nLoading {key} M15 (cached after first run)...")
        df = _lower_ohlcv(fetch_timeframe(key, "M15", START, END))
        run_one(df, f"{key} M15, ORB baseline (atr_mult=1.0, stop=1.0x)")


if __name__ == "__main__":
    main()
