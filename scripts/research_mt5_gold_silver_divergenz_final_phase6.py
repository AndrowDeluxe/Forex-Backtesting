"""Phase 6 "Robustheit" -- re-run on the FINAL optimized config, not the bot
default. Rule from [[backtest-standard-process]] (this repo's own
second-brain lesson, gold-ctnl-edge-portfolio.md incident): Phase 6 must be
re-validated on whatever config is actually being proposed as final, not
just once on the original baseline before optimization. The Phase 6 run in
scripts/research_mt5_gold_silver_divergenz_phase6.py covered the BOT-DEFAULT
config only -- this script covers the config chosen by the Phase 5 sweep in
scripts/research_mt5_gold_silver_divergenz_optimization.py:

  ret_len=25, band_lookback=50, band_mult=1.75 (was 20/100/1.5)
  stop_atr_mult=2.0, rr_ratio=2.0 (unchanged -- swept and confirmed optimal)
  confirm_len=10 (new: Silver's own 10-bar return must be positive too)

Same four checks as the original Phase 6 script, same periods/thresholds,
so the two are directly comparable:
  p6_1/p6_4 walk-forward across the same 3 rolling sub-periods
  p6_2 Monte-Carlo-Bootstrap (ou_paper_backtest/monte_carlo.py, 2000 paths)
  p6_3 cost sensitivity (breakeven spread, OOS only)
  outlier check (best trade removed, full history)
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "ou_paper_backtest"))

import numpy as np
import pandas as pd

from combined_strategy.data import fetch_timeframe
from monte_carlo import run_monte_carlo
from mt5_gold_silver_divergenz.pipeline import run_pipeline
from strategy.backtest import BacktestConfig, simulate_trades, trades_to_daily_returns
from strategy.metrics import summarize

pd.set_option("display.width", 160)

DATA_START, DATA_END = "2016-01-01", "2026-08-01"
OOS_SPLIT = pd.Timestamp("2023-01-01", tz="UTC")
PERIODS = [
    ("2016-2019", "2016-01-01", "2019-01-01"),
    ("2019-2022", "2019-01-01", "2022-01-01"),
    ("2022-2026", "2022-01-01", "2026-08-01"),
]
STARTING_EQUITY = 100_000.0
RISK_PCT = 0.01

# Final optimized config (chosen on IS 2016-2022 only, scripts/research_mt5_gold_silver_divergenz_optimization.py)
RET_LEN, BAND_LOOKBACK, BAND_MULT = 25, 50, 1.75
ATR_STOP_MULT, RR_RATIO = 2.0, 2.0
CONFIRM_LEN = 10
SPREAD_BPS = 10.0


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  Sharpe={s['sharpe']:.2f}  CAGR={s['cagr']:+.1%}"


def run_mc(trades: pd.DataFrame, index: pd.DatetimeIndex, label: str) -> None:
    if trades.empty:
        print(f"  {label}: n=0, skipping Monte Carlo")
        return
    daily = trades_to_daily_returns(trades, index)
    mc = run_monte_carlo(daily, initial_equity=STARTING_EQUITY, block_size=20, n_sims=2000, seed=42)
    s = mc["summary"]
    print(f"  {label}  (n={len(trades)} trades)")
    for p in (5, 25, 50, 75, 95):
        dd_p = np.percentile(s["max_drawdown_pct"], p)
        ret_p = np.percentile(s["total_return_pct"], p)
        print(f"    P{p:>2}  MaxDD={dd_p:>8.2f}%   TotalReturn={ret_p:>+9.2f}%")
    for limit in (0.10, 0.20, 0.30):
        breach = (s["max_drawdown_pct"] < -limit * 100).mean()
        print(f"    P(MaxDD > {limit:.0%}) = {breach:.1%}", end="   ")
    print(f"\n    Median Sharpe={np.nanmedian(s['sharpe']):.2f}   Median Calmar={np.nanmedian(s['calmar']):.2f}")


def main():
    print(f"Fetching XAUUSD/XAGUSD H4 {DATA_START} -> {DATA_END} ...")
    xau = fetch_timeframe("GOLD", "H4", DATA_START, DATA_END).rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    xag = fetch_timeframe("SILVER", "H4", DATA_START, DATA_END).rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})

    signaled = run_pipeline(xau, xag, ret_len=RET_LEN, band_lookback=BAND_LOOKBACK, band_mult=BAND_MULT, confirm_len=CONFIRM_LEN)
    cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
    trades = simulate_trades(signaled, cfg)

    print(f"\nFinale Config: ret_len={RET_LEN}, band_lookback={BAND_LOOKBACK}, band_mult={BAND_MULT}, "
          f"stop_atr_mult={ATR_STOP_MULT}, rr={RR_RATIO}, confirm_len={CONFIRM_LEN}")
    print(f"Full: {fmt(summarize(trades, signaled.index))}")

    # ================================================================ p6_1/p6_4
    print("\n" + "=" * 100)
    print("p6_1/p6_4 - WALK-FORWARD UEBER 3 ROLLIERENDE SUB-PERIODEN (finale Config)")
    print("=" * 100)
    for name, start, end in PERIODS:
        start_ts, end_ts = pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC")
        period_idx = signaled.index[(signaled.index >= start_ts) & (signaled.index < end_ts)]
        t = trades[(trades["entry_time"] >= start_ts) & (trades["entry_time"] < end_ts)]
        print(f"  {name:<10} {fmt(summarize(t, period_idx))}")
    print("  (Referenz Bot-Default: 2016-2019 Sharpe=-0.53, 2019-2022 Sharpe=+0.61, 2022-2026 Sharpe=+1.11)")

    # ================================================================ p6_2
    print("\n" + "=" * 100)
    print(f"p6_2 - MONTE-CARLO-BOOTSTRAP (finale Config, Risk {RISK_PCT:.1%}/Trade, MAX_OPEN_POSITIONS=1)")
    print("=" * 100)
    run_mc(trades, signaled.index, "Full History (2016-2026)")
    oos_trades = trades[trades["entry_time"] >= OOS_SPLIT]
    oos_idx = signaled.index[signaled.index >= OOS_SPLIT]
    run_mc(oos_trades, oos_idx, "OOS only (2023-2026)")

    # ================================================================ p6_3
    print("\n" + "=" * 100)
    print("p6_3 - KOSTEN-SENSITIVITAET (OOS 2023-2026, finale Config)")
    print("=" * 100)
    oos_sig = signaled[signaled.index >= OOS_SPLIT]
    spread_candidates = [5.0, 10.0, 15.0, 20.0, 30.0, 40.0, 50.0, 70.0, 100.0, 150.0, 200.0]
    breakeven = None
    for sp in spread_candidates:
        c = BacktestConfig(spread_bps=sp, stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
        t = simulate_trades(oos_sig, c)
        if t.empty:
            print(f"  spread={sp:>6.1f}bps  n=0")
            continue
        total_ret = (1 + t["return_pct"]).prod() - 1
        pf = t.loc[t["return_pct"] > 0, "return_pct"].sum() / -t.loc[t["return_pct"] < 0, "return_pct"].sum() if (t["return_pct"] < 0).any() else float("inf")
        print(f"  spread={sp:>6.1f}bps  n={len(t):>3}  TotalReturn={total_ret:>+8.2%}  PF={pf:.3f}")
        if breakeven is None and total_ret < 0:
            breakeven = sp
    if breakeven:
        prior = spread_candidates[spread_candidates.index(breakeven) - 1]
        print(f"  -> Breakeven-Spread zwischen {prior:.0f} und {breakeven:.0f} bps (Annahme {SPREAD_BPS:.1f}bps -> Sicherheitsfaktor {breakeven / SPREAD_BPS:.1f}x)")
    else:
        print("  -> bleibt profitabel im gesamten getesteten Bereich")

    # ================================================================ outlier check
    print("\n" + "=" * 100)
    print("OUTLIER-CHECK: bester Trade entfernt (Full History, finale Config)")
    print("=" * 100)
    best_idx = trades["return_pct"].idxmax()
    without_best = trades.drop(best_idx)
    print(f"  Mit bestem Trade   : {fmt(summarize(trades, signaled.index))}")
    print(f"  Ohne besten Trade  : {fmt(summarize(without_best, signaled.index))}")

    wins = trades[trades["return_pct"] > 0].sort_values("return_pct", ascending=False)
    gross_profit = wins["return_pct"].sum()
    print("\n  Profit-Konzentration:")
    for n in (1, 3, 5, 10):
        top_n = wins["return_pct"].head(n).sum()
        print(f"    Top-{n:<2}: {top_n / gross_profit:.1%} des Bruttogewinns" if gross_profit > 0 else "    n/a")


if __name__ == "__main__":
    main()
