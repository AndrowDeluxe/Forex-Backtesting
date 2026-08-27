"""Phase 6 - Robustheit, on the candidate Stage 2/3 actually settled on:
entry_type="stop_breakout", range_bars=1 (15-min NY-open range),
stop_atr_mult=1.0, target_mode="r_multiple", target_r_mult=4.0, no ADX/RVOL
filters (both were tested and made things worse - see
knowledge/projects/ny-open-orb-sp500.md).

Follows the exact house Phase-6 convention (see
research_mt5_gold_silver_divergenz_phase6.py / research_gold_smc_phase6_robustness.py):
p6_1 walk-forward across genuinely different sub-periods (not just the one
IS/OOS split Stage 2/3 already used), p6_2 Monte Carlo bootstrap via
ou_paper_backtest/monte_carlo.py (block_size=20, n_sims=2000, seed=42) on
OOS daily returns, p6_3 a hand-rolled cost/slippage sweep bracketed to
breakeven, p6_4 a plain per-year OOS breakdown.
"""

import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ou_paper_backtest"))

import pandas as pd
from monte_carlo import run_monte_carlo

from ny_open_orb.data import fetch_sp500_m15, fetch_sp500_m5
from ny_open_orb.engine import build_frame, find_entries, simulate
from strategy.backtest import trades_to_daily_returns
from strategy.metrics import summarize

warnings.filterwarnings("ignore")
pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

START, END = "2016-07-28", "2026-07-28"
OOS_SPLIT = "2021-07-28"
PERIODS = [("2016-2019", "2016-07-28", "2019-07-28"), ("2019-2022", "2019-07-28", "2022-07-28"), ("2022-2026", "2022-07-28", "2026-07-28")]

CONFIG = dict(stop_atr_mult=1.0, target_mode="r_multiple", target_r_mult=4.0)
STARTING_EQUITY = 10_000.0


def build_trades(frame: pd.DataFrame, spread_bps: float = 0.5) -> pd.DataFrame:
    entries = find_entries(frame, "stop_breakout")
    return simulate(frame, entries, spread_bps=spread_bps, **CONFIG)


def p6_1_walkforward(frame: pd.DataFrame, trades: pd.DataFrame):
    print("\n" + "=" * 100)
    print("p6_1 - Walk-Forward ueber 3 unabhaengige ~3-Jahres-Perioden (nicht nur ein IS/OOS-Split)")
    print("=" * 100)
    tz = frame.index.tz
    for label, p_start, p_end in PERIODS:
        p_start_ts, p_end_ts = pd.Timestamp(p_start, tz=tz), pd.Timestamp(p_end, tz=tz)
        sub_trades = trades[(trades["entry_time"] >= p_start_ts) & (trades["entry_time"] < p_end_ts)]
        sub_index = frame.index[(frame.index >= p_start_ts) & (frame.index < p_end_ts)]
        if sub_trades.empty:
            print(f"{label:>12}: keine Trades")
            continue
        s = summarize(sub_trades, sub_index)
        print(
            f"{label:>12}: n={s['n_trades']:>4} sharpe={s['sharpe']:>6.2f} pf={s['profit_factor']:>5.2f} "
            f"win={s['win_rate']:>6.1%} cagr={s['cagr']:>7.1%} maxdd={s['max_drawdown']:>7.1%}"
        )


