"""Prop-firm-compliant variant of the dual-momentum rotation: ONE combined
weekly decision (vote across the 4/8/12-week lookbacks, instead of three
parallel fractional sub-books - a real funded account trades one position,
not three), sized by fixed-fractional risk to an ATR-based stop-loss,
monitored on daily closes so intra-week drawdowns are actually caught (the
plain vol-capped version in engine.py has NO intra-week risk control at
all - this module exists specifically to add that).

Optional extensions on top of the base ATR-stop, all disabled by default:
  - `min_agree`: require N of the 3 lookbacks to agree before taking a
    trade (2 = majority, the original; 3 = unanimous) - a confidence filter
    that skips marginal/split signals, intended to make a tighter stop
    tolerable without more whipsaw.
  - `tp_r_mult`: fixed take-profit at entry + tp_r_mult * stop_distance -
    locks in gains before a full week elapses instead of only exiting at
    the next Wednesday or via the stop.
  - `be_trigger_r`: once price has moved be_trigger_r * stop_distance in
    favor, move the stop to breakeven (entry price) - caps downside
    further without shrinking the initial stop distance.

Explicitly disclosed limitations:
  - The stop/TP/BE are checked on DAILY closes, not intraday/tick data - a
    real stop could fill worse (slippage/gaps), especially in Bitcoin.
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


def composite_position(weekly: pd.DataFrame, lookbacks: tuple[int, ...] = (4, 8, 12), min_agree: int = 2) -> pd.Series:
    """One position per week (gold/btc/cash): requires `min_agree` of the
    per-lookback dual-momentum decisions to agree on the SAME non-cash
    asset (2 = majority, 3 = unanimous/all-agree). Anything short of that
    falls back to cash - conservative by construction."""
    votes = []
    for lb in lookbacks:
        mom = weekly[["gold", "btc"]].pct_change(lb)
        long_btc = (mom["btc"] > mom["gold"]) & (mom["btc"] > 0)
        long_gold = (mom["gold"] > mom["btc"]) & (mom["gold"] > 0)
        votes.append(pd.Series(np.where(long_btc, "btc", np.where(long_gold, "gold", "cash")), index=weekly.index))
    stacked = pd.concat(votes, axis=1)

    def decide(row: pd.Series) -> str:
        counts = row.value_counts()
        for asset in ("btc", "gold"):
            if counts.get(asset, 0) >= min_agree:
                return asset
        return "cash"

    return stacked.apply(decide, axis=1)


# kept for backward compatibility with earlier scripts/pages
def majority_composite_position(weekly: pd.DataFrame, lookbacks: tuple[int, ...] = (4, 8, 12)) -> pd.Series:
    return composite_position(weekly, lookbacks, min_agree=2)


def simulate_risk_based(
    daily: dict[str, pd.DataFrame],
    weekly_decision: pd.Series,
    risk_pct: float = 0.005,
    atr_mult: float = 3.0,
    atr_window: int = 14,
    tp_r_mult: float | None = None,
    be_trigger_r: float | None = None,
    starting_equity: float = 100_000.0,
) -> pd.DataFrame:
    atr = {name: compute_atr(df, atr_window) for name, df in daily.items()}
    close = {name: df["close"] for name, df in daily.items()}

    common_index = close["gold"].index.intersection(close["btc"].index).sort_values()
    decision_dates = set(weekly_decision.index)

    running_equity = starting_equity
    position = None  # dict: asset, entry_price, stop_price, stop_distance_price, tp_price, shares, be_moved
    rows = []

    for date in common_index:
        stopped_out = False
        tp_hit = False

        if position is not None:
            px = close[position["asset"]].loc[date]

            if be_trigger_r is not None and not position["be_moved"]:
                favorable_r = (px - position["entry_price"]) / position["stop_distance_price"]
                if favorable_r >= be_trigger_r:
                    position["stop_price"] = position["entry_price"]
                    position["be_moved"] = True

            if px <= position["stop_price"]:
                running_equity += position["shares"] * (position["stop_price"] - position["entry_price"])
                position = None
                stopped_out = True
            elif position["tp_price"] is not None and px >= position["tp_price"]:
                running_equity += position["shares"] * (position["tp_price"] - position["entry_price"])
                position = None
                tp_hit = True

        if date in decision_dates and position is not None:
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
                    tp_price = entry_price + tp_r_mult * stop_distance_price if tp_r_mult is not None else None
                    stop_distance_pct = stop_distance_price / entry_price
                    notional_fraction = min(risk_pct / stop_distance_pct, 1.0)
                    position_value = notional_fraction * running_equity
                    shares = position_value / entry_price
                    position = {
                        "asset": chosen, "entry_price": entry_price, "stop_price": stop_price,
                        "stop_distance_price": stop_distance_price, "tp_price": tp_price,
                        "shares": shares, "notional_fraction": notional_fraction, "be_moved": False,
                    }

        equity_today = running_equity
        if position is not None:
            equity_today += position["shares"] * (close[position["asset"]].loc[date] - position["entry_price"])

        rows.append({
            "date": date, "equity": equity_today,
            "asset": position["asset"] if position else "cash",
            "notional_fraction": position["notional_fraction"] if position else 0.0,
            "stopped_out_today": stopped_out, "tp_hit_today": tp_hit,
        })

    out = pd.DataFrame(rows).set_index("date")
    out["daily_return"] = out["equity"].pct_change()
    return out
