"""Cross-checks the Nasdaq-derived ORB filter (long-only + ADX>=25 at
entry) on the other 4 assets already tested in the baseline pass
(EUR/USD, Gold, Oil, SP500) - to see whether this is a general
trend-continuation pattern or a Nasdaq-specific (beta/trend) artifact.
Same yearly walk-forward reporting as every other research_*.py script.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from combined_strategy.data import fetch_timeframe
from orb_strategy.pipeline import run_orb_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import summarize
from strategy.real_data import fetch_pair_history

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

YEARS = list(range(2017, 2027))
OTHER_ASSETS = ["OIL", "GOLD", "SP500"]
START, END = "2016-07-28", "2026-07-28"
STOP_MULT = 2.0


def _lower_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})


def run_variant(df: pd.DataFrame, label: str, **filter_kwargs):
    signaled = run_orb_pipeline(df, atr_n=14, atr_mult=1.0, **filter_kwargs)
    cfg = BacktestConfig(spread_bps=0.3, stop_atr_mult=STOP_MULT, use_vwap_target=False)
    trades = simulate_trades(signaled, cfg)
    if trades.empty:
        print(f"  {label}: 0 trades")
        return

    full = summarize(trades, signaled.index)
    rows = []
    for year in YEARS:
        yr_df = signaled[signaled.index.year == year]
        if yr_df.empty:
            continue
        yr_trades = trades[trades["entry_time"].dt.year == year]
        if yr_trades.empty:
            rows.append({"year": year, "n_trades": 0, "avg_return_bps": None})
            continue
        s = summarize(yr_trades, yr_df.index)
        rows.append({"year": year, "n_trades": s["n_trades"], "avg_return_bps": s["avg_return_pct"] * 1e4, "sharpe": s["sharpe"]})
    yearly = pd.DataFrame(rows).set_index("year")
    active = yearly[yearly["n_trades"] > 0]
    mean_yearly_sharpe = active["sharpe"].mean() if not active.empty else float("nan")
    pos_years = (active["avg_return_bps"] > 0).sum()

    print(
        f"  {label}: n={full['n_trades']}, sharpe_pooled={full['sharpe']:.2f}, "
        f"mean_yearly_sharpe={mean_yearly_sharpe:.2f}, pf={full['profit_factor']:.2f}, "
        f"win_rate={full['win_rate']:.1%}, years_positive={pos_years}/{len(active)}"
    )


def main():
    print("Loading EUR/USD M15 (reference)...")
    eurusd = fetch_pair_history("EURUSD", START, END)
    assets = {"EUR/USD": eurusd}
    for key in OTHER_ASSETS:
        print(f"Loading {key} M15 (cached after first run)...")
        assets[key] = _lower_ohlcv(fetch_timeframe(key, "M15", START, END))

    for name, df in assets.items():
        print(f"\n{'=' * 15} {name} {'=' * 15}")
        run_variant(df, "Baseline (Long+Short)")
        run_variant(df, "Long-only", long_only=True)
        run_variant(df, "Long-only + ADX>=25", long_only=True, adx_min=25.0)


if __name__ == "__main__":
    main()
