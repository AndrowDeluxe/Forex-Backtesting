"""Phase 6 "Robustheit" (app_pages/education_gold_intraday.py) for the
community "David-V2" bot (mt5_david_v2/pipeline.py). The base replication
(scripts/research_mt5_david_v2.py) already showed a weak/negative picture
full-history and IS -- this script checks whether that holds up across
sub-periods, survives realistic costs, and what the sequence-risk profile
looks like, before writing any verdict into
knowledge/projects/mt5-david-v2-pullback.md.

  p6_1/p6_4 Walk-Forward across 3 rolling sub-periods (2016-2019, 2019-2022,
       2022-2026, chosen to give each window several years and a roughly
       even trade count rather than an arbitrary IS/OOS midpoint).
  p6_2 Monte-Carlo-Bootstrap of the trade sequence (ou_paper_backtest/
       monte_carlo.py, block_size=20, n_sims=2000), on the most recent
       sub-period (2022-2026) at the bot's actual risk/concurrency
       (RISK_PERCENT=0.5%, MAX_OPEN_POSITIONS=3, mt5_trend_pullback.
       account_simulation reused as-is -- it's generic across any
       trades_by_market dict, not specific to the Haupt-Bot).
  p6_3 Kosten-Sensitivitaet: breakeven spread per market, on the most recent
       sub-period only (an earlier-period breakeven would be moot given
       those periods are already negative cost-free).
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "ou_paper_backtest"))

import numpy as np
import pandas as pd

from combined_strategy.data import fetch_timeframe
from gold_smc_htf_ltf.concurrent_backtest import equity_curve_to_daily_returns
from monte_carlo import run_monte_carlo
from mt5_david_v2.pipeline import ATR_STOP_MULT, RR_RATIO, run_pipeline
from mt5_trend_pullback.account_simulation import simulate_account
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import summarize

pd.set_option("display.width", 160)

DATA_START, DATA_END = "2016-01-01", "2026-08-01"
PERIODS = [
    ("2016-2019", "2016-01-01", "2019-01-01"),
    ("2019-2022", "2019-01-01", "2022-01-01"),
    ("2022-2026", "2022-01-01", "2026-08-01"),
]
MARKETS = [
    ("EURUSD", "H1", "EURUSD", 1.5),
    ("GBPUSD", "H1", "GBPUSD", 2.0),
    ("USDJPY", "H1", "USDJPY", 1.5),
    ("GOLD", "H4", "XAUUSD", 10.0),
]

STARTING_EQUITY = 100_000.0
RISK_PCT = 0.005
MAX_CONCURRENT = 3


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  Sharpe={s['sharpe']:.2f}"


def main():
    trades_by_market_full = {}
    signaled_by_market = {}
    for key, tf, label, spread_bps in MARKETS:
        print(f"Fetching {label} {tf} {DATA_START} -> {DATA_END} ...")
        df = fetch_timeframe(key, tf, DATA_START, DATA_END)
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        signaled = run_pipeline(df)
        cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
        trades = simulate_trades(signaled, cfg)
        trades_by_market_full[label] = (trades, spread_bps)
        signaled_by_market[label] = signaled

    # ================================================================ p6_1/p6_4
    print("\n" + "=" * 100)
    print("p6_1/p6_4 - WALK-FORWARD UEBER 3 ROLLIERENDE SUB-PERIODEN")
    print("=" * 100)
    for name, start, end in PERIODS:
        start_ts, end_ts = pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC")
        print(f"\n{name}:")
        for label, (trades, _) in trades_by_market_full.items():
            sig_idx = signaled_by_market[label].index
            period_idx = sig_idx[(sig_idx >= start_ts) & (sig_idx < end_ts)]
            t = trades[(trades["entry_time"] >= start_ts) & (trades["entry_time"] < end_ts)]
            print(f"  {label:<8} {fmt(summarize(t, period_idx))}")

    # ================================================================ p6_2
    print("\n" + "=" * 100)
    print("p6_2 - MONTE-CARLO-BOOTSTRAP (ou_paper_backtest/monte_carlo.py, block_size=20, n_sims=2000)")
    print(f"Letzte Sub-Periode 2022-2026, Portfolio, Risk {RISK_PCT:.1%}/Trade, max {MAX_CONCURRENT} gleichzeitige Positionen")
    print("=" * 100)
    recent_start = pd.Timestamp("2022-01-01", tz="UTC")
    trades_recent = {label: t[t["entry_time"] >= recent_start] for label, (t, _) in trades_by_market_full.items()}
    full_index = None
    for label, sig in signaled_by_market.items():
        idx = sig.index[sig.index >= recent_start]
        full_index = idx if full_index is None else full_index.union(idx)

    sim = simulate_account(trades_recent, starting_equity=STARTING_EQUITY, risk_pct=RISK_PCT, max_concurrent=MAX_CONCURRENT)
    daily = equity_curve_to_daily_returns(sim["equity_curve"], full_index)
    mc = run_monte_carlo(daily, initial_equity=STARTING_EQUITY, block_size=20, n_sims=2000, seed=42)
    s = mc["summary"]
    print(f"real path: n_taken={sim['n_taken']}, n_skipped={sim['n_skipped']}, final_equity={sim['final_equity']:,.0f}")
    for p in (5, 25, 50, 75, 95):
        dd_p = np.percentile(s["max_drawdown_pct"], p)
        ret_p = np.percentile(s["total_return_pct"], p)
        print(f"  P{p:>2}  MaxDD={dd_p:>8.2f}%   TotalReturn={ret_p:>+9.2f}%")
    for limit in (0.10, 0.20, 0.30):
        breach = (s["max_drawdown_pct"] < -limit * 100).mean()
        print(f"  P(MaxDD > {limit:.0%}) = {breach:.1%}", end="   ")
    print(f"\n  Median Sharpe={np.nanmedian(s['sharpe']):.2f}   Median Calmar={np.nanmedian(s['calmar']):.2f}")

    # ================================================================ p6_3
    print("\n" + "=" * 100)
    print("p6_3 - KOSTEN-SENSITIVITAET (letzte Sub-Periode 2022-2026, je Markt)")
    print("=" * 100)
    spread_candidates = [1.0, 2.0, 3.0, 5.0, 8.0, 10.0, 15.0, 20.0, 30.0, 50.0]
    for key, tf, label, assumed_bps in MARKETS:
        sig = signaled_by_market[label]
        sig_recent = sig[sig.index >= recent_start]
        print(f"\n{label} (angenommen: {assumed_bps}bps):")
        breakeven = None
        for sp in spread_candidates:
            cfg = BacktestConfig(spread_bps=sp, stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
            t = simulate_trades(sig_recent, cfg)
            if t.empty:
                print(f"  spread={sp:>6.1f}bps  n=0")
                continue
            total_ret = (1 + t["return_pct"]).prod() - 1
            pf = t.loc[t["return_pct"] > 0, "return_pct"].sum() / -t.loc[t["return_pct"] < 0, "return_pct"].sum() if (t["return_pct"] < 0).any() else float("inf")
            print(f"  spread={sp:>6.1f}bps  n={len(t):>3}  TotalReturn={total_ret:>+8.2%}  PF={pf:.3f}")
            if breakeven is None and total_ret < 0:
                breakeven = sp
        if breakeven:
            prior = spread_candidates[spread_candidates.index(breakeven) - 1] if spread_candidates.index(breakeven) > 0 else 0.0
            print(f"  -> Breakeven-Spread zwischen {prior:.1f} und {breakeven:.1f} bps (Sicherheitsfaktor vs. Annahme {assumed_bps}bps: {breakeven / assumed_bps:.1f}x)")
        else:
            print(f"  -> bleibt profitabel im gesamten getesteten Bereich")


if __name__ == "__main__":
    main()
