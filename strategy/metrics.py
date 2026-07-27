"""Performance metrics, regime decomposition (Sec. 7), and transaction-cost
sensitivity / breakeven-spread analysis (Sec. 6.3, 7)."""

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def equity_curve(daily_returns: pd.Series) -> pd.Series:
    return (1 + daily_returns).cumprod()


def max_drawdown(daily_returns: pd.Series) -> float:
    curve = equity_curve(daily_returns)
    running_max = curve.cummax()
    dd = curve / running_max - 1.0
    return dd.min()


def annualized_sharpe(daily_returns: pd.Series, periods_per_year: int = TRADING_DAYS_PER_YEAR) -> float:
    if daily_returns.std(ddof=1) == 0 or daily_returns.empty:
        return 0.0
    return float(daily_returns.mean() / daily_returns.std(ddof=1) * np.sqrt(periods_per_year))


def cagr(daily_returns: pd.Series, periods_per_year: int = TRADING_DAYS_PER_YEAR) -> float:
    curve = equity_curve(daily_returns)
    if curve.empty or curve.iloc[-1] <= 0:
        return -1.0
    n_years = len(daily_returns) / periods_per_year
    if n_years <= 0:
        return 0.0
    return curve.iloc[-1] ** (1 / n_years) - 1


def calmar_ratio(daily_returns: pd.Series) -> float:
    mdd = max_drawdown(daily_returns)
    if mdd == 0:
        return 0.0
    return cagr(daily_returns) / abs(mdd)


def trade_stats(trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {
            "n_trades": 0, "win_rate": np.nan, "profit_factor": np.nan,
            "avg_return_pct": np.nan, "avg_hold_bars": np.nan,
            "exit_reason_counts": {},
        }
    wins = trades["return_pct"] > 0
    gross_win = trades.loc[wins, "return_pct"].sum()
    gross_loss = -trades.loc[~wins, "return_pct"].sum()
    return {
        "n_trades": len(trades),
        "win_rate": wins.mean(),
        "profit_factor": (gross_win / gross_loss) if gross_loss > 0 else np.inf,
        "avg_return_pct": trades["return_pct"].mean(),
        "avg_hold_bars": trades["hold_bars"].mean(),
        "exit_reason_counts": trades["exit_reason"].value_counts().to_dict(),
    }


def summarize(trades: pd.DataFrame, index: pd.DatetimeIndex) -> dict:
    from strategy.backtest import trades_to_daily_returns

    daily = trades_to_daily_returns(trades, index)
    out = {
        "sharpe": annualized_sharpe(daily),
        "calmar": calmar_ratio(daily),
        "cagr": cagr(daily),
        "max_drawdown": max_drawdown(daily),
    }
    out.update(trade_stats(trades))
    return out


def regime_decomposition(trades: pd.DataFrame, adx_level_threshold: float = 25.0) -> pd.DataFrame:
    """Split trade PnL by trend strength at entry (Sec. 7: 'trending vs.
    mean-reverting') and by an ATR-at-entry volatility tercile (proxy for
    'high vs. low volatility')."""
    if trades.empty:
        return pd.DataFrame()

    t = trades.copy()
    t["adx_bucket"] = np.where(t["adx_at_entry"] >= adx_level_threshold, "high_adx (>=25)", "low_adx (<25)")
    try:
        t["vol_tercile"] = pd.qcut(t["atr_at_entry"], 3, labels=["low_vol", "mid_vol", "high_vol"])
    except ValueError:
        t["vol_tercile"] = "n/a"

    rows = []
    for keys, group in t.groupby(["adx_bucket", "vol_tercile"], observed=True):
        stats = trade_stats(group)
        rows.append({"adx_bucket": keys[0], "vol_tercile": keys[1], **stats})
    return pd.DataFrame(rows).drop(columns=["exit_reason_counts"], errors="ignore")


def breakeven_spread_bps(
    signaled_df: pd.DataFrame,
    base_config,
    lo: float = 0.0,
    hi: float = 20.0,
    tol: float = 1e-6,
    max_iter: int = 30,
) -> float:
    """Bisect on spread_bps for the round-trip cost at which mean trade
    return crosses zero (Sec. 6.3: break-even spread analysis).

    `tol` is in return units (1e-6 = 0.01bps): trade returns here are
    themselves only ~1-2bps, so a loose tolerance would falsely "converge"
    on the first bisection step. Convergence is really driven by the
    `hi - lo < 1e-3` (bps) interval-width check below.
    """
    from dataclasses import replace

    from strategy.backtest import simulate_trades

    def mean_return_at(spread_bps: float) -> float:
        cfg = replace(base_config, spread_bps=spread_bps)
        trades = simulate_trades(signaled_df, cfg)
        return trades["return_pct"].mean() if not trades.empty else -np.inf

    f_lo, f_hi = mean_return_at(lo), mean_return_at(hi)
    if f_lo < 0:
        return lo  # unprofitable even cost-free
    if f_hi > 0:
        return hi  # still profitable at the widest spread tested

    for _ in range(max_iter):
        mid = (lo + hi) / 2
        f_mid = mean_return_at(mid)
        if abs(f_mid) < tol or (hi - lo) < 1e-3:
            return mid
        if f_mid > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2
