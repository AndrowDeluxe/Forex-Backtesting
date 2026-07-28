"""Screen alternative session definitions (Sec. 6.1: London 07-17 GMT vs.
NY 13-22 GMT vs. a 24h rolling reset) crossed with the two signal-filter
variants from `research_refinement.py` (plain Eq. 14 vs. the ADX-ceiling
refinement).

In-sample only (2016-07-28 .. 2023-07-28). NOTE ON METHODOLOGY: the
2023-07-28..2026-07-28 window was already inspected once in
research_refinement.py. Looking at it again here for a *different* family of
candidates is a second peek at the same holdout - it no longer functions as a
clean, unbiased out-of-sample estimate the way the first look did. Treated
here as a final confirmatory read, not as grounds for further tuning.
"""

import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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

SESSION_VARIANTS = {
    "rollover_22h_current": dict(reset_hour=22, session_start_hour=None, session_end_hour=None),
    "rollover_5h_ny_midnight": dict(reset_hour=5, session_start_hour=None, session_end_hour=None),
    "london_07_17": dict(reset_hour=22, session_start_hour=7, session_end_hour=17),
    "ny_13_22": dict(reset_hour=22, session_start_hour=13, session_end_hour=22),
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
    print("Loading real Dukascopy history for all pairs (cached after first run)...")
    data = load_all_pairs_real("2016-07-28", "2026-07-28")

    print(f"\n=== In-sample screen (2016-07-28 .. {SPLIT_DATE.date()}) ===")
    rows = []
    for session_name, session_params in SESSION_VARIANTS.items():
        for filter_name, filter_params in FILTER_VARIANTS.items():
            candidate = f"{session_name} | {filter_name}"
            pair_sharpes, pair_returns, pair_trades = [], [], []
            for pair in PAIRS:
                signaled = run_indicator_pipeline(data[pair], **session_params, **filter_params)
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
            print(f"  {candidate:45s} done")

    screen = pd.DataFrame(rows).set_index("candidate").sort_values("mean_sharpe", ascending=False)
    print("\n", screen)

    winner_key = screen.index[0]
    winner_session_name, winner_filter_name = [s.strip() for s in winner_key.split("|")]
    winner_session = SESSION_VARIANTS[winner_session_name]
    winner_filter = FILTER_VARIANTS[winner_filter_name]
    print(f"\n=== Winner (in-sample): {winner_key} ===")

    print(
        f"\n=== Confirmatory out-of-sample read ({SPLIT_DATE.date()} .. 2026-07-28) "
        "- SECOND look at this holdout, treat as final, not a tuning signal ==="
    )
    oos_rows = []
    for pair in PAIRS:
        signaled = run_indicator_pipeline(data[pair], **winner_session, **winner_filter)
        s = backtest_slice(signaled, start=SPLIT_DATE)
        oos_rows.append({"pair": pair, **s})
    oos = pd.DataFrame(oos_rows).set_index("pair")
    print(oos[["n_trades", "win_rate", "avg_return_pct", "sharpe", "calmar", "max_drawdown"]])


if __name__ == "__main__":
    main()
