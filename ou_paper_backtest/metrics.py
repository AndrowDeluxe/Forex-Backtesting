"""Performance metrics matching paper section 5.4 / Fig. 6."""

import numpy as np
import pandas as pd

import config


def cumulative_curve(daily_returns: pd.Series, base: float = 100.0) -> pd.Series:
    return base * (1.0 + daily_returns).cumprod()


def max_drawdown(cum_curve: pd.Series) -> float:
    running_max = cum_curve.cummax()
    dd = cum_curve / running_max - 1.0
    return dd.min()


def annualized_return(daily_returns: pd.Series) -> float:
    total_days = len(daily_returns)
    if total_days == 0:
        return np.nan
    total_return = (1.0 + daily_returns).prod()
    years = total_days / config.TRADING_DAYS_PER_YEAR
    return total_return ** (1.0 / years) - 1.0 if years > 0 else np.nan


def annualized_vol(daily_returns: pd.Series) -> float:
    return daily_returns.std() * np.sqrt(config.TRADING_DAYS_PER_YEAR)


def sharpe_ratio(daily_returns: pd.Series, rf: float = 0.0) -> float:
    vol = annualized_vol(daily_returns)
    if vol == 0 or np.isnan(vol):
        return np.nan
    return (annualized_return(daily_returns) - rf) / vol


def sortino_ratio(daily_returns: pd.Series, rf: float = 0.0) -> float:
    downside = daily_returns[daily_returns < 0]
    dd_vol = downside.std() * np.sqrt(config.TRADING_DAYS_PER_YEAR)
    if dd_vol == 0 or np.isnan(dd_vol):
        return np.nan
    return (annualized_return(daily_returns) - rf) / dd_vol


def calmar_ratio(daily_returns: pd.Series) -> float:
    cum = cumulative_curve(daily_returns)
    mdd = max_drawdown(cum)
    if mdd == 0:
        return np.nan
    return annualized_return(daily_returns) / abs(mdd)


def summarize(daily_returns: pd.Series, trades: list[dict] | None = None) -> dict:
    cum = cumulative_curve(daily_returns)
    total_return = cum.iloc[-1] / cum.iloc[0] - 1.0
    out = {
        "total_return_pct": total_return * 100,
        "annualized_return_pct": annualized_return(daily_returns) * 100,
        "annualized_vol_pct": annualized_vol(daily_returns) * 100,
        "sharpe": sharpe_ratio(daily_returns),
        "sortino": sortino_ratio(daily_returns),
        "calmar": calmar_ratio(daily_returns),
        "max_drawdown_pct": max_drawdown(cum) * 100,
    }
    if trades is not None:
        n = len(trades)
        pnls = [t["pnl"] if "pnl" in t else t["pnl_pct"] for t in trades]
        wins = sum(1 for p in pnls if p > 0)
        out["n_trades"] = n
        out["win_rate_pct"] = (wins / n * 100) if n else np.nan
        out["avg_trade_pnl_pct"] = (np.mean(pnls) * 100) if n else np.nan
        out["avg_days_held"] = np.mean([t["days_held"] for t in trades]) if n else np.nan
    return out
