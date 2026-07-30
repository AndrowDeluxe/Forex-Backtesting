"""Robustness pass on the ORB long-only + ADX>=25 filter, before pushing it
to Streamlit as a real strategy: the filter itself was derived by looking
at the exact same Nasdaq window it's now being praised on (see chat), so
this checks it honestly on a held-out later period instead of just
re-confirming on the same data. Also runs the existing cost/breakeven-
spread utility (strategy.metrics.breakeven_spread_bps) - already built
for exactly this purpose - on both confirmed assets (Nasdaq, SP500).
"""

import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from combined_strategy.data import fetch_timeframe
from orb_strategy.pipeline import run_orb_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import breakeven_spread_bps, summarize

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

START, END = "2016-07-28", "2026-07-28"
SPLIT = "2021-07-28"
STOP_MULT = 2.0
BASE_CFG = BacktestConfig(spread_bps=0.3, stop_atr_mult=STOP_MULT, use_vwap_target=False)


def _lower_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})


def _report(signaled: pd.DataFrame, trades: pd.DataFrame, label: str):
    if trades.empty:
        print(f"  {label}: 0 trades")
        return
    s = summarize(trades, signaled.index)
    print(
        f"  {label}: n={s['n_trades']}, sharpe={s['sharpe']:.2f}, pf={s['profit_factor']:.2f}, "
        f"win_rate={s['win_rate']:.1%}, avg_bps={s['avg_return_pct'] * 1e4:.2f}, max_dd={s['max_drawdown']:.1%}"
    )


def run_is_oos(df: pd.DataFrame, name: str):
    print(f"\n{'=' * 15} {name}: In-Sample (2016-2021) vs Out-of-Sample (2021-2026) {'=' * 15}")
    signaled = run_orb_pipeline(df, atr_n=14, atr_mult=1.0, long_only=True, adx_min=25.0)
    trades = simulate_trades(signaled, BASE_CFG)

    split_ts = pd.Timestamp(SPLIT, tz=signaled.index.tz)
    is_signaled, oos_signaled = signaled[signaled.index < split_ts], signaled[signaled.index >= split_ts]
    is_trades = trades[trades["entry_time"] < split_ts]
    oos_trades = trades[trades["entry_time"] >= split_ts]

    _report(is_signaled, is_trades, "In-Sample  (2016-2021)")
    _report(oos_signaled, oos_trades, "Out-of-Sample (2021-2026)")

    print(f"\n  Breakeven-Spread (round-trip bps, full period, long-only+ADX>=25):")
    be = breakeven_spread_bps(signaled, BASE_CFG, lo=0.0, hi=30.0)
    print(f"    {be:.2f} bps (currently modelled: {BASE_CFG.spread_bps} bps)")


def main():
    print("Loading NASDAQ M15...")
    nasdaq = _lower_ohlcv(fetch_timeframe("NASDAQ", "M15", START, END))
    run_is_oos(nasdaq, "NASDAQ")

    print("\nLoading SP500 M15...")
    sp500 = _lower_ohlcv(fetch_timeframe("SP500", "M15", START, END))
    run_is_oos(sp500, "SP500")


if __name__ == "__main__":
    main()
