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


def run_exit_time_walk_forward(
    trades_by_exit_time: dict[str, pd.DataFrame],
    default_exit: str,
    start_test_year: int,
    end_test_year: int,
    min_train_trades: int = 30,
) -> pd.DataFrame:
    """Same expanding-window discipline as the other walk-forward helpers,
    but choosing among ExitTime candidates instead of a fixed filter
    threshold - each dict value is the full production-filter-stack trades
    DataFrame simulated at that exit time (see
    scripts/research_gold_exit_time_walk_forward.py). For each test year,
    picks whichever candidate had the best profit factor on strictly-prior
    years, then applies that choice forward - compared against always
    keeping `default_exit` (the current production value)."""
    rows = []
    for year in range(start_test_year, end_test_year + 1):
        best_et, best_pf = None, -float("inf")
        for et, trades in trades_by_exit_time.items():
            train = trades[trades["entry_time"].dt.year < year]
            if len(train) < min_train_trades:
                continue
            pf = trade_stats(train)["profit_factor"]
            if pf > best_pf:
                best_et, best_pf = et, pf

        default_test = trades_by_exit_time[default_exit]
        default_test = default_test[default_test["entry_time"].dt.year == year]
        base = trade_stats(default_test)

        if best_et is None:
            rows.append(
                {
                    "test_year": year,
                    "chosen_exit": None,
                    "train_pf": float("nan"),
                    "n_trades_default": base["n_trades"],
                    "pf_default": base["profit_factor"],
                    "n_trades_walkforward": base["n_trades"],
                    "pf_walkforward": base["profit_factor"],
                }
            )
            continue

        chosen_test = trades_by_exit_time[best_et]
        chosen_test = chosen_test[chosen_test["entry_time"].dt.year == year]
        wf = trade_stats(chosen_test)

        rows.append(
            {
                "test_year": year,
                "chosen_exit": best_et,
                "train_pf": best_pf,
                "n_trades_default": base["n_trades"],
                "pf_default": base["profit_factor"],
                "n_trades_walkforward": wf["n_trades"],
                "pf_walkforward": wf["profit_factor"],
            }
        )
    return pd.DataFrame(rows)


