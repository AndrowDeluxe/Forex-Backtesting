"""Properly out-of-sample test of a weekday filter - and per the user's
request, Nasdaq and SP500 are now tuned INDEPENDENTLY rather than forcing
one filter to work on both (a stronger cross-asset-agreement bar was used
before; this relaxes that, so IS/OOS discipline within each asset matters
even more).

The earlier "Thursday is weak on both assets" finding was derived from the
FULL period (2016-2026), which already includes the OOS half - looking at
it and then "confirming" it on that same OOS slice would be circular. This
script redoes it honestly per asset: rank weekdays by profit factor using
ONLY the In-Sample half (2016-2021), pick the weakest day found in-sample
for THAT asset specifically, then test excluding it on the untouched
Out-of-Sample half (2021-2026) - a real holdout test, not a re-confirmation
of what was already seen.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from combined_strategy.data import fetch_timeframe
from orb_strategy.pipeline import run_orb_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import summarize, trade_stats

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

START, END = "2016-07-28", "2026-07-28"
SPLIT = "2021-07-28"


def _lower_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})


def _weekday_table(trades: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for day, group in trades.groupby(trades["entry_time"].dt.day_name()):
        if len(group) < 10:  # skip near-empty buckets (e.g. stray Sunday) - not a real weekday sample
            continue
        s = trade_stats(group)
        rows.append({"day": day, "n": s["n_trades"], "win_rate": s["win_rate"], "profit_factor": s["profit_factor"]})
    return pd.DataFrame(rows).set_index("day").sort_values("profit_factor")


def run_asset(name: str, df: pd.DataFrame):
    print(f"\n{'=' * 15} {name} {'=' * 15}")
    signaled = run_orb_pipeline(df, atr_n=14, atr_mult=1.0, long_only=True, adx_min=25.0)
    cfg = BacktestConfig(spread_bps=0.3, stop_atr_mult=2.0, use_vwap_target=False)
    trades = simulate_trades(signaled, cfg)

    split_ts = pd.Timestamp(SPLIT, tz=signaled.index.tz)
    is_trades = trades[trades["entry_time"] < split_ts]
    oos_trades_all = trades[trades["entry_time"] >= split_ts]
    oos_signaled = signaled[signaled.index >= split_ts]

    print("\nIn-Sample (2016-2021) Wochentag-Ranking (schwaechste zuerst):")
    is_table = _weekday_table(is_trades)
    print(is_table)

    if is_table.empty:
        print("  Zu wenig In-Sample-Daten fuer ein Wochentag-Ranking.")
        return

    weakest_day = is_table.index[0]
    print(f"\n-> Schwaechster In-Sample-Wochentag fuer {name}: {weakest_day} (PF {is_table.iloc[0]['profit_factor']:.2f}, n={int(is_table.iloc[0]['n'])})")

    oos_baseline = summarize(oos_trades_all, oos_signaled.index)
    oos_filtered_trades = oos_trades_all[oos_trades_all["entry_time"].dt.day_name() != weakest_day]
    oos_filtered = summarize(oos_filtered_trades, oos_signaled.index)

    print(f"\nOut-of-Sample (2021-2026), Baseline (alle Wochentage):")
    print(f"  n={oos_baseline['n_trades']}, sharpe={oos_baseline['sharpe']:.2f}, pf={oos_baseline['profit_factor']:.2f}, win_rate={oos_baseline['win_rate']:.1%}")
    print(f"Out-of-Sample, {weakest_day} ausgeschlossen:")
    print(f"  n={oos_filtered['n_trades']}, sharpe={oos_filtered['sharpe']:.2f}, pf={oos_filtered['profit_factor']:.2f}, win_rate={oos_filtered['win_rate']:.1%}")

    only_that_day_oos = oos_trades_all[oos_trades_all["entry_time"].dt.day_name() == weakest_day]
    if not only_that_day_oos.empty:
        s = trade_stats(only_that_day_oos)
        print(f"\nZur Kontrolle - nur {weakest_day} in der Out-of-Sample-Haelfte:")
        print(f"  n={s['n_trades']}, win_rate={s['win_rate']:.1%}, pf={s['profit_factor']:.2f}")


def main():
    print("Loading NASDAQ M15...")
    run_asset("NASDAQ", _lower_ohlcv(fetch_timeframe("NASDAQ", "M15", START, END)))

    print("\nLoading SP500 M15...")
    run_asset("SP500", _lower_ohlcv(fetch_timeframe("SP500", "M15", START, END)))


if __name__ == "__main__":
    main()
