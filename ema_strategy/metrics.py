"""Performance metrics for the EMA S/R strategy's simulated trades."""

import numpy as np
import pandas as pd


def _buy_and_hold_pct(price_series: pd.Series | None, index: pd.Index) -> float:
    """Buy-and-hold return (%) of `price_series` over the same span as
    `index` (the equity curve's date range) - so a trend-following
    strategy's apparent edge on a strongly-drifting asset (e.g. Nasdaq/Gold
    over 2016-2026) can be told apart from just holding that asset. None if
    no price series was supplied (backward compatible)."""
    if price_series is None or index.empty:
        return np.nan
    window = price_series.loc[(price_series.index >= index[0]) & (price_series.index <= index[-1])]
    if len(window) < 2:
        return np.nan
    return (window.iloc[-1] / window.iloc[0] - 1) * 100


def compute_metrics(
    trades: pd.DataFrame, equity: pd.Series, initial_equity=10_000.0,
    price_series: pd.Series | None = None,
) -> dict:
    """`price_series`: optional Close prices (any timeframe) spanning at
    least `equity`'s date range, used only to compute the buy-and-hold
    benchmark and the strategy's alpha over it - the strategy's own P&L
    calculation never uses it.
    """
    bh_pct = _buy_and_hold_pct(price_series, equity.index)

    if trades.empty:
        out = {"Anzahl Trades": 0}
        if price_series is not None:
            out["Buy & Hold %"] = round(bh_pct, 1)
            out["Alpha vs. Buy & Hold %"] = round(0.0 - bh_pct, 1) if not np.isnan(bh_pct) else np.nan
        return out

    wins = trades[trades["pnl"] > 0]
    losses = trades[trades["pnl"] <= 0]
    total_return = (equity.iloc[-1] / initial_equity - 1) * 100
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = ((equity.iloc[-1] / initial_equity) ** (1 / years) - 1) * 100 if years > 0 else np.nan

    running_max = equity.cummax()
    drawdown = (equity - running_max) / running_max
    max_dd = drawdown.min() * 100

    gross_profit = wins["pnl"].sum()
    gross_loss = -losses["pnl"].sum()
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.nan

    daily_eq = equity.resample("D").last().ffill()
    daily_ret = daily_eq.pct_change().dropna()
    sharpe = (daily_ret.mean() / daily_ret.std() * np.sqrt(252)) if daily_ret.std() > 0 else np.nan

    out = {
        "Anzahl Trades": len(trades),
        "Trefferquote %": round(len(wins) / len(trades) * 100, 1),
        "Profit Factor": round(profit_factor, 2),
        "Ø R-Multiple": round(trades["r_multiple"].mean(), 2),
        "Gesamtrendite %": round(total_return, 1),
        "CAGR %": round(cagr, 1),
        "Max Drawdown %": round(max_dd, 1),
        "Sharpe (approx.)": round(sharpe, 2),
        "Bester Trade %R": round(trades["r_multiple"].max(), 2),
        "Schlechtester Trade %R": round(trades["r_multiple"].min(), 2),
    }
    if price_series is not None:
        out["Buy & Hold %"] = round(bh_pct, 1)
        out["Alpha vs. Buy & Hold %"] = round(total_return - bh_pct, 1) if not np.isnan(bh_pct) else np.nan
    return out
