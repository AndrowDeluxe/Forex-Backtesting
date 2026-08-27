"""Phase 6b - re-run the Monte Carlo + cost-sweep robustness checks (same
house convention as phase6.py) on the Stage 4b2 upgrade: stop_breakout,
long-only, EMA-ribbon-bias neutral. Trade count is much lower (452 over 10
years vs 2570 raw) - the whole point of this script is checking whether the
robustness checks still hold up at that lower sample size, not re-deriving
p6_1/p6_4 (already shown as the walk-forward table in Stage 4b2).
"""

import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ou_paper_backtest"))

import numpy as np
import pandas as pd
from monte_carlo import run_monte_carlo

from ny_open_orb import filters, regime
from ny_open_orb.data import fetch_sp500_m15, fetch_sp500_m5
from ny_open_orb.engine import build_frame, find_entries, simulate
from strategy.backtest import trades_to_daily_returns
from strategy.metrics import summarize

warnings.filterwarnings("ignore")
pd.set_option("display.width", 160)

START, END = "2016-07-28", "2026-07-28"
OOS_SPLIT = "2021-07-28"
EXIT_CFG = dict(stop_atr_mult=1.0, target_mode="r_multiple", target_r_mult=4.0)
STARTING_EQUITY = 10_000.0


def build_filtered_entries(frame: pd.DataFrame, m15: pd.DataFrame) -> pd.DataFrame:
    all_entries = find_entries(frame, "stop_breakout")
    long_entries = filters.filter_by_direction(all_entries, 1)
    bias = regime.ema_trend_bias(m15, frame["session"].unique())
    bias_vals = filters.values_at(long_entries, bias)
    return filters.filter_by_category(long_entries, bias_vals, (0.0,))


def main():
    m15 = fetch_sp500_m15(START, END)
    m5 = fetch_sp500_m5(START, END)
    frame = build_frame(m15, m5, range_bars=1)
    entries = build_filtered_entries(frame, m15)
    trades = simulate(frame, entries, spread_bps=0.5, **EXIT_CFG)
    split_ts = pd.Timestamp(OOS_SPLIT, tz=frame.index.tz)

    print(f"Config: stop_breakout, long-only, EMA-neutral, {EXIT_CFG}")
    print(f"n_trades full={len(trades)}, OOS(>=2021-07-28)={len(trades[trades['entry_time'] >= split_ts])}")

    print("\n" + "=" * 100)
    print("p6_2 - Monte Carlo (block_size=20, n_sims=2000, seed=42), OOS-only")
    print("=" * 100)
    oos_trades = trades[trades["entry_time"] >= split_ts]
    oos_index = frame.index[frame.index >= split_ts]
    daily = trades_to_daily_returns(oos_trades, oos_index)
    mc = run_monte_carlo(daily, initial_equity=STARTING_EQUITY, block_size=20, n_sims=2000, seed=42)
    s = mc["summary"]
    for pct in (5, 25, 50, 75, 95):
        print(f"  p{pct:>2}: max_drawdown={np.percentile(s['max_drawdown_pct'], pct):>7.1f}%  total_return={np.percentile(s['total_return_pct'], pct):>8.1f}%  sharpe={np.percentile(s['sharpe'], pct):>5.2f}")
    for limit in (5.0, 10.0, 20.0):
        print(f"  P(MaxDD > {limit:.0f}%) = {(s['max_drawdown_pct'] < -limit).mean():.1%}")
    print(f"  Median Sharpe: {np.median(s['sharpe']):.2f}   Median Calmar: {np.nanmedian(s['calmar']):.2f}")

    print("\n" + "=" * 100)
    print("p6_3 - Cost/Slippage-Sweep bis Breakeven, OOS-only")
    print("=" * 100)
    spread_candidates = [0.5, 1, 2, 3, 5, 8, 12, 18, 25]
    prev_bps, prev_ret, breakeven = None, None, None
    for bps in spread_candidates:
        t = simulate(frame, entries, spread_bps=bps, **EXIT_CFG)
        oos_t = t[t["entry_time"] >= split_ts]
        total_ret = (1 + oos_t["return_pct"]).prod() - 1 if not oos_t.empty else float("nan")
        print(f"  spread={bps:>5.1f}bps  n={len(oos_t):>4}  total_return={total_ret:>8.1%}")
        if breakeven is None and prev_ret is not None and prev_ret >= 0 > total_ret:
            breakeven = prev_bps + (bps - prev_bps) * prev_ret / (prev_ret - total_ret)
        prev_bps, prev_ret = bps, total_ret
    if breakeven is not None:
        print(f"\n  Breakeven-Spread: ~{breakeven:.1f}bps, Sicherheitsfaktor = {breakeven / 0.5:.1f}x")


if __name__ == "__main__":
    main()
