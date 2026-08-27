"""Deep validation of the two filter candidates that survived the first
IS/OOS sweep in research_orb_filter_bank.py (Jump-Activity-Ratio top-tercile
exclusion, VIX-Level bottom-tercile exclusion - both improved OOS Sharpe/PF
on BOTH Nasdaq and SP500 with the same bucket/direction). Brings them up to
the same evidence bar Gold-ASB's Corwin-Schultz liquidity filter had to
clear before being considered for production (see scripts/research_gold_
liquidity_event_filters.py):

1. Structure-preserving (dwell-preserving) randomization inference
   (asian_range_breakout.randomization) - is the filter's specific
   footprint (which trades it keeps/drops, and when) better than an
   arbitrary signal-blind footprint with the exact same shape (same run
   count, same run lengths, same total kept count)? Tested on the FULL
   trade sample (2016-2026), same convention as the Gold-ASB script.
2. Expanding-window walk-forward (asian_range_breakout.walkforward) - for
   each test year 2019-2026, using ONLY trades strictly before that year,
   re-derive the tercile threshold and re-check the filter is still the
   weaker bucket BEFORE applying it that year. Jump-activity reuses
   run_jump_activity_walk_forward unmodified; VIX gets an analogous
   bottom-tercile-is-weak walk-forward helper (no premade one exists yet).

ORB's total sample (~100-125 trades/asset in 10 years) is far smaller than
Gold-ASB's - both tests are run and reported honestly, but treat thin-year
walk-forward buckets (min_train_trades=30, single-digit test-year trade
counts in early years) with the same caution the rest of this project
applies to small samples."""

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from asian_range_breakout.randomization import dwell_preserving_test
from asian_range_breakout.vix import fetch_vix_daily
from asian_range_breakout.walkforward import run_jump_activity_walk_forward
from bond_yield_indicator.friction import corwin_schultz_spread  # noqa: F401 (not used, kept for parity/context)
from combined_strategy.data import fetch_timeframe
from research_orb_filter_bank import SPLIT, START, WEEKDAY_FILTER, _lower_ohlcv, _prior_value, build_frame, daily_series
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import trade_stats

warnings.filterwarnings("ignore")
pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

END = "2026-07-28"
N_SHUFFLES = 1000


def profit_factor(trades: pd.DataFrame) -> float:
    return trade_stats(trades)["profit_factor"]


def report_randomization(name: str, result: dict):
    print(f"\n--- Randomisierung: {name} ---")
    print(f"  behaelt {result['n_kept']} / {result['n_total']} Trades   tatsaechlicher PF = {result['actual_metric']:.3f}")
    for method in ("rotation", "run_permutation"):
        r = result[method]
        print(
            f"  [{method:>15}]  Null-PF Mittel={r['null_mean']:.3f}  std={r['null_std']:.3f}  "
            f"[p05={r['null_p05']:.3f}, p95={r['null_p95']:.3f}]  "
            f"p-value(null>=actual)={r['p_value']:.3f}  (n_valid={r['n_valid_shuffles']}/{N_SHUFFLES})"
        )


def _vix_confirmed(train: pd.DataFrame, threshold: float, min_bucket_trades: int = 20) -> bool:
    """Analogous to walkforward._jump_activity_confirmed, but for the
    bottom-tercile-VIX-is-weak pattern found in research_orb_filter_bank.py
    (filter #11): True if, using ONLY `train` and a threshold computed ONLY
    from `train`, the low-VIX bucket has both enough trades to judge and a
    strictly lower profit factor than the rest."""
    if train.empty or "vix_prior" not in train.columns:
        return False
    low = train[train["vix_prior"] <= threshold]
    rest = train[train["vix_prior"] > threshold]
    low_stats, rest_stats = trade_stats(low), trade_stats(rest)
    if low_stats["n_trades"] < min_bucket_trades or rest_stats["n_trades"] < min_bucket_trades:
        return False
    return rest_stats["profit_factor"] > low_stats["profit_factor"]


def run_vix_walk_forward(trades_with_vix: pd.DataFrame, start_test_year: int, end_test_year: int, min_train_trades: int = 30) -> pd.DataFrame:
    rows = []
    for year in range(start_test_year, end_test_year + 1):
        train = trades_with_vix[trades_with_vix["entry_time"].dt.year < year]
        test = trades_with_vix[trades_with_vix["entry_time"].dt.year == year]
        if test.empty or len(train) < min_train_trades:
            continue

        threshold = train["vix_prior"].quantile(1 / 3)
        confirmed = _vix_confirmed(train, threshold)
        base = trade_stats(test)
        test_filtered = test[test["vix_prior"] > threshold] if confirmed else test
        filtered = trade_stats(test_filtered)

        rows.append({
            "test_year": year, "train_n_trades": len(train), "filter_confirmed_on_train": confirmed,
            "n_trades_unfiltered": base["n_trades"], "pf_unfiltered": base["profit_factor"],
            "n_trades_walkforward": filtered["n_trades"], "pf_walkforward": filtered["profit_factor"],
            "win_rate_walkforward": filtered["win_rate"],
        })
    return pd.DataFrame(rows)


