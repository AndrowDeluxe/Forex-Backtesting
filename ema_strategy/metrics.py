"""Performance metrics for the EMA S/R strategy's simulated trades."""

import numpy as np
import pandas as pd


def compute_metrics(trades: pd.DataFrame, equity: pd.Series, initial_equity=10_000.0) -> dict:
    if trades.empty:
        return {"Anzahl Trades": 0}

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

    return {
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
