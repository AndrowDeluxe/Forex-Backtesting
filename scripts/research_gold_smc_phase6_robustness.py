"""Phase 6 "Robustheit" (app_pages/education_gold_intraday.py), done properly
this time (chat 2026-08-20: "Du bist nicht nach dem Standardprozess
vorgegangen"):

  p6_1 Walk-Forward/echter OOS-Split (anderer Zeitraum) -> bereits erledigt
       in research_gold_smc_walkforward.py (2016-2024, nie gesehen).
  p6_2 Monte-Carlo-Bootstrap der Trade-Sequenz, MUSTER: ou_paper_backtest/
       monte_carlo.py -> hier per echtem Import nachgeholt (vorher hatte ich
       mir einen eigenen, abweichenden Bootstrap gebaut statt den bereits
       etablierten wiederzuverwenden - genau die Inkonsistenz, die das
       Second Brain verhindern soll).
  p6_3 Kosten-Sensitivitaet: Spread/Slippage bis zum Breakeven sweepen ->
       bisher komplett ausgelassen, hier nachgeholt.
  p6_4 Mehrere Jahre/Marktregime -> bereits erledigt in research_gold_smc_
       walkforward.py (4 Sub-Perioden 2016-2024).
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "ou_paper_backtest"))

import numpy as np
import pandas as pd

from gold_smc_htf_ltf.concurrent_backtest import (
    equity_curve_to_daily_returns, simulate_combined_account, simulate_trades_concurrent,
)
from gold_smc_htf_ltf.continuation import run_pipeline as run_continuation
from gold_smc_htf_ltf.data import fetch_gold_h1, fetch_gold_h4, fetch_gold_m5, fetch_gold_m15
from gold_smc_htf_ltf.reversal_cascade import run_pipeline as run_reversal
from monte_carlo import run_monte_carlo  # ou_paper_backtest/monte_carlo.py - the established pattern
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import annualized_sharpe, cagr

pd.set_option("display.width", 160)

START, END = "2024-08-01", "2026-08-01"
SPLIT = pd.Timestamp("2025-08-01", tz="America/New_York")
STARTING_EQUITY = 100_000.0
MAX_DD_LIMIT = 0.06

CONT_PIPELINE_KWARGS = dict(trend_indicator="ema_adx_combo", htf_valid_bars=24, entry_variant="direct", min_target_distance_atr=0.5)
REV_PIPELINE_KWARGS = dict(h4_confirm_bars=30, h1_valid_bars=24, min_target_distance_atr=1.0, require_ema_reject=True, m15_entry_mode="repeat_sweep")

MAX_CONCURRENT = {"continuation": None, "reversal": 3}

SCENARIOS = {
    "FK (0.50% / 0.15%)": (0.005, 0.0015),
    "EK (2.00% / 1.50%)": (0.02, 0.015),
}


def cfg_cont(spread_bps: float) -> BacktestConfig:
    return BacktestConfig(spread_bps=spread_bps, stop_atr_mult=0.5, use_vwap_target=True, breakeven_trigger_r=None, max_hold_bars=24 * 12)


def cfg_rev(spread_bps: float) -> BacktestConfig:
    return BacktestConfig(spread_bps=spread_bps, stop_atr_mult=3.0, use_vwap_target=False, take_profit_r=5.0, breakeven_trigger_r=None, max_hold_bars=96 * 4)


def main():
    print(f"Fetching GOLD H4/H1/M15/M5 {START} -> {END} ...")
    h4 = fetch_gold_h4(START, END)
    h1 = fetch_gold_h1(START, END)
    m15 = fetch_gold_m15(START, END)
    m5 = fetch_gold_m5(START, END)

    cont_sig = run_continuation(h4, h1, m5, trend_df=m15, **CONT_PIPELINE_KWARGS)
    cont_oos_sig = cont_sig[cont_sig.index >= SPLIT]
    rev_sig = run_reversal(h4, h1, m15, **REV_PIPELINE_KWARGS)
    rev_oos_sig = rev_sig[rev_sig.index >= SPLIT]

    # ================================================================ p6_2
    print("\n" + "=" * 100)
    print("p6_2 - MONTE-CARLO-BOOTSTRAP (echter Import von ou_paper_backtest/monte_carlo.py)")
    print("=" * 100)
    cont_trades = simulate_trades(cont_oos_sig, cfg_cont(8.0))
    rev_trades = simulate_trades_concurrent(rev_oos_sig, cfg_rev(8.0))

    for name, (risk_cont, risk_rev) in SCENARIOS.items():
        sim = simulate_combined_account(
            {"continuation": cont_trades, "reversal": rev_trades},
            {"continuation": risk_cont, "reversal": risk_rev},
            MAX_CONCURRENT, starting_equity=STARTING_EQUITY,
        )
        daily = equity_curve_to_daily_returns(sim["equity_curve"], rev_oos_sig.index)
        mc = run_monte_carlo(daily, initial_equity=STARTING_EQUITY, block_size=20, n_sims=2000, seed=42)
        s = mc["summary"]
        print(f"\n{name}  (block_size=20, n_sims=2000, zirkulaerer Bootstrap - Original-Muster)")
        for p in (5, 25, 50, 75, 95):
            dd_p = np.percentile(s["max_drawdown_pct"], p)
            ret_p = np.percentile(s["total_return_pct"], p)
            print(f"  P{p:>2}  MaxDD={dd_p:>8.2f}%   TotalReturn={ret_p:>+9.2f}%")
        breach = (s["max_drawdown_pct"] < -MAX_DD_LIMIT * 100).mean()
        print(f"  P(MaxDD > {MAX_DD_LIMIT:.0%}) = {breach:.1%}   Median Sharpe={np.nanmedian(s['sharpe']):.2f}   Median Calmar={np.nanmedian(s['calmar']):.2f}")

    # ================================================================ p6_3
    print("\n" + "=" * 100)
    print("p6_3 - KOSTEN-SENSITIVITAET: Spread/Slippage bis zum Breakeven (OOS, je Strategie einzeln)")
    print("=" * 100)
    spread_candidates = [8.0, 16.0, 24.0, 32.0, 40.0, 50.0, 60.0, 80.0, 100.0, 120.0, 150.0, 200.0]

    print("\nContinuation (single-position):")
    cont_breakeven = None
    for sp in spread_candidates:
        t = simulate_trades(cont_oos_sig, cfg_cont(sp))
        if t.empty:
            print(f"  spread={sp:>6.1f}bps  n=0")
            continue
        total_ret = (1 + t["return_pct"]).prod() - 1
        pf = t.loc[t["return_pct"] > 0, "return_pct"].sum() / -t.loc[t["return_pct"] < 0, "return_pct"].sum() if (t["return_pct"] < 0).any() else float("inf")
        print(f"  spread={sp:>6.1f}bps  n={len(t):>3}  TotalReturn={total_ret:>+8.2%}  PF={pf:.3f}")
        if cont_breakeven is None and total_ret < 0:
            cont_breakeven = sp
    print(f"  -> Breakeven-Spread ungefaehr zwischen {spread_candidates[spread_candidates.index(cont_breakeven) - 1] if cont_breakeven else spread_candidates[-1]:.0f} und {cont_breakeven:.0f} bps" if cont_breakeven else "  -> bleibt profitabel im gesamten getesteten Bereich")
    print(f"  Aktuell angenommen: 8.0bps -> Sicherheitsfaktor: {(cont_breakeven / 8.0):.1f}x" if cont_breakeven else "")

    print("\nReversal-Kaskade (concurrent, mc=3, r-multiple-basiert):")
    rev_breakeven = None
    for sp in spread_candidates:
        t = simulate_trades_concurrent(rev_oos_sig, cfg_rev(sp))
        if t.empty:
            print(f"  spread={sp:>6.1f}bps  n=0")
            continue
        t_valid = t.dropna(subset=["r_multiple"])
        total_r = t_valid["r_multiple"].sum()
        pf = t_valid.loc[t_valid["r_multiple"] > 0, "r_multiple"].sum() / -t_valid.loc[t_valid["r_multiple"] < 0, "r_multiple"].sum() if (t_valid["r_multiple"] < 0).any() else float("inf")
        print(f"  spread={sp:>6.1f}bps  n={len(t_valid):>4}  Sum(R)={total_r:>+8.2f}  PF={pf:.3f}")
        if rev_breakeven is None and total_r < 0:
            rev_breakeven = sp
    print(f"  -> Breakeven-Spread ungefaehr zwischen {spread_candidates[spread_candidates.index(rev_breakeven) - 1] if rev_breakeven else spread_candidates[-1]:.0f} und {rev_breakeven:.0f} bps" if rev_breakeven else "  -> bleibt profitabel im gesamten getesteten Bereich")
    print(f"  Aktuell angenommen: 8.0bps -> Sicherheitsfaktor: {(rev_breakeven / 8.0):.1f}x" if rev_breakeven else "")


if __name__ == "__main__":
    main()
