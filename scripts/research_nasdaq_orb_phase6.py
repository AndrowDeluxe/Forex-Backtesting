"""Phase 6 for the NASDAQ-specific config found in stage2/stage3/stage3b:
stop_breakout, range_bars=1, long+short, exclude Wednesday, ATR-stop 0.6x,
target 4R. Same house convention as the SP500 phase6/phase6b scripts
(3-period walk-forward, Monte Carlo block-bootstrap on OOS daily returns,
cost/slippage sweep to breakeven, yearly OOS breakdown).
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

from ny_open_orb import filters
from ny_open_orb.data import fetch_m15, fetch_m5
from ny_open_orb.engine import build_frame, find_entries, simulate
from strategy.backtest import trades_to_daily_returns
from strategy.metrics import summarize

warnings.filterwarnings("ignore")
pd.set_option("display.width", 160)

START, END = "2016-07-28", "2026-07-28"
OOS_SPLIT = "2021-07-28"
PERIODS = [("2016-2019", "2016-07-28", "2019-07-28"), ("2019-2022", "2019-07-28", "2022-07-28"), ("2022-2026", "2022-07-28", "2026-07-28")]
EXIT_CFG = dict(stop_atr_mult=0.6, target_mode="r_multiple", target_r_mult=4.0)
STARTING_EQUITY = 10_000.0
INSTRUMENT = "NASDAQ"


def build_config_entries(frame: pd.DataFrame) -> pd.DataFrame:
    all_entries = find_entries(frame, "stop_breakout")
    return filters.filter_by_weekday(all_entries, exclude=["Wednesday"])


def report(label, index, trades):
    if trades.empty:
        print(f"{label:>14} keine Trades")
        return
    s = summarize(trades, index)
    print(f"{label:>14} n={s['n_trades']:>4} sharpe={s['sharpe']:>6.2f} pf={s['profit_factor']:>5.2f} win={s['win_rate']:>6.1%} cagr={s['cagr']:>7.1%} maxdd={s['max_drawdown']:>7.1%}")


def main():
    m15 = fetch_m15(INSTRUMENT, START, END)
    m5 = fetch_m5(INSTRUMENT, START, END)
    frame = build_frame(m15, m5, range_bars=1)
    entries = build_config_entries(frame)
    trades = simulate(frame, entries, spread_bps=0.5, **EXIT_CFG)
    split_ts = pd.Timestamp(OOS_SPLIT, tz=frame.index.tz)

    print(f"Config: {INSTRUMENT} stop_breakout, long+short, ohne Mittwoch, {EXIT_CFG}")
    print(f"n_trades full={len(trades)}, OOS={len(trades[trades['entry_time'] >= split_ts])}")

    print("\n" + "=" * 100)
    print("p6_1 - Walk-Forward (3 unabhaengige Perioden)")
    print("=" * 100)
    for label, p_start, p_end in PERIODS:
        p_start_ts, p_end_ts = pd.Timestamp(p_start, tz=frame.index.tz), pd.Timestamp(p_end, tz=frame.index.tz)
        sub_trades = trades[(trades["entry_time"] >= p_start_ts) & (trades["entry_time"] < p_end_ts)]
        sub_index = frame.index[(frame.index >= p_start_ts) & (frame.index < p_end_ts)]
        report(label, sub_index, sub_trades)
    report("full", frame.index, trades)

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

    print("\n" + "=" * 100)
    print("p6_4 - Jaehrliche OOS-Aufschluesselung")
    print("=" * 100)
    for year, group in oos_trades.groupby(oos_trades["entry_time"].dt.year):
        year_index = frame.index[frame.index.year == year]
        s = summarize(group, year_index)
        print(f"  {year}: n={s['n_trades']:>3} sharpe={s['sharpe']:>6.2f} pf={s['profit_factor']:>5.2f} win={s['win_rate']:>6.1%} cagr={s['cagr']:>7.1%}")


if __name__ == "__main__":
    main()
