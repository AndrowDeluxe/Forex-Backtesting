"""Prop-firm-compliant variant of the dual-momentum rotation: ONE combined
weekly decision (majority vote across the 4/8/12-week lookbacks, instead of
three parallel fractional sub-books - a real funded account trades one
position, not three), sized by fixed-fractional risk to an ATR-based
stop-loss, monitored on daily closes so intra-week drawdowns are actually
caught (the plain vol-capped version in engine.py has NO intra-week risk
control at all - this module exists specifically to add that).

Explicitly disclosed limitations:
  - The stop is checked on DAILY closes, not intraday/tick data - a real
    stop could fill worse (slippage/gaps), especially in Bitcoin.
  - Gold has no weekend prints; if Bitcoin is held over a weekend crash,
    this simulation (like a real funded account whose platform is closed
    for the FX/metals side) cannot react until the next shared trading day.
    This is a genuine, not just a modeling, limitation.
  - Position size is fixed at entry (start of the week) and only marked to
    market daily - it is not continuously re-risked intraday.
"""

import numpy as np
import pandas as pd

from strategy.indicators import compute_atr


def majority_composite_position(weekly: pd.DataFrame, lookbacks: tuple[int, ...] = (4, 8, 12)) -> pd.Series:
    """One position per week (gold/btc/cash): majority vote across the
    per-lookback dual-momentum decisions. A tie (no lookback agrees on the
    same non-cash asset) falls back to cash - conservative by construction."""
    votes = []
    for lb in lookbacks:
        mom = weekly[["gold", "btc"]].pct_change(lb)
        long_btc = (mom["btc"] > mom["gold"]) & (mom["btc"] > 0)
        long_gold = (mom["gold"] > mom["btc"]) & (mom["gold"] > 0)
        votes.append(pd.Series(np.where(long_btc, "btc", np.where(long_gold, "gold", "cash")), index=weekly.index))
    stacked = pd.concat(votes, axis=1)

    def majority(row: pd.Series) -> str:
        counts = row.value_counts()
        top, top_n = counts.idxmax(), counts.max()
        return top if top_n > len(row) / 2 else "cash"

    return stacked.apply(majority, axis=1)


def simulate_risk_based(
    daily: dict[str, pd.DataFrame],
    weekly_decision: pd.Series,
    risk_pct: float = 0.005,
    atr_mult: float = 3.0,
    atr_window: int = 14,
    starting_equity: float = 100_000.0,
) -> pd.DataFrame:
    atr = {name: compute_atr(df, atr_window) for name, df in daily.items()}
    close = {name: df["close"] for name, df in daily.items()}

    common_index = close["gold"].index.intersection(close["btc"].index).sort_values()
    decision_dates = set(weekly_decision.index)

    running_equity = starting_equity
    position = None  # dict: asset, entry_price, stop_price, shares
    rows = []

    for date in common_index:
        stopped_out = False
        if position is not None:
            px = close[position["asset"]].loc[date]
            if px <= position["stop_price"]:
                running_equity += position["shares"] * (px - position["entry_price"])
                position = None
                stopped_out = True

        if date in decision_dates and not stopped_out and position is not None:
            px = close[position["asset"]].loc[date]
            running_equity += position["shares"] * (px - position["entry_price"])
            position = None

        if date in decision_dates and position is None:
            chosen = weekly_decision.loc[date]
            if chosen in ("gold", "btc"):
                entry_price = close[chosen].loc[date]
                a = atr[chosen].loc[date] if date in atr[chosen].index else np.nan
                if pd.notna(a) and a > 0 and entry_price > 0:
                    stop_distance_price = atr_mult * a
                    stop_price = entry_price - stop_distance_price
                    stop_distance_pct = stop_distance_price / entry_price
                    notional_fraction = min(risk_pct / stop_distance_pct, 1.0)
                    position_value = notional_fraction * running_equity
                    shares = position_value / entry_price
                    position = {
                        "asset": chosen, "entry_price": entry_price, "stop_price": stop_price,
                        "shares": shares, "notional_fraction": notional_fraction,
                    }

        equity_today = running_equity
        if position is not None:
            equity_today += position["shares"] * (close[position["asset"]].loc[date] - position["entry_price"])

        rows.append({
            "date": date, "equity": equity_today,
            "asset": position["asset"] if position else "cash",
            "notional_fraction": position["notional_fraction"] if position else 0.0,
            "stopped_out_today": stopped_out,
        })

    out = pd.DataFrame(rows).set_index("date")
    out["daily_return"] = out["equity"].pct_change()
    return out