def run_asset(name: str, base: pd.DataFrame, daily: dict, vix_daily: pd.Series):
    print(f"\n{'=' * 20} {name} {'=' * 20}")
    cfg = BacktestConfig(spread_bps=0.3, stop_atr_mult=2.0, use_vwap_target=False)

    signaled = base.copy()
    signaled.loc[signaled["signal"] == -1, "signal"] = 0
    signaled.loc[signaled["adx"] < 25.0, "signal"] = 0
    signaled.loc[signaled.index.day_name() == WEEKDAY_FILTER[name], "signal"] = 0

    trades = simulate_trades(signaled, cfg).sort_values("entry_time").reset_index(drop=True)
    if trades.empty:
        print("Keine Trades.")
        return

    pos = base.index.get_indexer(trades["entry_time"]) - 1
    sig_time = base.index[pos]
    entry_dates = sig_time.tz_localize(None).normalize().to_numpy() if sig_time.tz else sig_time.normalize().to_numpy()

    trades["jump_ratio_prior"] = _prior_value(entry_dates, daily["jump_ratio"])
    trades["vix_prior"] = _prior_value(entry_dates, vix_daily) if vix_daily is not None else np.nan

    # ------------------------------------------------------------------
    # 1. Randomization inference (full sample, full-sample-quantile threshold
    #    - matches the Gold-ASB script's own convention for this specific test)
    # ------------------------------------------------------------------
    valid_jump = trades.dropna(subset=["jump_ratio_prior"]).reset_index(drop=True)
    jump_thresh = valid_jump["jump_ratio_prior"].quantile(2 / 3)
    mask_jump = (valid_jump["jump_ratio_prior"] <= jump_thresh).reset_index(drop=True)
    result_jump = dwell_preserving_test(valid_jump, mask_jump, profit_factor, n_shuffles=N_SHUFFLES, seed=11)
    report_randomization(f"{name} Jump-Activity (unterste 2 Tercile behalten)", result_jump)

    if trades["vix_prior"].notna().any():
        valid_vix = trades.dropna(subset=["vix_prior"]).reset_index(drop=True)
        vix_thresh = valid_vix["vix_prior"].quantile(1 / 3)
        mask_vix = (valid_vix["vix_prior"] > vix_thresh).reset_index(drop=True)
        result_vix = dwell_preserving_test(valid_vix, mask_vix, profit_factor, n_shuffles=N_SHUFFLES, seed=12)
        report_randomization(f"{name} VIX-Level (unterstes Tercile ausgeschlossen)", result_vix)

    # ------------------------------------------------------------------
    # 2. Expanding-window walk-forward, 2019-2026
    # ------------------------------------------------------------------
    print(f"\n--- Walk-Forward: {name} Jump-Activity (train-only Bestaetigung je Testjahr) ---")
    wf_jump = run_jump_activity_walk_forward(trades, start_test_year=2019, end_test_year=2026, min_train_trades=30)
    if wf_jump.empty:
        print("  Nicht genug Trades fuer irgendein Testjahr.")
    else:
        print(wf_jump.to_string(index=False))
        confirmed_years = wf_jump[wf_jump["filter_confirmed_on_train"]]
        print(f"  -> in {len(confirmed_years)}/{len(wf_jump)} Testjahren train-only bestaetigt.")

    if trades["vix_prior"].notna().any():
        print(f"\n--- Walk-Forward: {name} VIX-Level (train-only Bestaetigung je Testjahr) ---")
        wf_vix = run_vix_walk_forward(trades, start_test_year=2019, end_test_year=2026, min_train_trades=30)
        if wf_vix.empty:
            print("  Nicht genug Trades fuer irgendein Testjahr.")
        else:
            print(wf_vix.to_string(index=False))
            confirmed_years = wf_vix[wf_vix["filter_confirmed_on_train"]]
            print(f"  -> in {len(confirmed_years)}/{len(wf_vix)} Testjahren train-only bestaetigt.")


def main():
    print("Loading NASDAQ + SP500 M15 ...")
    nasdaq_base = build_frame(_lower_ohlcv(fetch_timeframe("NASDAQ", "M15", START, END)))
    sp500_base = build_frame(_lower_ohlcv(fetch_timeframe("SP500", "M15", START, END)))
    nasdaq_daily = daily_series(nasdaq_base)
    sp500_daily = daily_series(sp500_base)

    print("Fetching VIX ...")
    try:
        vix_daily = fetch_vix_daily(START, END)
    except Exception as e:
        print(f"  VIX-Abruf fehlgeschlagen ({e}).")
        vix_daily = None

    run_asset("NASDAQ", nasdaq_base, nasdaq_daily, vix_daily)
    run_asset("SP500", sp500_base, sp500_daily, vix_daily)


if __name__ == "__main__":
    main()