def p6_2_monte_carlo(frame: pd.DataFrame, trades: pd.DataFrame, split_ts: pd.Timestamp):
    print("\n" + "=" * 100)
    print("p6_2 - Monte Carlo (circular block bootstrap, block_size=20, n_sims=2000, seed=42), OOS-only")
    print("=" * 100)
    oos_trades = trades[trades["entry_time"] >= split_ts]
    oos_index = frame.index[frame.index >= split_ts]
    daily = trades_to_daily_returns(oos_trades, oos_index)
    mc = run_monte_carlo(daily, initial_equity=STARTING_EQUITY, block_size=20, n_sims=2000, seed=42)
    s = mc["summary"]
    import numpy as np
    for pct in (5, 25, 50, 75, 95):
        print(
            f"  p{pct:>2}: max_drawdown={np.percentile(s['max_drawdown_pct'], pct):>7.1f}%  "
            f"total_return={np.percentile(s['total_return_pct'], pct):>8.1f}%  "
            f"sharpe={np.percentile(s['sharpe'], pct):>5.2f}"
        )
    for limit in (10.0, 20.0, 30.0):
        p_exceed = (s["max_drawdown_pct"] < -limit).mean()
        print(f"  P(MaxDD > {limit:.0f}%) = {p_exceed:.1%}")
    print(f"  Median Sharpe: {np.median(s['sharpe']):.2f}   Median Calmar: {np.nanmedian(s['calmar']):.2f}")


def p6_3_cost_sweep(frame: pd.DataFrame, split_ts: pd.Timestamp, assumed_bps: float = 0.5):
    print("\n" + "=" * 100)
    print("p6_3 - Cost/Slippage-Sweep bis Breakeven, OOS-only")
    print("=" * 100)
    spread_candidates = [0.5, 1, 2, 3, 5, 8, 12, 18, 25, 35, 50, 70]
    prev_bps, prev_ret = None, None
    breakeven = None
    for bps in spread_candidates:
        trades = build_trades(frame, spread_bps=bps)
        oos_trades = trades[trades["entry_time"] >= split_ts]
        total_ret = (1 + oos_trades["return_pct"]).prod() - 1 if not oos_trades.empty else float("nan")
        print(f"  spread={bps:>5.1f}bps  n={len(oos_trades):>4}  total_return={total_ret:>8.1%}")
        if breakeven is None and prev_ret is not None and prev_ret >= 0 > total_ret:
            breakeven = prev_bps + (bps - prev_bps) * prev_ret / (prev_ret - total_ret)
        prev_bps, prev_ret = bps, total_ret
    if breakeven is not None:
        print(f"\n  Breakeven-Spread (gebrackt): ~{breakeven:.1f}bps")
        print(f"  Sicherheitsfaktor = breakeven/angenommen = {breakeven / assumed_bps:.1f}x")
    else:
        print(f"\n  Kein Breakeven in der getesteten Spannbreite ({spread_candidates[-1]}bps) gefunden.")


def p6_4_yearly(frame: pd.DataFrame, trades: pd.DataFrame, split_ts: pd.Timestamp):
    print("\n" + "=" * 100)
    print("p6_4 - Jaehrliche OOS-Aufschluesselung (>= 2021-07-28)")
    print("=" * 100)
    oos_trades = trades[trades["entry_time"] >= split_ts]
    for year, group in oos_trades.groupby(oos_trades["entry_time"].dt.year):
        year_index = frame.index[frame.index.year == year]
        s = summarize(group, year_index)
        print(f"  {year}: n={s['n_trades']:>3} sharpe={s['sharpe']:>6.2f} pf={s['profit_factor']:>5.2f} win={s['win_rate']:>6.1%} cagr={s['cagr']:>7.1%}")


def main():
    m15 = fetch_sp500_m15(START, END)
    m5 = fetch_sp500_m5(START, END)
    frame = build_frame(m15, m5, range_bars=1)
    split_ts = pd.Timestamp(OOS_SPLIT, tz=frame.index.tz)
    trades = build_trades(frame)

    print(f"Config: entry_type=stop_breakout, range_bars=1, {CONFIG}")
    print(f"Full history: n_trades={len(trades)}")

    p6_1_walkforward(frame, trades)
    p6_2_monte_carlo(frame, trades, split_ts)
    p6_3_cost_sweep(frame, split_ts)
    p6_4_yearly(frame, trades, split_ts)


if __name__ == "__main__":
    main()
