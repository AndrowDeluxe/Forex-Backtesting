"""Research script: FX-only rebuild of the JPM "Cross Asset Momentum
Spillover" paper (Salopek/Tzotchev, 28.05.2025) - Workstream A of the
2026-09-09 plan, see knowledge/resources/cross-asset-momentum-spillover.md
and knowledge/projects/fx-momentum-spillover.md.

Own SIMPLIFIED rebuild, disclosed deviations from the paper:
1. Momentum signal is a substitute (t-test on mean daily log return,
   mapped to [-1,1] via the normal CDF - see fx_momentum_spillover/
   signals.py docstring) since the paper's own formula lives in a
   different, unavailable paper.
2. Universe is the 7 FX majors only (EURUSD, GBPUSD, AUDUSD, NZDUSD,
   USDCAD, USDCHF, USDJPY), not the paper's full 42-asset cross-asset
   universe (Commodities/Equities/Bonds/FX) - deferred, see DASHBOARD.md
   Ideen-Inbox.
3. Everything else follows the paper's own stated construction as closely
   as possible: 5 lookbacks (32/64/126/252/504 trading days), rolling
   L1-logistic spillover regression per rebalancing month (fx_momentum_
   spillover/spillover.py), monthly rebalance, inverse-realized-vol
   position sizing, 10% target annualized portfolio vol (rolling 1y),
   1-day execution lag, transaction costs (fx_momentum_spillover/
   portfolio.py).

Produces the same three tables the paper does (Individual-only,
Spillover-only, Combination, per lookback + aggregated) so the JPM-claimed
Sharpe uplift (0.66 -> 0.75 individual -> spillover, full 42-asset
universe) is directly comparable against this FX-only rebuild's own
numbers - NOT expected to replicate at the same magnitude, see the
sample-size caveat in the plan (7 assets instead of 42, same ~23y history
-> a much thinner, noisier cross-section)."""

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fx_momentum_spillover.data import fetch_fx_universe_closes
from fx_momentum_spillover.portfolio import backtest_portfolio, daily_weights_from_signal
from fx_momentum_spillover.signals import LOOKBACKS, all_momentum_signals
from fx_momentum_spillover.spillover import (
    forward_returns,
    monthly_rebalance_dates,
    rolling_spillover_predictions,
)
from strategy.metrics import annualized_sharpe, cagr, calmar_ratio, max_drawdown

# START = 2010-11-01, not 2003 (Dukascopy's own data range): NZDUSD is
# sparse/gappy through 2003-2009 and USDJPY separately has a gap through
# 2010-02..2010-09 (see fx_momentum_spillover/data.py module docstring,
# check_no_gaps()) - starting after both keeps the joined 7-pair index
# fully continuous, which a rolling-window momentum signal requires. Costs
# ~7.5 years of history vs. the paper's own ~30y window - on top of the
# 7-vs-42 asset sample-size caveat already flagged in the plan.
START, END = "2010-11-01", "2026-08-31"
IS_OOS_SPLIT = "2019-01-01"
HORIZON = 21  # trading days ~ 1 month, matches the monthly rebalance/forward-return target
MIN_TRAIN_SAMPLES = 60


def perf_row(returns: pd.Series) -> dict:
    if returns.empty or returns.std(ddof=1) == 0:
        return {"AnnReturn": float("nan"), "AnnVol": float("nan"), "Sharpe": float("nan"), "MaxDD": float("nan")}
    return {
        "AnnReturn": cagr(returns),
        "AnnVol": returns.std(ddof=1) * np.sqrt(252),
        "Sharpe": annualized_sharpe(returns),
        "MaxDD": max_drawdown(returns),
    }


def fmt_row(label: str, row: dict) -> str:
    return (
        f"{label:<12} Return={row['AnnReturn']:>8.2%}  Vol={row['AnnVol']:>7.2%}  "
        f"Sharpe={row['Sharpe']:>6.2f}  MaxDD={row['MaxDD']:>8.2%}"
    )


