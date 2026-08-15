"""Daily mark-to-market risk engine for prop-firm ("Fremdkapital"/FK) and
personal-capital ("Eigenkapital"/EK) risk-parameter calibration. Same core
idea as gold_bitcoin_dual_momentum/risk_engine.py::simulate_risk_based
("die bisherige Logik" - fixed-fractional risk to an ATR-based stop, marked
to market daily so intra-trade drawdowns are actually caught, not just
close-to-close jumps at trade exit), reusing this package's own
account_simulation.simulate_account for trade acceptance (max-concurrent /
one-per-market) and dollar risk sizing (already correctly compounding), and
adding only the daily mark-to-market layer on top.

Conservative-by-design choices (this feeds real prop-firm and personal risk
limits, where understating risk is the dangerous failure mode, not
overstating it):
  - Each open position is marked, on every day it's held, at that day's
    intraday LOW (not close) - the worst point a real broker's daily-DD
    monitor could have caught, for a long-only strategy. The exit day itself
    still uses the trade's own exact realized r_multiple (the true fill).
  - "Daily drawdown" = the drop from the PRIOR day's end-of-day equity to
    TODAY's worst (low-marked) equity - a trailing daily-loss convention
    (matches how most funded-account rules work), not a fixed % of initial
    balance.
  - Calibration should be run against the FULL available history (2016-2026,
    not just the recent favourable 2023-2026 regime) - the strategy was
    flat-to-losing 2016-2022 in every market (scripts/research_mt5_trend_
    pullback.py), and a real funded account has to survive whatever regime
    actually happens next, not assume the favourable recent one continues.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from mt5_trend_pullback.account_simulation import simulate_account


@dataclass
class DailyRiskResult:
    equity_curve: pd.DataFrame
    max_daily_dd_pct: float
    max_total_dd_pct: float
    final_equity: float
    total_return: float
    n_trades_taken: int
    n_trades_skipped: int


def mark_daily(sim: dict, daily_low_by_market: dict[str, pd.Series], starting_equity: float = 100_000.0) -> DailyRiskResult:
    """Daily mark-to-market pass on top of an ALREADY-BUILT acceptance sim
    (anything with the account_simulation.simulate_account output shape:
    `sim["trades"]` carrying entry_time/exit_time/market/entry_price/
    initial_risk/risk_dollars/r_multiple/pnl, plus n_taken/n_skipped) -
    decoupled from account_simulation specifically so callers can also use
    mt5_trend_pullback.open_risk_engine's aggregate-open-risk acceptance
    engine here instead, without duplicating this marking logic."""
    accepted = sim["trades"]
    if accepted.empty or "initial_risk" not in accepted.columns:
        empty = pd.DataFrame({"equity": [starting_equity]}, index=[pd.Timestamp.now()])
        return DailyRiskResult(empty, 0.0, 0.0, starting_equity, 0.0, sim["n_taken"], sim["n_skipped"])

    accepted = accepted.copy()
    accepted["entry_time_naive"] = accepted["entry_time"].dt.tz_localize(None)
    accepted["exit_time_naive"] = accepted["exit_time"].dt.tz_localize(None)

    daily_low_naive = {}
    for m, s in daily_low_by_market.items():
        idx = s.index.tz_localize(None) if s.index.tz is not None else s.index
        daily_low_naive[m] = pd.Series(s.to_numpy(), index=idx).sort_index()

    start = accepted["entry_time_naive"].min().normalize()
    end = accepted["exit_time_naive"].max().normalize()
    calendar = pd.date_range(start, end, freq="D")

    # Vectorized per-TRADE pass (not per-day): for each accepted trade, mark
    # its own open days (entry day through the day before exit) against that
    # market's daily low in one vectorised reindex/ffill, instead of
    # re-filtering the whole trade list on every one of ~3500 calendar days
    # (the previous per-day/iterrows version) - same numbers, much faster.
    floating_by_day = pd.Series(0.0, index=calendar)
    realized_by_day = pd.Series(0.0, index=calendar)
    for pos in accepted.itertuples(index=False):
        entry_day = pos.entry_time_naive.normalize()
        exit_day = pos.exit_time_naive.normalize()
        realized_by_day.loc[exit_day] += pos.pnl

        low_series = daily_low_naive.get(pos.market)
        initial_risk = getattr(pos, "initial_risk", np.nan)
        if low_series is None or low_series.empty or pd.isna(initial_risk) or exit_day <= entry_day:
            continue
        open_days = pd.date_range(entry_day, exit_day, freq="D")[:-1]  # exit day itself is realized, not marked
        if len(open_days) == 0:
            continue
        lows = low_series.reindex(open_days, method="ffill")
        r_at_low = (lows - pos.entry_price) / initial_risk
        floating_by_day.loc[open_days] += pos.risk_dollars * r_at_low.fillna(0.0).to_numpy()

    equity_series = starting_equity + realized_by_day.cumsum() + floating_by_day
    curve = pd.DataFrame({"equity": equity_series})
    curve["running_peak"] = curve["equity"].cummax()
    curve["total_dd_pct"] = curve["equity"] / curve["running_peak"] - 1.0
    curve["prev_equity"] = curve["equity"].shift(1).fillna(starting_equity)
    curve["daily_dd_pct"] = np.minimum(0.0, curve["equity"] / curve["prev_equity"] - 1.0)

    final_equity = curve["equity"].iloc[-1]
    return DailyRiskResult(
        equity_curve=curve,
        max_daily_dd_pct=curve["daily_dd_pct"].min(),
        max_total_dd_pct=curve["total_dd_pct"].min(),
        final_equity=final_equity,
        total_return=final_equity / starting_equity - 1.0,
        n_trades_taken=sim["n_taken"],
        n_trades_skipped=sim["n_skipped"],
    )


def simulate_daily_marked(
    trades_by_market: dict[str, pd.DataFrame],
    daily_low_by_market: dict[str, pd.Series],
    risk_pct: float,
    starting_equity: float = 100_000.0,
    max_concurrent: int = 3,
    risk_weight_by_market: dict[str, float] | None = None,
) -> DailyRiskResult:
    """Position-count-cap variant (max `max_concurrent` positions across all
    markets) - see mt5_trend_pullback.open_risk_engine.simulate_open_risk_daily
    for the OU-Modell-style aggregate-dollar-open-risk-cap-with-breakeven-
    exclusion variant instead."""
    sim = simulate_account(
        trades_by_market, starting_equity=starting_equity, risk_pct=risk_pct,
        max_concurrent=max_concurrent, risk_weight_by_market=risk_weight_by_market,
    )
    return mark_daily(sim, daily_low_by_market, starting_equity)


def simulate_open_risk_daily(
    trades_by_market: dict[str, pd.DataFrame],
    daily_low_by_market: dict[str, pd.Series],
    risk_pct: float,
    max_total_risk_pct: float,
    starting_equity: float = 100_000.0,
    risk_weight_by_market: dict[str, float] | None = None,
) -> DailyRiskResult:
    """OU-Modell-style aggregate-open-risk-cap-with-breakeven-exclusion
    variant - see mt5_trend_pullback.open_risk_engine.simulate_open_risk_account."""
    from mt5_trend_pullback.open_risk_engine import simulate_open_risk_account

    sim = simulate_open_risk_account(
        trades_by_market, starting_equity=starting_equity, risk_pct=risk_pct,
        max_total_risk_pct=max_total_risk_pct, risk_weight_by_market=risk_weight_by_market,
    )
    return mark_daily(sim, daily_low_by_market, starting_equity)


def sweep_risk_pct(
    trades_by_market: dict[str, pd.DataFrame],
    daily_low_by_market: dict[str, pd.Series],
    risk_pct_candidates: list[float],
    max_daily_dd_limit: float | None,
    max_total_dd_limit: float,
    starting_equity: float = 100_000.0,
    max_concurrent: int = 3,
    risk_weight_by_market: dict[str, float] | None = None,
) -> pd.DataFrame:
    """One row per candidate risk_pct with compliance flags against
    `max_daily_dd_limit` (None = unconstrained, for EK) and `max_total_dd_limit`
    (both positive fractions, e.g. 0.03 for 3%)."""
    rows = []
    for rp in risk_pct_candidates:
        res = simulate_daily_marked(
            trades_by_market, daily_low_by_market, risk_pct=rp,
            starting_equity=starting_equity, max_concurrent=max_concurrent,
            risk_weight_by_market=risk_weight_by_market,
        )
        daily_ok = (max_daily_dd_limit is None) or (abs(res.max_daily_dd_pct) <= max_daily_dd_limit)
        total_ok = abs(res.max_total_dd_pct) <= max_total_dd_limit
        rows.append({
            "risk_pct": rp, "max_daily_dd": res.max_daily_dd_pct, "max_total_dd": res.max_total_dd_pct,
            "final_equity": res.final_equity, "total_return": res.total_return,
            "n_trades": res.n_trades_taken, "n_skipped": res.n_trades_skipped,
            "daily_ok": daily_ok, "total_ok": total_ok, "compliant": daily_ok and total_ok,
        })
    return pd.DataFrame(rows)
