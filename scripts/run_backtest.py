"""End-to-end run across all 6 pairs from the paper's planned empirical
programme (Sec. 7): load data -> indicators -> signal -> backtest ->
metrics -> regime decomposition -> walk-forward stability -> breakeven spread.

Usage: python scripts/run_backtest.py [synthetic|real]  (default: real)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from strategy.backtest import BacktestConfig, simulate_trades
from strategy.data import PAIRS, generate_all_pairs
from strategy.metrics import breakeven_spread_bps, regime_decomposition, summarize
from strategy.real_data import load_all_pairs_real
from strategy.signals import run_indicator_pipeline
from strategy.walkforward import fold_performance, stability_summary

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)


def run_pair(pair: str, df: pd.DataFrame, config: BacktestConfig) -> dict:
    signaled = run_indicator_pipeline(df)
    trades = simulate_trades(signaled, config)
    summary = summarize(trades, df.index)

    folds = fold_performance(trades, df.index, fold="MS")
    stability = stability_summary(folds)

    regimes = regime_decomposition(trades)

    breakeven = breakeven_spread_bps(signaled, config) if not trades.empty else 0.0

    return {
        "pair": pair,
        "summary": summary,
        "stability": stability,
        "regimes": regimes,
        "breakeven_spread_bps": breakeven,
        "trades": trades,
    }


def main():
    source = sys.argv[1] if len(sys.argv) > 1 else "real"
    config = BacktestConfig(spread_bps=0.3, stop_atr_mult=0.5)

    if source == "synthetic":
        data = generate_all_pairs(start="2023-01-01", end="2026-01-01", freq_minutes=15, seed=42)
    elif source == "real":
        print("Loading real Dukascopy history for all pairs (cached after first run)...")
        data = load_all_pairs_real("2016-07-28", "2026-07-28")
    else:
        raise SystemExit(f"unknown source '{source}', expected 'synthetic' or 'real'")

    results = {}
    for pair, df in data.items():
        print(f"--- {pair} ---")
        results[pair] = run_pair(pair, df, config)
        s = results[pair]["summary"]
        st = results[pair]["stability"]
        print(
            f"trades={s['n_trades']:>5}  win_rate={s['win_rate']:.2%}  "
            f"avg_ret={s['avg_return_pct']*1e4:6.2f}bps  sharpe={s['sharpe']:6.2f}  "
            f"calmar={s['calmar']:6.2f}  max_dd={s['max_drawdown']:.2%}  "
            f"breakeven_spread={results[pair]['breakeven_spread_bps']:.2f}bps  "
            f"active_folds={st.get('n_active_folds', 0)}/{st.get('n_folds', 0)}  "
            f"pct_folds_pos={st.get('pct_folds_positive', float('nan')):.0%}"
        )

    print("\n=== Portfolio summary (equal-weight across pairs) ===")
    summary_table = pd.DataFrame({p: r["summary"] for p, r in results.items()}).T
    print(summary_table[["n_trades", "win_rate", "avg_return_pct", "sharpe", "calmar", "max_drawdown"]])

    print("\n=== Regime decomposition, EURUSD ===")
    print(results["EURUSD"]["regimes"])

    return results


if __name__ == "__main__":
    main()
