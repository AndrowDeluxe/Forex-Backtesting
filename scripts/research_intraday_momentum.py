"""Independent test of Seeck (2026)'s London-Open 30-minute intraday-momentum
signal on this repo's own Dukascopy M5 data -- see app_pages/fx_papers_202608.py
Tab 3 for the paper write-up. The paper's own claimed numbers (e.g. USDJPY OOS
Sortino +0.748, JPY-pair beta ~3.8x non-JPY) are NOT assumed here; this script
recomputes everything from scratch on our own data pull and compares against
those claims explicitly, rather than reporting them as if verified.

Three periods, matching the paper's own IS/OOS split plus a genuine holdout
the paper could not have seen (published mid-2026):
  IS      2012-01-01 .. 2018-12-31  (paper's in-sample)
  OOS     2019-01-01 .. 2024-12-31  (paper's out-of-sample)
  HOLDOUT 2025-01-01 .. 2026-08-01  (beyond the paper's own OOS end)

Significance (beta, permutation p-value) is computed on RAW (no-cost)
returns, matching the paper's Table 1. Performance (Sortino/Sharpe/win
rate) is computed on cost-adjusted returns, matching the paper's Table 2.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from intraday_momentum.costs import apply_costs
from intraday_momentum.data import PAIRS, load_all_pairs_m5
from intraday_momentum.metrics import summarize_period
from intraday_momentum.signals import generate_london_momentum_trades

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)
pd.set_option("display.float_format", lambda x: f"{x:,.4f}")

START, END = "2012-01-01", "2026-08-01"
PERIODS = {
    "IS_2012_2018": ("2012-01-01", "2018-12-31"),
    "OOS_2019_2024": ("2019-01-01", "2024-12-31"),
    "HOLDOUT_2025_2026": ("2025-01-01", "2026-08-01"),
}
JPY_PAIRS = {"AUDJPY", "GBPJPY", "USDJPY"}
NON_JPY_EXCL_GBPUSD = {"EURUSD"}  # paper explicitly excludes GBPUSD from this comparison (reversed signal)


def slice_period(trades: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    if trades.empty:
        return trades
    mask = (trades["entry_time"] >= pd.Timestamp(start, tz="UTC")) & (
        trades["entry_time"] <= pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
    )
    return trades[mask]


def main():
    print(f"Loading M5 Dukascopy history for {PAIRS} ({START} .. {END}), cached after first run...")
    data = load_all_pairs_m5(START, END)

    all_trades = {}
    for pair in PAIRS:
        print(f"  building signal/trades for {pair}...")
        trades = generate_london_momentum_trades(data[pair])
        trades = apply_costs(trades, pair)
        all_trades[pair] = trades
        print(f"    {len(trades)} total signalled days, {trades['entry_time'].min()} .. {trades['entry_time'].max()}")

    print("\n=== Per-pair, per-period results (raw-return significance, cost-adjusted performance) ===")
    rows = []
    for pair in PAIRS:
        for period_name, (p_start, p_end) in PERIODS.items():
            period_trades = slice_period(all_trades[pair], p_start, p_end)
            stats = summarize_period(period_trades)
            rows.append({"pair": pair, "period": period_name, **stats})
    results = pd.DataFrame(rows).set_index(["pair", "period"])
    print(results)

    print("\n=== JPY-amplification check (mean |beta|, JPY pairs vs. EURUSD; GBPUSD excluded per paper) ===")
    jpy_betas, non_jpy_betas = [], []
    for pair in PAIRS:
        oos = slice_period(all_trades[pair], *PERIODS["OOS_2019_2024"])
        stats = summarize_period(oos)
        if pair in JPY_PAIRS and not np.isnan(stats["beta"]):
            jpy_betas.append(abs(stats["beta"]))
        elif pair in NON_JPY_EXCL_GBPUSD and not np.isnan(stats["beta"]):
            non_jpy_betas.append(abs(stats["beta"]))
    if jpy_betas and non_jpy_betas:
        ratio = np.mean(jpy_betas) / np.mean(non_jpy_betas) if np.mean(non_jpy_betas) != 0 else np.nan
        print(f"  mean |beta| JPY pairs (OOS):     {np.mean(jpy_betas):.6f}")
        print(f"  mean |beta| EURUSD (OOS):        {np.mean(non_jpy_betas):.6f}")
        print(f"  ratio (paper claims ~3.8x):      {ratio:.2f}x")
    else:
        print("  insufficient data for JPY-amplification comparison")

    print("\n=== Comparison to the paper's own claimed OOS numbers (Seeck 2026, Table 1/2) ===")
    paper_claims = {
        "EURUSD": {"beta": 0.000536, "sortino": -0.756},
        "GBPUSD": {"beta": -0.000084, "sortino": None},
        "AUDJPY": {"beta": 0.000879, "sortino": None},
        "GBPJPY": {"beta": 0.000950, "sortino": -0.052},
        "USDJPY": {"beta": 0.000748, "sortino": 0.748},
    }
    for pair in PAIRS:
        oos = slice_period(all_trades[pair], *PERIODS["OOS_2019_2024"])
        stats = summarize_period(oos)
        claim = paper_claims[pair]
        print(
            f"  {pair}: our beta={stats['beta']:+.6f} (paper {claim['beta']:+.6f}), "
            f"our sortino={stats['sortino']:+.3f} (paper {claim['sortino']})"
        )

    print("\nDone. Results are this repo's own independent computation, not a copy of the paper's numbers.")
    return results


if __name__ == "__main__":
    main()
