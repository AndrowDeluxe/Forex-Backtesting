"""Tests the new breakeven_trigger_r mechanic (strategy/backtest.py) on the
ORB long-only + ADX>=25 strategy: does moving the stop to entry once a
trade is +R in favour reduce the drawdown tail found in the Monte Carlo
bootstrap, without giving up too much of the (already modest) edge?

BE_TRIGGER_R candidates 0.5 and 1.0 chosen to match the same convention
already used by the user's live OU-Modell bot (BE_TRIGGER_R=0.5) and by
checklist_strategy (breakeven at 1:1) - not arbitrary numbers.

Reports full-period AND the honest Out-of-Sample slice (2021-2026, same
split as research_orb_robustness.py), plus a Monte Carlo bootstrap on the
OOS trades so the drawdown-tail comparison is apples-to-apples with the
no-breakeven baseline already reported in chat.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from combined_strategy.data import fetch_timeframe
from orb_strategy.pipeline import run_orb_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import summarize

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

START, END = "2016-07-28", "2026-07-28"
SPLIT = "2021-07-28"
RNG = np.random.default_rng(42)


def _lower_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})


def _report(signaled: pd.DataFrame, trades: pd.DataFrame, label: str):
    if trades.empty:
        print(f"  {label}: 0 trades")
        return
    s = summarize(trades, signaled.index)
    be_count = int(trades["moved_to_be"].sum()) if "moved_to_be" in trades.columns else 0
    print(
        f"  {label}: n={s['n_trades']}, sharpe={s['sharpe']:.2f}, pf={s['profit_factor']:.2f}, "
        f"win_rate={s['win_rate']:.1%}, avg_bps={s['avg_return_pct'] * 1e4:.2f}, "
        f"max_dd={s['max_drawdown']:.1%}, exit_reasons={trades['exit_reason'].value_counts().to_dict()}, "
        f"auf_BE_verschoben={be_count}"
    )


def monte_carlo(oos_trades: pd.DataFrame, label: str, n_sims: int = 5000, risk_pct: float = 0.01, start_capital: float = 10_000.0):
    if oos_trades.empty:
        print(f"  {label}: keine Trades")
        return
    returns = oos_trades["return_pct"].to_numpy()
    stop_frac = (2.0 * oos_trades["atr_at_entry"] / oos_trades["entry_price"]).to_numpy()
    n = len(returns)
    finals, dds = [], []
    for _ in range(n_sims):
        idx = RNG.integers(0, n, size=n)
        equity, curve = start_capital, [start_capital]
        for r, sf in zip(returns[idx], stop_frac[idx]):
            equity += (equity * risk_pct / sf) * r
            curve.append(equity)
        finals.append(equity)
        arr = np.array(curve)
        dds.append(((arr - np.maximum.accumulate(arr)) / np.maximum.accumulate(arr)).min())
    finals, dds = np.array(finals), np.array(dds)
    print(
        f"  {label}: p5={np.percentile(finals, 5):,.0f}, p50={np.percentile(finals, 50):,.0f}, "
        f"p95={np.percentile(finals, 95):,.0f}, Anteil<Start={((finals < start_capital).mean()):.1%}, "
        f"MaxDD p5={np.percentile(dds, 5):.1%}, MaxDD p50={np.percentile(dds, 50):.1%}"
    )


def run_asset(name: str, df: pd.DataFrame):
    print(f"\n{'=' * 15} {name} {'=' * 15}")
    signaled = run_orb_pipeline(df, atr_n=14, atr_mult=1.0, long_only=True, adx_min=25.0)
    split_ts = pd.Timestamp(SPLIT, tz=signaled.index.tz)
    oos_signaled = signaled[signaled.index >= split_ts]

    for be_r, label in [(None, "Kein Breakeven (Baseline)"), (0.5, "Breakeven @ 0.5R"), (1.0, "Breakeven @ 1.0R")]:
        cfg = BacktestConfig(spread_bps=0.3, stop_atr_mult=2.0, use_vwap_target=False, breakeven_trigger_r=be_r)
        trades = simulate_trades(signaled, cfg)
        oos_trades = trades[trades["entry_time"] >= split_ts] if not trades.empty else trades

        print(f"\n-- {label} --")
        _report(signaled, trades, "Full-Period")
        _report(oos_signaled, oos_trades, "Out-of-Sample")
        monte_carlo(oos_trades, "Monte Carlo (OOS)")


def main():
    print("Loading NASDAQ M15...")
    run_asset("NASDAQ", _lower_ohlcv(fetch_timeframe("NASDAQ", "M15", START, END)))

    print("\nLoading SP500 M15...")
    run_asset("SP500", _lower_ohlcv(fetch_timeframe("SP500", "M15", START, END)))


if __name__ == "__main__":
    main()
