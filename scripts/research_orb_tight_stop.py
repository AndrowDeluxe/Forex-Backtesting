"""Sweeps stop_atr_mult into much tighter territory (0.1-0.75x M15-ATR)
than tested so far (1.0-4.0x, all essentially inert - session_end exits
dominated regardless). Question: does a genuinely tight stop start
clipping the from-the-start-losing trades identified as the real
drawdown driver in the breakeven test (research_orb_breakeven.py found
breakeven barely ever triggers, since most damage comes from trades that
never move favourably at all, not from give-back after a good move)?

Reports exit-reason mix (to see exactly where "stop" starts displacing
"session_end"), full-period + Out-of-Sample (2021-2026) stats, and the
OOS Monte Carlo drawdown tail, same methodology as every other
research_orb_*.py script.
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
STOP_MULTS = [0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0]


def _lower_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})


def monte_carlo_tail(oos_trades: pd.DataFrame, stop_mult: float, n_sims: int = 3000, risk_pct: float = 0.01, start_capital: float = 10_000.0):
    if oos_trades.empty:
        return None, None
    returns = oos_trades["return_pct"].to_numpy()
    stop_frac = (stop_mult * oos_trades["atr_at_entry"] / oos_trades["entry_price"]).to_numpy()
    stop_frac = np.where(stop_frac <= 0, 1e-6, stop_frac)
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
    return np.percentile(finals, 5), np.percentile(dds, 5)


def run_asset(name: str, df: pd.DataFrame):
    print(f"\n{'=' * 15} {name}: enger Stop, atr_mult=1.0, ADX>=25, Long-only {'=' * 15}")
    signaled = run_orb_pipeline(df, atr_n=14, atr_mult=1.0, long_only=True, adx_min=25.0)
    split_ts = pd.Timestamp(SPLIT, tz=signaled.index.tz)
    oos_signaled = signaled[signaled.index >= split_ts]

    for stop_mult in STOP_MULTS:
        cfg = BacktestConfig(spread_bps=0.3, stop_atr_mult=stop_mult, use_vwap_target=False)
        trades = simulate_trades(signaled, cfg)
        oos_trades = trades[trades["entry_time"] >= split_ts] if not trades.empty else trades

        full_s = summarize(trades, signaled.index)
        oos_s = summarize(oos_trades, oos_signaled.index) if not oos_trades.empty else None
        p5_final, p5_dd = monte_carlo_tail(oos_trades, stop_mult)

        exit_mix = trades["exit_reason"].value_counts().to_dict() if not trades.empty else {}
        stop_share = exit_mix.get("stop", 0) / max(len(trades), 1)

        print(
            f"\nstop_atr_mult={stop_mult}: exit_mix={exit_mix} (stop-Anteil {stop_share:.1%})"
        )
        print(
            f"  Full:  n={full_s['n_trades']}, sharpe={full_s['sharpe']:.2f}, pf={full_s['profit_factor']:.2f}, "
            f"max_dd={full_s['max_drawdown']:.1%}"
        )
        if oos_s:
            print(
                f"  OOS:   n={oos_s['n_trades']}, sharpe={oos_s['sharpe']:.2f}, pf={oos_s['profit_factor']:.2f}, "
                f"win_rate={oos_s['win_rate']:.1%}, max_dd={oos_s['max_drawdown']:.1%}"
            )
        if p5_final is not None:
            print(f"  Monte Carlo OOS: Endkapital p5={p5_final:,.0f}, MaxDD p5={p5_dd:.1%}")


def main():
    print("Loading NASDAQ M15...")
    run_asset("NASDAQ", _lower_ohlcv(fetch_timeframe("NASDAQ", "M15", START, END)))

    print("\nLoading SP500 M15...")
    run_asset("SP500", _lower_ohlcv(fetch_timeframe("SP500", "M15", START, END)))


if __name__ == "__main__":
    main()