def run_execution_mode_walk_forward(
    trades_by_mode: dict[str, pd.DataFrame],
    default_mode: str,
    start_test_year: int,
    end_test_year: int,
    min_train_trades: int = 30,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Same expanding-window discipline as run_exit_time_walk_forward, but
    choosing between entry-execution modes (e.g. "wick" vs "overlay" from
    execution_overlay.py) instead of an ExitTime candidate - each dict value
    is the full production-filter-stack trades DataFrame simulated under
    that mode. For each test year, picks whichever mode had the best
    profit factor on strictly-prior years, then applies that choice
    forward - compared against always keeping `default_mode` (today's
    production entry rule). Returns (summary_df, stitched_trades_df) - the
    second so a risk-based position-sizing pass can be run on the actual
    walk-forward-selected trade sequence, not just its aggregate stats."""
    rows = []
    stitched = []
    for year in range(start_test_year, end_test_year + 1):
        best_mode, best_pf = None, -float("inf")
        for mode, trades in trades_by_mode.items():
            train = trades[trades["entry_time"].dt.year < year]
            if len(train) < min_train_trades:
                continue
            pf = trade_stats(train)["profit_factor"]
            if pf > best_pf:
                best_mode, best_pf = mode, pf

        default_test = trades_by_mode[default_mode]
        default_test = default_test[default_test["entry_time"].dt.year == year]
        base = trade_stats(default_test)

        if best_mode is None:
            rows.append(
                {
                    "test_year": year, "chosen_mode": None, "train_pf": float("nan"),
                    "n_trades_default": base["n_trades"], "pf_default": base["profit_factor"],
                    "n_trades_walkforward": base["n_trades"], "pf_walkforward": base["profit_factor"],
                }
            )
            stitched.append(default_test)
            continue

        chosen_test = trades_by_mode[best_mode]
        chosen_test = chosen_test[chosen_test["entry_time"].dt.year == year]
        wf = trade_stats(chosen_test)

        rows.append(
            {
                "test_year": year, "chosen_mode": best_mode, "train_pf": best_pf,
                "n_trades_default": base["n_trades"], "pf_default": base["profit_factor"],
                "n_trades_walkforward": wf["n_trades"], "pf_walkforward": wf["profit_factor"],
            }
        )
        stitched.append(chosen_test)

    summary = pd.DataFrame(rows)
    walkforward_trades = pd.concat(stitched).sort_values("entry_time").reset_index(drop=True) if stitched else pd.DataFrame()
    return summary, walkforward_trades


def _jump_activity_confirmed(train: pd.DataFrame, threshold: float, min_bucket_trades: int = 20) -> bool:
    """True if, using ONLY `train` and a threshold computed ONLY from
    `train`, the top-tercile jump-ratio bucket has both enough trades to
    judge and a strictly lower profit factor than the rest. Same expanding-
    window discipline as the other _*_confirmed helpers."""
    if train.empty or "jump_ratio_prior" not in train.columns:
        return False
    high = train[train["jump_ratio_prior"] > threshold]
    low = train[train["jump_ratio_prior"] <= threshold]
    high_stats, low_stats = trade_stats(high), trade_stats(low)
    if high_stats["n_trades"] < min_bucket_trades or low_stats["n_trades"] < min_bucket_trades:
        return False
    return low_stats["profit_factor"] > high_stats["profit_factor"]


def run_jump_activity_walk_forward(
    trades_with_jump: pd.DataFrame, start_test_year: int, end_test_year: int, min_train_trades: int = 30
) -> pd.DataFrame:
    """Same expanding-window logic as run_walk_forward, but for the
    jump-activity regime filter instead of ADX. `trades_with_jump` must
    already have a `jump_ratio_prior` column (see
    filters.py::attach_jump_activity). The top-tercile threshold is
    recomputed each test year from TRAIN-ONLY data (no lookahead into the
    test year's own jump-ratio distribution), then only applied if the
    training-only bucket comparison confirms it."""
    rows = []
    for year in range(start_test_year, end_test_year + 1):
        train = trades_with_jump[trades_with_jump["entry_time"].dt.year < year]
        test = trades_with_jump[trades_with_jump["entry_time"].dt.year == year]
        if test.empty or len(train) < min_train_trades:
            continue

        threshold = train["jump_ratio_prior"].quantile(2 / 3)
        confirmed = _jump_activity_confirmed(train, threshold)
        base = trade_stats(test)
        test_filtered = test[test["jump_ratio_prior"] <= threshold] if confirmed else test
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


_DELAY_BINS = [0, 3, 7, 999]
_DELAY_LABELS = ["<=3", "4-7", "8+"]


def _delay_filter_confirmed(train: pd.DataFrame, min_bucket_trades: int = 100) -> bool:
    """True if, using ONLY `train`, the fast-fill bucket (<=3 bars) has
    both enough trades to judge and a strictly higher profit factor than
    the slower buckets. Same expanding-window discipline as the other two
    _*_confirmed helpers."""
    if train.empty or "delay_bars" not in train.columns:
        return False
    t = train.copy()
    t["bucket"] = pd.cut(t["delay_bars"], bins=_DELAY_BINS, labels=_DELAY_LABELS, right=True)
    stats_by_bucket = {str(b): trade_stats(g) for b, g in t.groupby("bucket", observed=True)}

    fast = stats_by_bucket.get("<=3")
    others = [s for label, s in stats_by_bucket.items() if label != "<=3"]
    if fast is None or fast["n_trades"] < min_bucket_trades or not others:
        return False
    return all(fast["profit_factor"] > s["profit_factor"] for s in others if s["n_trades"] >= min_bucket_trades)


def _liquidity_filter_confirmed(train: pd.DataFrame, threshold: float, min_bucket_trades: int = 40) -> bool:
    """True if, using ONLY `train` and a threshold computed ONLY from
    `train`, the normal/good-liquidity bucket (friction_prior <= threshold)
    has both enough trades to judge and a strictly higher profit factor
    than the poor-liquidity bucket. Same expanding-window discipline as the
    other _*_confirmed helpers - see scripts/research_gold_liquidity_
    event_filters.py for how `friction_prior` is attached (Corwin-Schultz
    bid-ask-spread estimate, prior day, no lookahead)."""
    if train.empty or "friction_prior" not in train.columns:
        return False
    good = train[train["friction_prior"] <= threshold]
    poor = train[train["friction_prior"] > threshold]
    good_stats, poor_stats = trade_stats(good), trade_stats(poor)
    if good_stats["n_trades"] < min_bucket_trades or poor_stats["n_trades"] < min_bucket_trades:
        return False
    return good_stats["profit_factor"] > poor_stats["profit_factor"]


def run_liquidity_filter_walk_forward(
    trades_with_friction: pd.DataFrame, start_test_year: int, end_test_year: int, min_train_trades: int = 100
) -> pd.DataFrame:
    """Same expanding-window logic as run_jump_activity_walk_forward, but
    for the Corwin-Schultz GOLD-liquidity gate instead of the jump-ratio
    regime filter. `trades_with_friction` must already have a
    `friction_prior` column. The bottom-two-thirds threshold is recomputed
    each test year from TRAIN-ONLY data (no lookahead into the test year's
    own friction distribution), then only applied if the training-only
    bucket comparison confirms it."""
    rows = []
    for year in range(start_test_year, end_test_year + 1):
        train = trades_with_friction[trades_with_friction["entry_time"].dt.year < year]
        test = trades_with_friction[trades_with_friction["entry_time"].dt.year == year]
        if test.empty or len(train) < min_train_trades:
            continue

        threshold = train["friction_prior"].quantile(2 / 3)
        confirmed = _liquidity_filter_confirmed(train, threshold)
        base = trade_stats(test)
        test_filtered = test[test["friction_prior"] <= threshold] if confirmed else test
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


def run_delay_filter_walk_forward(
    trades_with_delay: pd.DataFrame, start_test_year: int, end_test_year: int, min_train_trades: int = 200
) -> pd.DataFrame:
    """Same expanding-window logic as run_walk_forward, but for the
    entry-fill-delay filter instead of ADX. `trades_with_delay` must already
    have a `delay_bars` column (see filters.py::attach_entry_delay)."""
    rows = []
    for year in range(start_test_year, end_test_year + 1):
        train = trades_with_delay[trades_with_delay["entry_time"].dt.year < year]
        test = trades_with_delay[trades_with_delay["entry_time"].dt.year == year]
        if test.empty or len(train) < min_train_trades:
            continue

        confirmed = _delay_filter_confirmed(train)
        base = trade_stats(test)
        test_filtered = test[test["delay_bars"] <= 3] if confirmed else test
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
