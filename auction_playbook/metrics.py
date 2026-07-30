"""Trade-level stats for the Auction Market Playbook reconstruction.
Deliberately simple (no Sharpe/equity-curve machinery) - with likely a
handful to a few dozen trades per variant, R-multiple and win rate are the
honest, readable numbers; anything fancier would overstate precision on
this sample size.
"""

import numpy as np
import pandas as pd


def _profit_factor(returns: pd.Series) -> float:
    wins = returns > 0
    gross_win = returns.loc[wins].sum()
    gross_loss = -returns.loc[~wins].sum()
    return (gross_win / gross_loss) if gross_loss > 0 else np.inf


def trade_stats(trades: pd.DataFrame) -> dict:
    """Includes `median_r_multiple` and `profit_factor_excl_best_trade`
    alongside the usual mean-based stats - profit factor alone reads much
    more favourably than the fuller picture on this strategy's samples
    (median R-multiple is exactly -1.00 in almost every variant tested so
    far; a couple of large winners carry the mean), so both numbers are
    surfaced together everywhere this is displayed, not just in one-off
    research-script checks.
    """
    if trades.empty:
        return {
            "n_trades": 0, "win_rate": np.nan, "profit_factor": np.nan,
            "avg_r_multiple": np.nan, "median_r_multiple": np.nan,
            "profit_factor_excl_best_trade": np.nan, "avg_hold_bars": np.nan, "exit_reason_counts": {},
        }
    wins = trades["return_pct"] > 0
    if len(trades) > 1:
        without_best = trades.sort_values("return_pct", ascending=False).iloc[1:]
        pf_excl_best = _profit_factor(without_best["return_pct"])
    else:
        pf_excl_best = np.nan
    return {
        "n_trades": len(trades),
        "win_rate": wins.mean(),
        "profit_factor": _profit_factor(trades["return_pct"]),
        "avg_r_multiple": trades["r_multiple"].mean(),
        "median_r_multiple": trades["r_multiple"].median(),
        "profit_factor_excl_best_trade": pf_excl_best,
        "avg_hold_bars": trades["hold_bars"].mean(),
        "exit_reason_counts": trades["exit_reason"].value_counts().to_dict(),
    }


def equity_curve_from_trades(trades: pd.DataFrame) -> pd.DataFrame:
    """Per-trade (not calendar-day) compounding equity curve, ordered by
    exit time - appropriate for a low-frequency, state-machine-driven
    strategy like this one rather than a daily-return series."""
    if trades.empty:
        return pd.DataFrame(columns=["exit_time", "equity"])
    ordered = trades.sort_values("exit_time")
    equity = (1 + ordered["return_pct"]).cumprod()
    return pd.DataFrame({"exit_time": ordered["exit_time"].to_numpy(), "equity": equity.to_numpy()})
