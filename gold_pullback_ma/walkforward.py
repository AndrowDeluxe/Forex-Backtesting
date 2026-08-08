"""Expanding-window walk-forward for the pullback strategy's `n_down_days`
parameter - same discipline as asian_range_breakout/walkforward.py, but for
a strategy design parameter (which N to trade) rather than a post-hoc
filter threshold: for each test year, pick whichever N looked best on
strictly-prior data (min_train_trades gate), then apply that choice
forward to the test year untouched - no peeking at the test year itself
when choosing N."""

import pandas as pd

from gold_pullback_ma.engine import simulate_pullback
from strategy.metrics import trade_stats


def run_pullback_walk_forward(
    daily_ohlc: pd.DataFrame,
    ma_window: int,
    n_candidates: list[int],
    start_test_year: int,
    end_test_year: int,
    min_train_trades: int = 20,
    cost_bps: float = 5.0,
) -> pd.DataFrame:
    all_trades = {
        n: simulate_pullback(daily_ohlc, ma_window=ma_window, n_down_days=n, cost_bps=cost_bps)
        for n in n_candidates
    }

    rows = []
    for year in range(start_test_year, end_test_year + 1):
        test_start = pd.Timestamp(f"{year}-01-01")
        test_end = pd.Timestamp(f"{year}-12-31")

        best_n, best_pf = None, -float("inf")
        for n, trades in all_trades.items():
            train = trades[trades["entry_time"] < test_start]
            if len(train) < min_train_trades:
                continue
            pf = trade_stats(train)["profit_factor"]
            if pf > best_pf:
                best_n, best_pf = n, pf

        if best_n is None:
            rows.append({"year": year, "chosen_n": None, "train_pf": float("nan"), "n_trades": 0, "win_rate": float("nan"), "profit_factor": float("nan")})
            continue

        test_trades = all_trades[best_n]
        test_trades = test_trades[(test_trades["entry_time"] >= test_start) & (test_trades["entry_time"] <= test_end)]
        wf_stats = trade_stats(test_trades)
        rows.append(
            {
                "year": year,
                "chosen_n": best_n,
                "train_pf": best_pf,
                "n_trades": wf_stats["n_trades"],
                "win_rate": wf_stats["win_rate"],
                "profit_factor": wf_stats["profit_factor"],
            }
        )

    return pd.DataFrame(rows)
