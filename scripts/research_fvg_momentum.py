"""Honest rebuild of Bindra (2025), "Multi-Asset A/A+ Momentum Fair Value Gap
Strategy" - see fvg_momentum/engine.py's docstring for why the source's own
reported numbers (473 trades, 78% WR, +132.5% return, -2.0% MaxDD) cannot be
trusted: its own Appendix A discloses a "deterministic hashing" win-
probability simulator instead of a real price-path backtest, and its trade
log shows literally zero R-multiples other than exactly +1.0 or -1.0 despite
the strategy spec including a TP2/runner-extension target.

This script implements the same rules against REAL Dukascopy M5/H1 price
data for the same 4 instruments and the same calendar year (2025), and
reports what actually happens - matching this repo's standing practice of
re-testing every paper claim rather than trusting it (CLS Advanced, Gap-Fade,
Execution-Overlay, ADX-VWAP all went through the same process)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from fvg_momentum.data import PAIRS, PIP_SIZE, fetch_h1, fetch_m5
from fvg_momentum.engine import simulate_fvg_momentum
from fvg_momentum.indicators import compute_htf_levels

START, END = "2025-01-01", "2025-12-31"
STARTING_CAPITAL = 50_000.0
RISK_PER_TRADE = 250.0


def fmt(trades: pd.DataFrame) -> str:
    if trades.empty:
        return "n=0"
    wins = trades["r_multiple"] > 0
    gross_win = trades.loc[wins, "r_multiple"].sum()
    gross_loss = -trades.loc[~wins, "r_multiple"].sum()
    pf = gross_win / gross_loss if gross_loss > 0 else float("inf")
    return f"n={len(trades):>4}  WR={wins.mean():.1%}  PF={pf:.3f}  TotalR={trades['r_multiple'].sum():+.1f}"


def main():
    all_trades = []
    for pair in PAIRS:
        print(f"Fetching {pair} M5 + H1 ({START} -> {END}) ...")
        m5 = fetch_m5(pair, START, END)
        h1 = fetch_h1(pair, START, END)
        h1_levels = compute_htf_levels(h1)

        trades = simulate_fvg_momentum(m5, h1_levels, pip_size=PIP_SIZE[pair])
        trades["pair"] = pair
        all_trades.append(trades)
        print(f"  {pair}: {fmt(trades)}")

    trades = pd.concat(all_trades, ignore_index=True).sort_values("entry_time").reset_index(drop=True)

    print("\n" + "=" * 78)
    print("PORTFOLIO-LEVEL (all 4 instruments, real M5/H1 Dukascopy price action)")
    print("=" * 78)
    print(f"  {fmt(trades)}")
    if not trades.empty:
        pnl = trades["r_multiple"] * RISK_PER_TRADE
        equity = STARTING_CAPITAL + pnl.cumsum()
        running_max = equity.cummax()
        dd = (equity - running_max) / running_max
        print(f"  Start-Kapital: ${STARTING_CAPITAL:,.0f}   End-Kapital: ${equity.iloc[-1]:,.0f}")
        print(f"  Netto-Gewinn: ${pnl.sum():+,.0f}   Rendite: {(equity.iloc[-1]/STARTING_CAPITAL-1):+.1%}")
        print(f"  Max Drawdown: {dd.min():.1%}")
        print(f"  Exit-Gruende: {trades['exit_reason'].value_counts().to_dict()}")

        print("\n  --- Per Asset ---")
        for pair, g in trades.groupby("pair"):
            print(f"  {pair:8s} {fmt(g)}")

        print("\n  --- Per Grade ---")
        for grade, g in trades.groupby("grade"):
            print(f"  {grade:3s} {fmt(g)}")

        print("\n  --- Per Session ---")
        for session, g in trades.groupby("session"):
            print(f"  {session:10s} {fmt(g)}")

        print("\n  --- Monatlich ---")
        monthly = trades.copy()
        monthly["month"] = monthly["entry_time"].dt.to_period("M")
        for month, g in monthly.groupby("month"):
            r = g["r_multiple"].sum()
            print(f"  {month}  n={len(g):>3}  R={r:+.1f}  P&L=${r*RISK_PER_TRADE:+,.0f}")

        print("\n  --- Vergleich mit dem Paper (deterministisches Hashing statt echter Preise) ---")
        print(f"  Paper:  n=473  WR=78.0%  TotalR=+265.0  Rendite=+132.5%  MaxDD=-2.0%")
        wins = trades["r_multiple"] > 0
        gross_win = trades.loc[wins, "r_multiple"].sum()
        gross_loss = -trades.loc[~wins, "r_multiple"].sum()
        pf = gross_win / gross_loss if gross_loss > 0 else float("inf")
        print(
            f"  Real :  n={len(trades)}  WR={wins.mean():.1%}  TotalR={trades['r_multiple'].sum():+.1f}  "
            f"Rendite={(equity.iloc[-1]/STARTING_CAPITAL-1):+.1%}  MaxDD={dd.min():.1%}  PF={pf:.3f}"
        )
    else:
        print("  Keine Trades gefunden.")


if __name__ == "__main__":
    main()
