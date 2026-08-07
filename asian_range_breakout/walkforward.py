"""Walk-forward validation of the ADX<15-Filter (see filters.py): for each
test year, re-check whether ADX<15 is still the weakest bucket using ONLY
trades BEFORE that year (an expanding training window - no full-sample
hindsight), then apply the filter that year only if the training-only check
confirms it. Reports each year's out-of-sample result with vs. without the
filter, plus whether the filter was confirmed that year - tests whether the
finding is a genuinely stable, forward-usable rule rather than an artifact
of looking at the whole 10.5y sample at once."""

import pandas as pd

from strategy.metrics import trade_stats

_ADX_BINS = [0, 15, 25, 35, 200]
_ADX_LABELS = ["<15", "15-25", "25-35", ">35"]


def _adx_filter_confirmed(train: pd.DataFrame, min_bucket_trades: int = 30) -> bool:
    """True if, using ONLY `train`, the <15 bucket has both enough trades to
    judge and a strictly lower profit factor than every other bucket."""
    if train.empty:
        return False
    t = train.copy()
    t["bucket"] = pd.cut(t["adx_at_entry"], bins=_ADX_BINS, labels=_ADX_LABELS)
    stats_by_bucket = {}
    for b, g in t.groupby("bucket", observed=True):
        stats_by_bucket[str(b)] = trade_stats(g)

    low = stats_by_bucket.get("<15")
    others = [s for label, s in stats_by_bucket.items() if label != "<15"]
    if low is None or low["n_trades"] < min_bucket_trades or not others:
        return False
    return all(low["profit_factor"] < s["profit_factor"] for s in others if s["n_trades"] >= min_bucket_trades)


def run_walk_forward(
    trades: pd.DataFrame, start_test_year: int, end_test_year: int, min_train_trades: int = 200
) -> pd.DataFrame:
    rows = []
    for year in range(start_test_year, end_test_year + 1):
        train = trades[trades["entry_time"].dt.year < year]
        test = trades[trades["entry_time"].dt.year == year]
        if test.empty or len(train) < min_train_trades:
            continue

        confirmed = _adx_filter_confirmed(train)
        base = trade_stats(test)
        test_filtered = test[test["adx_at_entry"] >= 15] if confirmed else test
        filtered = trade_stats(test_filtered)

        rows.append(
            {
                "test_year": year,
                "train_n_trades": len(train),
                "filter_confirmed_on_train": confirmed,
                "n_trades_unfiltered": base["n_trades"],
                "pf_unfiltered": base["profit_factor"],
                "n_trades_walkforward": filtered["n_trades"],
                "pf_walkforward": filtered["profit_factor"],
                "win_rate_walkforward": filtered["win_rate"],
            }
        )
    return pd.DataFrame(rows)


def _trend_bias_confirmed(train: pd.DataFrame, min_bucket_trades: int = 100) -> bool:
    """True if, using ONLY `train`, trades aligned with Gold's own daily
    trend (see filters.py::attach_series_level - `aligned` column expected
    to already be attached) have both enough trades to judge and a strictly
    higher profit factor than counter-trend trades. Same expanding-window
    walk-forward discipline as _adx_filter_confirmed."""
    if train.empty or "aligned" not in train.columns:
        return False
    aligned_stats = trade_stats(train[train["aligned"]])
    counter_stats = trade_stats(train[~train["aligned"]])
    if aligned_stats["n_trades"] < min_bucket_trades or counter_stats["n_trades"] < min_bucket_trades:
        return False
    return aligned_stats["profit_factor"] > counter_stats["profit_factor"]


def run_trend_bias_walk_forward(
    trades_with_bias: pd.DataFrame, start_test_year: int, end_test_year: int, min_train_trades: int = 200
) -> pd.DataFrame:
    """Same expanding-window logic as run_walk_forward, but for the Gold
    daily-trend-bias filter instead of ADX. `trades_with_bias` must already
    have an `aligned` boolean column (see filters.py::attach_series_level +
    scripts/research_gold_trend_bias_seasonality.py for how it's built)."""
    rows = []
    for year in range(start_test_year, end_test_year + 1):
        train = trades_with_bias[trades_with_bias["entry_time"].dt.year < year]
        test = trades_with_bias[trades_with_bias["entry_time"].dt.year == year]
        if test.empty or len(train) < min_train_trades:
            continue

        confirmed = _trend_bias_confirmed(train)
        base = trade_stats(test)
        test_filtered = test[test["aligned"]] if confirmed else test
        filtered = trade_stats(test_filtered)

        rows.append(
            {
                "test_year": year,
                "train_n_trades": len(train),
                "filter_confirmed_on_train": confirmed,
                "n_trades_unfiltered": base["n_trades"],
                "pf_unfiltered": base["profit_factor"],
                "n_trades_walkforward": filtered["n_trades"],
                "pf_walkforward": filtered["profit_factor"],
                "win_rate_walkforward": filtered["win_rate"],
            }
        )
    return pd.DataFrame(rows)
