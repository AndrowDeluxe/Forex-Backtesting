"""Tests an economically-motivated volume-confirmation filter for ORB
(long-only + ADX>=25 + per-asset weekday-filter already in place): does
requiring the breakout bar's volume to exceed some multiple of its own
trailing 20-bar average further cut losing trades?

Same IS/OOS discipline as the weekday filter: sweep volume_min_ratio on
In-Sample (2016-2021) only, pick whatever ratio looks best there for each
asset independently, then verify on the untouched Out-of-Sample half
(2021-2026) - not just report whatever wins on the full period.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from combined_strategy.data import fetch_timeframe
from orb_strategy.pipeline import run_orb_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import summarize

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

START, END = "2016-07-28", "2026-07-28"
SPLIT = "2021-07-28"
ASSET_WEEKDAY = {"NASDAQ": "Thursday", "SP500": "Monday"}
RATIOS = [None, 0.75, 1.0, 1.25, 1.5, 2.0]


def _lower_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})


def run_asset(name: str, df: pd.DataFrame):
    print(f"\n{'=' * 15} {name} {'=' * 15}")
    exclude_weekday = ASSET_WEEKDAY[name]

    print("\n-- In-Sample (2016-2021): Volumen-Ratio-Sweep --")
    is_results = {}
    for ratio in RATIOS:
        signaled = run_orb_pipeline(
            df, atr_n=14, atr_mult=1.0, long_only=True, adx_min=25.0,
            exclude_weekday=exclude_weekday, volume_min_ratio=ratio,
        )
        cfg = BacktestConfig(spread_bps=0.3, stop_atr_mult=2.0, use_vwap_target=False)
        trades = simulate_trades(signaled, cfg)
        split_ts = pd.Timestamp(SPLIT, tz=signaled.index.tz)
        is_trades = trades[trades["entry_time"] < split_ts]
        is_signaled = signaled[signaled.index < split_ts]
        s = summarize(is_trades, is_signaled.index) if not is_trades.empty else None
        label = "kein Filter" if ratio is None else f"ratio>={ratio}"
        if s:
            print(f"  {label}: n={s['n_trades']}, sharpe={s['sharpe']:.2f}, pf={s['profit_factor']:.2f}, win_rate={s['win_rate']:.1%}")
            is_results[ratio] = s["sharpe"]
        else:
            print(f"  {label}: keine Trades")

    best_ratio = max(is_results, key=is_results.get) if is_results else None
    print(f"\n-> Bester In-Sample-Ratio fuer {name}: {best_ratio} (Sharpe {is_results.get(best_ratio, float('nan')):.2f})")

    print("\n-- Out-of-Sample (2021-2026): Baseline vs. bester IS-Ratio --")
    for ratio, label in [(None, "kein Volumenfilter (Baseline)"), (best_ratio, f"ratio>={best_ratio}")]:
        if ratio == best_ratio and best_ratio is None:
            continue  # avoid printing the baseline twice if "kein Filter" was itself the IS-best
        signaled = run_orb_pipeline(
            df, atr_n=14, atr_mult=1.0, long_only=True, adx_min=25.0,
            exclude_weekday=exclude_weekday, volume_min_ratio=ratio,
        )
        cfg = BacktestConfig(spread_bps=0.3, stop_atr_mult=2.0, use_vwap_target=False)
        trades = simulate_trades(signaled, cfg)
        split_ts = pd.Timestamp(SPLIT, tz=signaled.index.tz)
        oos_trades = trades[trades["entry_time"] >= split_ts]
        oos_signaled = signaled[signaled.index >= split_ts]
        s = summarize(oos_trades, oos_signaled.index) if not oos_trades.empty else None
        if s:
            print(f"  {label}: n={s['n_trades']}, sharpe={s['sharpe']:.2f}, pf={s['profit_factor']:.2f}, win_rate={s['win_rate']:.1%}, max_dd={s['max_drawdown']:.1%}")
        else:
            print(f"  {label}: keine Trades")


def main():
    print("Loading NASDAQ M15...")
    run_asset("NASDAQ", _lower_ohlcv(fetch_timeframe("NASDAQ", "M15", START, END)))

    print("\nLoading SP500 M15...")
    run_asset("SP500", _lower_ohlcv(fetch_timeframe("SP500", "M15", START, END)))


if __name__ == "__main__":
    main()