def main():
    t0 = time.time()
    print(f"Fetching FX universe D1 closes {START} -> {END} ...")
    closes = fetch_fx_universe_closes(START, END)
    print(f"{len(closes)} common trading days, {list(closes.columns)}")

    momentum = all_momentum_signals(closes)
    fwd = forward_returns(closes, horizon=HORIZON)
    reb_dates = monthly_rebalance_dates(closes.index)
    print(f"{len(reb_dates)} monthly rebalance dates, {reb_dates[0].date()} .. {reb_dates[-1].date()}")

    individual_returns: dict[int, pd.Series] = {}
    spillover_returns: dict[int, pd.Series] = {}
    combo_returns: dict[int, pd.Series] = {}
    combo_weights_by_lb: dict[int, pd.DataFrame] = {}

    for lb in LOOKBACKS:
        min_train_window = max(2 * lb, 252)
        print(f"\n--- lookback={lb} (min_train_window={min_train_window}) ---")

        mom_lb = momentum[lb]
        ind_signal = mom_lb.reindex(reb_dates)
        ind_weights = daily_weights_from_signal(ind_signal, closes)
        individual_returns[lb] = backtest_portfolio(ind_weights, closes)

        t1 = time.time()
        spill_prob = rolling_spillover_predictions(
            mom_lb, fwd, reb_dates, horizon=HORIZON, min_train_window=min_train_window,
            min_train_samples=MIN_TRAIN_SAMPLES,
        )
        print(f"    spillover regressions: {time.time() - t1:.1f}s, "
              f"{spill_prob.notna().sum().sum()}/{spill_prob.size} non-NaN predictions")
        spill_signal = spill_prob - 0.5
        spill_weights = daily_weights_from_signal(spill_signal, closes)
        spillover_returns[lb] = backtest_portfolio(spill_weights, closes)

        # average, rescaled to a comparable range first (ind_signal in
        # [-1,1], spill_signal in [-0.5,0.5]) - only the SIGN of the sum
        # drives daily_weights_from_signal, so this lets a strong individual
        # reading outvote a weak/disagreeing spillover reading and vice versa
        combo_signal = (ind_signal + spill_signal.reindex(ind_signal.index) * 2) / 2
        combo_weights_by_lb[lb] = daily_weights_from_signal(combo_signal, closes)
        combo_returns[lb] = backtest_portfolio(combo_weights_by_lb[lb], closes)

    def aggregate(returns_by_lb: dict[int, pd.Series]) -> pd.Series:
        df = pd.concat(returns_by_lb, axis=1)
        return df.mean(axis=1).dropna()

    individual_returns["agg"] = aggregate(individual_returns)
    spillover_returns["agg"] = aggregate(spillover_returns)
    combo_returns["agg"] = aggregate(combo_returns)

    def print_table(title: str, returns_by_lb: dict) -> None:
        print("\n" + "=" * 78)
        print(title)
        print("=" * 78)
        for lb in [*LOOKBACKS, "agg"]:
            label = f"{lb}d" if lb != "agg" else "Aggregated"
            print(fmt_row(label, perf_row(returns_by_lb[lb])))

    print_table("TABLE 1: INDIVIDUAL-MOMENTUM-ONLY (own substitute signal)", individual_returns)
    print_table("TABLE 2: SPILLOVER-ONLY (L1-logistic, FX-only 7-asset universe)", spillover_returns)
    print_table("TABLE 3: COMBINATION (average of individual + spillover)", combo_returns)

    print("\n" + "=" * 78)
    print("PAPER'S OWN CLAIM (42-asset universe, full period from late 1996):")
    print("  Individual aggregated Sharpe 0.66 -> Spillover aggregated Sharpe 0.75 -> Combination 0.74")
    print("=" * 78)

    # =========================================================================
    # IS/OOS split (aggregated strategy only)
    # =========================================================================
    print("\n" + "=" * 78)
    print(f"IS/OOS SPLIT at {IS_OOS_SPLIT} (Aggregated strategy)")
    print("=" * 78)
    for label, returns in [
        ("Individual", individual_returns["agg"]),
        ("Spillover", spillover_returns["agg"]),
        ("Combination", combo_returns["agg"]),
    ]:
        is_ret = returns[returns.index < IS_OOS_SPLIT]
        oos_ret = returns[returns.index >= IS_OOS_SPLIT]
        print(fmt_row(f"{label} IS", perf_row(is_ret)))
        print(fmt_row(f"{label} OOS", perf_row(oos_ret)))

    # =========================================================================
    # Monte-Carlo bootstrap of the monthly return sequence (Aggregated Combination)
    # =========================================================================
    print("\n" + "=" * 78)
    print("MONTE-CARLO BOOTSTRAP (Aggregated Combination, resample monthly blocks, n=2000)")
    print("=" * 78)
    daily_ret = combo_returns["agg"]
    monthly_ret = (1 + daily_ret).resample("ME").prod() - 1
    n_months = len(monthly_ret)
    rng = np.random.default_rng(42)
    n_boot = 2000
    boot_sharpes = np.empty(n_boot)
    boot_finalrets = np.empty(n_boot)
    for i in range(n_boot):
        sample = monthly_ret.to_numpy()[rng.integers(0, n_months, n_months)]
        boot_sharpes[i] = (sample.mean() / sample.std(ddof=1) * np.sqrt(12)) if sample.std(ddof=1) > 0 else 0.0
        boot_finalrets[i] = np.prod(1 + sample) - 1
    actual_sharpe = (monthly_ret.mean() / monthly_ret.std(ddof=1) * np.sqrt(12)) if monthly_ret.std(ddof=1) > 0 else 0.0
    print(f"n_months={n_months}  actual monthly Sharpe={actual_sharpe:.2f}")
    print(f"Bootstrap Sharpe: mean={boot_sharpes.mean():.2f}  p05={np.percentile(boot_sharpes, 5):.2f}  "
          f"p50={np.percentile(boot_sharpes, 50):.2f}  p95={np.percentile(boot_sharpes, 95):.2f}")
    print(f"Bootstrap total return: p05={np.percentile(boot_finalrets, 5):.1%}  "
          f"p50={np.percentile(boot_finalrets, 50):.1%}  p95={np.percentile(boot_finalrets, 95):.1%}  "
          f"P(total return < 0)={float((boot_finalrets < 0).mean()):.1%}")

    # =========================================================================
    # Cost sensitivity (Aggregated Combination) - custom sweep, not
    # strategy.metrics.breakeven_spread_bps (that helper is coupled to
    # strategy.backtest.simulate_trades' trade-level DataFrame + config
    # dataclass, doesn't fit this portfolio-return engine's shape)
    # =========================================================================
    print("\n" + "=" * 78)
    print("COST SENSITIVITY (Aggregated Combination) - perf at various per-rebalance cost levels")
    print("=" * 78)
    for cost_bps in [0.0, 2.5, 5.0, 10.0, 20.0, 40.0, 80.0]:
        combo_ret_at_cost = aggregate(
            {lb: backtest_portfolio(combo_weights_by_lb[lb], closes, cost_bps=cost_bps) for lb in LOOKBACKS}
        )
        print(fmt_row(f"{cost_bps:.1f}bps", perf_row(combo_ret_at_cost)))

    print(f"\nTotal runtime: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
