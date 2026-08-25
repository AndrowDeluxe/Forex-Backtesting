"""Phase 6 gap-fill for the "Haupt-Bot" (mt5_trend_pullback): p6_2 Monte-Carlo
bootstrap of the trade sequence. Everything else in Phase 6 was already done
across mt5_trend_pullback's 15 research scripts (p6_1 walk-forward/regime-shift
OOS split: research_mt5_trend_pullback_regime_shift.py; p6_3 cost sensitivity:
research_mt5_trend_pullback_spread_sensitivity.py; p6_4 multi-year/regime:
research_mt5_trend_pullback_master_table.py's 2016-2026 span + _small_timeframes.py
+ _regime_shift.py's timeframe comparison) - only the Monte Carlo bootstrap was
missing (grepped for it across all 15 scripts, no hit). Reuses the established
ou_paper_backtest/monte_carlo.py pattern (block_size=20, n_sims=2000) rather than
building an ad-hoc bootstrap - see knowledge/projects/gold-ctnl-edge-portfolio.md
for why that distinction matters (a prior session built its own bootstrap instead
of reusing this one).

Uses the same trusted regime-shifted OOS window as master_table.csv
(2024-07-01 -> 2026-08-01, bot DEFAULT config - not the "optimized" filter combo
that overfit in research_mt5_trend_pullback_regime_shift.py) and the bot's real
portfolio constraint (max 3 concurrent positions across all 5 markets,
mt5_trend_pullback/account_simulation.py), at all 4 risk levels already used in
master_table.csv (0.5/1.0/1.5/2.0%) so the two tables read side by side.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "ou_paper_backtest"))  # monte_carlo.py does a bare `import config` resolved here

import numpy as np
import pandas as pd

from combined_strategy.data import fetch_timeframe
from gold_smc_htf_ltf.concurrent_backtest import equity_curve_to_daily_returns
from monte_carlo import run_monte_carlo
from mt5_trend_pullback.account_simulation import simulate_account
from mt5_trend_pullback.pipeline import ATR_STOP_MULT, RR_RATIO, run_pipeline
from strategy.backtest import BacktestConfig, simulate_trades

pd.set_option("display.width", 160)

DATA_START, DATA_END = "2016-01-01", "2026-08-01"
NEW_SPLIT = pd.Timestamp("2024-07-01", tz="UTC")

MARKETS = [
    ("GOLD", "H1", "XAUUSD", 10.0),
    ("SILVER", "H1", "XAGUSD", 10.0),
    ("PLATINUM", "H1", "XPTUSD", 10.0),
    ("CHFJPY", "H4", "CHFJPY", 3.0),
    ("USDJPY", "H4", "USDJPY", 1.5),
]

STARTING_EQUITY = 100_000.0
RISK_LEVELS = [0.005, 0.01, 0.015, 0.02]
MAX_CONCURRENT = 3


def main():
    trades_by_market_oos = {}
    full_index_parts = []
    for key, tf, label, spread_bps in MARKETS:
        print(f"Fetching {label} {tf} {DATA_START} -> {DATA_END} ...")
        df = fetch_timeframe(key, tf, DATA_START, DATA_END)
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        signaled = run_pipeline(df)
        cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
        trades = simulate_trades(signaled, cfg)
        oos_t = trades[trades["entry_time"] >= NEW_SPLIT]
        trades_by_market_oos[label] = oos_t
        full_index_parts.append(signaled.index[signaled.index >= NEW_SPLIT])

    full_index = full_index_parts[0]
    for idx in full_index_parts[1:]:
        full_index = full_index.union(idx)

    print("\n" + "=" * 100)
    print("p6_2 - MONTE-CARLO-BOOTSTRAP (ou_paper_backtest/monte_carlo.py, block_size=20, n_sims=2000)")
    print(f"OOS-Fenster {NEW_SPLIT.date()} -> {DATA_END} (Portfolio, max {MAX_CONCURRENT} gleichzeitige Positionen)")
    print("=" * 100)

    for risk_pct in RISK_LEVELS:
        sim = simulate_account(trades_by_market_oos, starting_equity=STARTING_EQUITY, risk_pct=risk_pct, max_concurrent=MAX_CONCURRENT)
        daily = equity_curve_to_daily_returns(sim["equity_curve"], full_index)
        mc = run_monte_carlo(daily, initial_equity=STARTING_EQUITY, block_size=20, n_sims=2000, seed=42)
        s = mc["summary"]

        print(f"\nRisk {risk_pct:.1%}/Trade  (real path: n_taken={sim['n_taken']}, n_skipped={sim['n_skipped']}, final_equity={sim['final_equity']:,.0f})")
        for p in (5, 25, 50, 75, 95):
            dd_p = np.percentile(s["max_drawdown_pct"], p)
            ret_p = np.percentile(s["total_return_pct"], p)
            print(f"  P{p:>2}  MaxDD={dd_p:>8.2f}%   TotalReturn={ret_p:>+9.2f}%")
        for limit in (0.10, 0.20, 0.30):
            breach = (s["max_drawdown_pct"] < -limit * 100).mean()
            print(f"  P(MaxDD > {limit:.0%}) = {breach:.1%}", end="   ")
        print(f"\n  Median Sharpe={np.nanmedian(s['sharpe']):.2f}   Median Calmar={np.nanmedian(s['calmar']):.2f}")


if __name__ == "__main__":
    main()
