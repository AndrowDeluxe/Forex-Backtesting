"""Monte Carlo trade-sequence bootstrap: resamples the historical trades'
R-multiples WITH replacement (same outcome distribution, randomized order)
to get a distribution of possible equity paths instead of just the one
historical sequence. Answers "how much does the exact order of wins/losses
matter for drawdown/ruin risk" - complementary to, not a replacement for,
the walk-forward test (walkforward.py), which checks whether the EDGE
ITSELF held up over the REAL chronological order, not a shuffled one.

IID resampling (not a block bootstrap): each Asian-range window is a
distinct, largely independent event (a new session, a new range) rather
than a return series with strong autocorrelation, so treating trades as
exchangeable draws is a reasonable, standard approach here - same
philosophy as the risk-of-ruin/Monte-Carlo tools commonly used across
retail and prop trading, not something novel to this repo."""

import numpy as np
import pandas as pd


def _r_multiples(trades: pd.DataFrame) -> np.ndarray:
    if "r_multiple" in trades.columns:
        return trades["r_multiple"].to_numpy()
    sign = trades["direction"].map({"long": 1, "short": -1})
    price_move = sign * (trades["exit_price"] - trades["entry_price"])
    return (price_move / trades["stop_distance"]).to_numpy()


def run_monte_carlo(
    trades: pd.DataFrame,
    n_simulations: int = 3000,
    starting_equity: float = 100_000.0,
    risk_pct: float = 0.005,
    seed: int = 42,
) -> pd.DataFrame:
    """Returns one row per simulation: final_equity, total_return_pct,
    max_drawdown, longest_losing_streak. Vectorised over simulations (the
    losing-streak "reset on win" recurrence still loops over trades, but
    that loop is cheap - n_trades iterations, not n_simulations x n_trades)."""

    r = _r_multiples(trades)
    n_trades = len(r)
    if n_trades == 0:
        return pd.DataFrame(
            columns=["final_equity", "total_return_pct", "max_drawdown", "longest_losing_streak"]
        )

    rng = np.random.default_rng(seed)
    sample = rng.choice(r, size=(n_simulations, n_trades), replace=True)

    equity_rel = np.cumprod(1 + sample * risk_pct, axis=1)
    equity_path = starting_equity * equity_rel

    running_max = np.maximum.accumulate(equity_path, axis=1)
    drawdowns = (equity_path - running_max) / running_max
    max_dd = drawdowns.min(axis=1)

    losing = sample < 0
    streak = np.zeros_like(losing, dtype=np.int32)
    streak[:, 0] = losing[:, 0]
    for j in range(1, n_trades):
        streak[:, j] = (streak[:, j - 1] + 1) * losing[:, j]
    longest_streak = streak.max(axis=1)

    return pd.DataFrame(
        {
            "final_equity": equity_path[:, -1],
            "total_return_pct": equity_rel[:, -1] - 1,
            "max_drawdown": max_dd,
            "longest_losing_streak": longest_streak,
        }
    )


def simulate_time_to_target(
    trades: pd.DataFrame,
    target_return: float = 0.10,
    n_simulations: int = 3000,
    risk_pct: float = 0.01,
    max_trades: int = 400,
    seed: int = 42,
) -> pd.DataFrame:
    """Same IID trade-resampling philosophy as run_monte_carlo, but answers a
    different question: not "what's the return after a FIXED number of
    trades", but "how many trades does it statistically take to FIRST reach
    target_return" (first-passage time, not fixed-horizon). One row per
    simulation: trades_to_target (NaN if not reached within max_trades - a
    right-censored simulation, excluded from percentile stats downstream,
    not treated as zero)."""
    r = _r_multiples(trades)
    if len(r) == 0:
        return pd.DataFrame(columns=["trades_to_target"])

    rng = np.random.default_rng(seed)
    trades_to_target = np.full(n_simulations, np.nan)
    for s in range(n_simulations):
        sample = rng.choice(r, size=max_trades, replace=True)
        equity_rel = np.cumprod(1 + sample * risk_pct)
        hits = np.flatnonzero(equity_rel >= 1 + target_return)
        if hits.size:
            trades_to_target[s] = hits[0] + 1
    return pd.DataFrame({"trades_to_target": trades_to_target})


def summarize_monte_carlo(mc: pd.DataFrame, starting_equity: float) -> dict:
    if mc.empty:
        return {}
    return {
        "n_simulations": len(mc),
        "return_p5": mc["total_return_pct"].quantile(0.05),
        "return_p25": mc["total_return_pct"].quantile(0.25),
        "return_p50": mc["total_return_pct"].quantile(0.50),
        "return_p75": mc["total_return_pct"].quantile(0.75),
        "return_p95": mc["total_return_pct"].quantile(0.95),
        "dd_p50": mc["max_drawdown"].quantile(0.50),
        "dd_p95": mc["max_drawdown"].quantile(0.05),  # 5th percentile of DD = the WORSE 95% tail
        "dd_worst": mc["max_drawdown"].min(),
        "prob_net_loss": (mc["total_return_pct"] < 0).mean(),
        "prob_dd_worse_30": (mc["max_drawdown"] < -0.30).mean(),
        "prob_dd_worse_40": (mc["max_drawdown"] < -0.40).mean(),
        "prob_dd_worse_50": (mc["max_drawdown"] < -0.50).mean(),
        "streak_p95": mc["longest_losing_streak"].quantile(0.95),
    }
