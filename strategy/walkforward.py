"""Rolling-origin stability check (Sec. 7: 'walk-forward out-of-sample
evaluation'). Threshold theta is already adaptive/rolling (see
`compute_adaptive_theta`), so there is no train/test hyperparameter split
to perform; what this module checks instead is whether performance is
*stable across time* rather than concentrated in one lucky stretch -
the actual question a walk-forward evaluation is trying to answer.
"""

import numpy as np
import pandas as pd

from strategy.backtest import trades_to_daily_returns
from strategy.metrics import annualized_sharpe, calmar_ratio, max_drawdown, trade_stats


def fold_performance(trades: pd.DataFrame, index: pd.DatetimeIndex, fold: str = "MS") -> pd.DataFrame:
    """Per-fold (default: calendar month) Sharpe/Calmar/win-rate/trade count."""
    daily = trades_to_daily_returns(trades, index)
    rows = []
    for period, ret in daily.groupby(pd.Grouper(freq=fold)):
        if ret.empty:
            continue
        period_trades = trades[
            (trades["exit_time"] >= ret.index[0]) & (trades["exit_time"] <= ret.index[-1])
        ] if not trades.empty else trades
        stats = trade_stats(period_trades)
        rows.append(
            {
                "period": ret.index[0],
                "sharpe": annualized_sharpe(ret, periods_per_year=len(ret) if len(ret) < 252 else 252),
                "calmar": calmar_ratio(ret),
                "max_drawdown": max_drawdown(ret),
                "n_trades": stats["n_trades"],
                "win_rate": stats["win_rate"],
                "avg_return_pct": stats["avg_return_pct"],
            }
        )
    return pd.DataFrame(rows).set_index("period") if rows else pd.DataFrame()


def stability_summary(fold_df: pd.DataFrame) -> dict:
    """Is the edge broad-based across folds, or driven by one outlier period?"""
    if fold_df.empty:
        return {"n_folds": 0}
    active = fold_df[fold_df["n_trades"] > 0]
    return {
        "n_folds": len(fold_df),
        "n_active_folds": len(active),
        "pct_folds_positive": float((active["avg_return_pct"] > 0).mean()) if len(active) else np.nan,
        "sharpe_mean": active["sharpe"].mean() if len(active) else np.nan,
        "sharpe_std": active["sharpe"].std() if len(active) else np.nan,
        "worst_fold_drawdown": fold_df["max_drawdown"].min(),
    }
