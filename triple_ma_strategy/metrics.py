"""Performance metrics for the Triple Moving Average strategy's simulated
trades. Same Buy & Hold / Alpha convention as ema_strategy/metrics.py -
important here since this is a trend-follower on trending assets, where raw
return alone conflates strategy skill with just holding the asset."""

import numpy as np
import pandas as pd


def _buy_and_hold_pct(price_series: pd.Series | None, index: pd.Index) -> float:
    if price_series is None or index.empty:
        return np.nan
    window = price_series.loc[(price_series.index >= index[0]) & (price_series.index <= index[-1])]
    if len(window) < 2:
        return np.nan
    return (window.iloc[-1] / window.iloc[0] - 1) * 100


def compute_metrics(
    trades: pd.DataFrame, equity: pd.Series, initial_equity: float = 10_000.0,
    price_series: pd.Series | None = None,
) -> dict:
    bh_pct = _buy_and_hold_pct(price_series, equity.index)

    if trades.empty:
        out = {"Anzahl Trades": 0}
        if price_series is not None:
            out["Buy & Hold %"] = round(bh_pct, 1)
            out["Alpha vs. Buy & Hold %"] = round(0.0 - bh_pct, 1) if not np.isnan(bh_pct) else np.nan
        return out

    wins = trades[trades["pnl_pct"] > 0]
    losses = trades[trades["pnl_pct"] <= 0]
    total_return = (equity.iloc[-1] / initial_equity - 1) * 100
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = ((equity.iloc[-1] / initial_equity) ** (1 / years) - 1) * 100 if years > 0 else np.nan

    running_max = equity.cummax()
    drawdown = (equity - running_max) / running_max
    max_dd = drawdown.min() * 100

    gross_profit = wins["pnl_pct"].sum()
    gross_loss = -losses["pnl_pct"].sum()
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.nan

    daily_ret = equity.pct_change().dropna()
    sharpe = (daily_ret.mean() / daily_ret.std() * np.sqrt(252)) if daily_ret.std() > 0 else np.nan

    out = {
        "Anzahl Trades": len(trades),
        "Trefferquote %": round(len(wins) / len(trades) * 100, 1),
        "Profit Factor": round(profit_factor, 2),
        "Gesamtrendite %": round(total_return, 1),
        "CAGR %": round(cagr, 1),
        "Max Drawdown %": round(max_dd, 1),
        "Sharpe (approx.)": round(sharpe, 2),
        "Bester Trade %": round(trades["pnl_pct"].max() * 100, 1),
        "Schlechtester Trade %": round(trades["pnl_pct"].min() * 100, 1),
        "Ø Haltedauer (Tage)": round(trades["hold_days"].mean(), 1),
    }
    if price_series is not None:
        out["Buy & Hold %"] = round(bh_pct, 1)
        out["Alpha vs. Buy & Hold %"] = round(total_return - bh_pct, 1) if not np.isnan(bh_pct) else np.nan
    return out
