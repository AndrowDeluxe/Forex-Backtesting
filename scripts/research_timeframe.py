"""Last structural probe: M15 vs. H1 bars, crossed with the two filter
variants, at the session definition that won `research_session.py`
(22h UTC rollover). In-sample only (2016-07-28 .. 2023-07-28).

NOTE ON METHODOLOGY: this is the third look at the same
2023-07-28..2026-07-28 window across research_refinement.py,
research_session.py and this script. Per prior agreement with the user,
this is the last structural change probed - after this, no further
parameter tuning against this holdout, regardless of outcome.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import dukascopy_python
import pandas as pd

from strategy.backtest import BacktestConfig, simulate_trades
from strategy.data import PAIRS
from strategy.metrics import summarize
from strategy.real_data import load_all_pairs_real
from strategy.signals import run_indicator_pipeline

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

SPLIT_DATE = pd.Timestamp("2023-07-28", tz="UTC")
BASE_CONFIG = BacktestConfig(spread_bps=0.3, stop_atr_mult=0.5)

TIMEFRAMES = {
    "M15": dukascopy_python.INTERVAL_MIN_15,
    "H1": dukascopy_python.INTERVAL_HOUR_1,
}

FILTER_VARIANTS = {
    "plain_eq14": dict(adx_ceiling=None, theta_multiplier=1.0),
    "adx_ceiling_25_theta1.5": dict(adx_ceiling=25.0, theta_multiplier=1.5),
}


def backtest_slice(signaled: pd.DataFrame, start=None, end=None) -> dict:
    sliced = signaled
    if start is not None:
        sliced = sliced[sliced.index >= start]
    if end is not None:
        sliced = sliced[sliced.index < end]
    trades = simulate_trades(sliced, BASE_CONFIG)
    return summarize(trades, sliced.index)


def main():
    rows = []
    data_by_tf = {}
    for tf_name, interval in TIMEFRAMES.items():
        print(f"Loading real Dukascopy history ({tf_name}, cached after first run)...")
        data_by_tf[tf_name] = load_all_pairs_real("2016-07-28", "2026-07-28", interval=interval)

    print(f"\n=== In-sample screen (2016-07-28 .. {SPLIT_DATE.date()}) ===")
    for tf_name in TIMEFRAMES:
        for filter_name, filter_params in FILTER_VARIANTS.items():
            candidate = f"{tf_name} | {filter_name}"
            pair_sharpes, pair_returns, pair_trades = [], [], []
            for pair in PAIRS:
                signaled = run_indicator_pipeline(data_by_tf[tf_name][pair], **filter_params)
                s = backtest_slice(signaled, end=SPLIT_DATE)
                pair_sharpes.append(s["sharpe"])
                pair_returns.append(s["avg_return_pct"])
                pair_trades.append(s["n_trades"])
            rows.append(
                {
                    "candidate": candidate,
                    "mean_sharpe": sum(pair_sharpes) / len(pair_sharpes),
                    "pairs_sharpe_pos": sum(sh > 0 for sh in pair_sharpes),
                    "mean_avg_return_bps": sum(pair_returns) / len(pair_returns) * 1e4,
                    "min_trades": min(pair_trades),
                    "total_trades": sum(pair_trades),
                }
            )
            print(f"  {candidate:35s} done")

    screen = pd.DataFrame(rows).set_index("candidate").sort_values("mean_sharpe", ascending=False)
    print("\n", screen)

    winner_key = screen.index[0]
    winner_tf_name, winner_filter_name = [s.strip() for s in winner_key.split("|")]
    winner_filter = FILTER_VARIANTS[winner_filter_name]
    print(f"\n=== Winner (in-sample): {winner_key} ===")

    print(
        f"\n=== Confirmatory out-of-sample read ({SPLIT_DATE.date()} .. 2026-07-28) "
        "- THIRD and final look at this holdout ==="
    )
    oos_rows = []
    for pair in PAIRS:
        signaled = run_indicator_pipeline(data_by_tf[winner_tf_name][pair], **winner_filter)
        s = backtest_slice(signaled, start=SPLIT_DATE)
        oos_rows.append({"pair": pair, **s})
    oos = pd.DataFrame(oos_rows).set_index("pair")
    print(oos[["n_trades", "win_rate", "avg_return_pct", "sharpe", "calmar", "max_drawdown"]])


if __name__ == "__main__":
    main()
