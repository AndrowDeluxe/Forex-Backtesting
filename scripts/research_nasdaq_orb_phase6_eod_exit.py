"""Phase 6 robustness check for Stage 8's NASDAQ EOD-close-exit candidate
(knowledge/projects/ny-open-orb-sp500.md, Stage 8): Sharpe held roughly
constant (1.41->1.42) while CAGR nearly tripled (3.2%->9.1%) when swapping
the fixed 4R target for "ride to session close or stop, whichever first" -
too large a swing to trust without the same walk-forward/Monte-Carlo/cost-sweep
scrutiny every other "final" claim in this project has been through (repo
standard: Phase 6 is mandatory before any risk-sizing-relevant claim).

Also tests the user's follow-up question: does EOD-exit combine with the
already-adopted Stage-6 partial-exit+breakeven-rest logic, or are they
mutually exclusive philosophies (bank early + let the remainder run to
EOD instead of to a fixed 4R target)? engine.simulate already supports
this combination with no code change - target_mode=None simply disables
the FINAL target check; partial_exit_r/partial_exit_fraction/
move_stop_to_be_after_partial are independent of it.

Three configs, same house Phase-6 battery as research_nasdaq_orb_phase6.py
(3-period walk-forward, Monte Carlo block-bootstrap on OOS daily returns,
cost/slippage sweep to breakeven, yearly OOS breakdown) run for each:

1. baseline: the currently adopted standard (4R target + 1.5R/50%
   partial-exit + BE-rest) - reference point, numbers should match Stage 6/
   the portfolio dashboard exactly.
2. eod_pure: EOD-close exit, no partial exit at all (Stage 8's tested config).
3. eod_partial: EOD-close exit AND the Stage-6 partial-exit+BE-rest overlay -
   bank 50% at 1.5R (stop moves to breakeven for the remainder), then the
   remaining 50% rides to session close instead of a fixed 4R cap.
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
STARTING_EQUITY = 10_000.0
INSTRUMENT = "NASDAQ"

CONFIGS = {
    "baseline (4R + 1.5R/50% Teilausstieg+BE)": dict(stop_atr_mult=0.6, target_mode="r_multiple", target_r_mult=4.0, partial_exit_r=1.5, partial_exit_fraction=0.5, move_stop_to_be_after_partial=True),
    "eod_pure (EOD-Exit, kein Teilausstieg)": dict(stop_atr_mult=0.6, target_mode=None),
    "eod_partial (EOD-Exit + 1.5R/50% Teilausstieg+BE)": dict(stop_atr_mult=0.6, target_mode=None, partial_exit_r=1.5, partial_exit_fraction=0.5, move_stop_to_be_after_partial=True),
}


def build_config_entries(frame: pd.DataFrame) -> pd.DataFrame:
    all_entries = find_entries(frame, "stop_breakout")
    return filters.filter_by_weekday(all_entries, exclude=["Wednesday"])


def report(label, index, trades):
    if trades.empty:
        print(f"{label:>14} keine Trades")
        return
    s = summarize(trades, index)
    print(f"{label:>14} n={s['n_trades']:>4} sharpe={s['sharpe']:>6.2f} pf={s['profit_factor']:>5.2f} win={s['win_rate']:>6.1%} cagr={s['cagr']:>7.1%} maxdd={s['max_drawdown']:>7.1%}")


def run_phase6(name: str, exit_cfg: dict, frame: pd.DataFrame, entries: pd.DataFrame, split_ts: pd.Timestamp) -> None:
    print("\n" + "#" * 100)
    print(f"# {name}  --  {exit_cfg}")
    print("#" * 100)

    trades = simulate(frame, entries, spread_bps=0.5, **exit_cfg)
    print(f"n_trades full={len(trades)}, OOS={len(trades[trades['entry_time'] >= split_ts])}")

    print("\n--- p6_1 - Walk-Forward (3 unabhaengige Perioden) ---")
    for label, p_start, p_end in PERIODS:
        p_start_ts, p_end_ts = pd.Timestamp(p_start, tz=frame.index.tz), pd.Timestamp(p_end, tz=frame.index.tz)
        sub_trades = trades[(trades["entry_time"] >= p_start_ts) & (trades["entry_time"] < p_end_ts)]
        sub_index = frame.index[(frame.index >= p_start_ts) & (frame.index < p_end_ts)]
        report(label, sub_index, sub_trades)
    report("full", frame.index, trades)

    print("\n--- p6_2 - Monte Carlo (block_size=20, n_sims=2000, seed=42), OOS-only ---")
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
    print(f"  Realisierter Pfad: Sharpe={summarize(oos_trades, oos_index)['sharpe']:.2f} vs. Median-Simulation {np.median(s['sharpe']):.2f}")

    print("\n--- p6_3 - Cost/Slippage-Sweep bis Breakeven, OOS-only ---")
    spread_candidates = [0.5, 1, 2, 3, 5, 8, 12, 18, 25]
    prev_bps, prev_ret, breakeven = None, None, None
    for bps in spread_candidates:
        cfg = dict(exit_cfg)
        cfg["spread_bps"] = bps
        t = simulate(frame, entries, **cfg)
        oos_t = t[t["entry_time"] >= split_ts]
        total_ret = (1 + oos_t["return_pct"]).prod() - 1 if not oos_t.empty else float("nan")
        print(f"  spread={bps:>5.1f}bps  n={len(oos_t):>4}  total_return={total_ret:>8.1%}")
        if breakeven is None and prev_ret is not None and prev_ret >= 0 > total_ret:
            breakeven = prev_bps + (bps - prev_bps) * prev_ret / (prev_ret - total_ret)
        prev_bps, prev_ret = bps, total_ret
    if breakeven is not None:
        print(f"\n  Breakeven-Spread: ~{breakeven:.1f}bps, Sicherheitsfaktor = {breakeven / 0.5:.1f}x")

    print("\n--- p6_4 - Jaehrliche OOS-Aufschluesselung ---")
    for year, group in oos_trades.groupby(oos_trades["entry_time"].dt.year):
        year_index = frame.index[frame.index.year == year]
        s = summarize(group, year_index)
        print(f"  {year}: n={s['n_trades']:>3} sharpe={s['sharpe']:>6.2f} pf={s['profit_factor']:>5.2f} win={s['win_rate']:>6.1%} cagr={s['cagr']:>7.1%}")


def main():
    m15 = fetch_m15(INSTRUMENT, START, END)
    m5 = fetch_m5(INSTRUMENT, START, END)
    frame = build_frame(m15, m5, range_bars=1)
    entries = build_config_entries(frame)
    split_ts = pd.Timestamp(OOS_SPLIT, tz=frame.index.tz)

    for name, cfg in CONFIGS.items():
        run_phase6(name, cfg, frame, entries, split_ts)


if __name__ == "__main__":
    main()
