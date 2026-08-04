"""Fixed-fractional position sizing + compounding equity simulation - turns
the per-trade price return_pct (used everywhere else in this package) into
an actual dollar equity curve for a given starting balance and risk-per-
trade, same convention as the OU-Modell live bot's own risk_pct sizing
(see OU-Modell-MT5-Bridge/sizing.py: risk_amount = equity * risk_pct,
lots sized so a full stop-loss costs exactly that amount).

Uses the trade's own R-multiple (return relative to ITS stop distance, not
the raw price return) so the risk-per-trade is genuinely constant in dollar
terms regardless of how wide a given night's Asian range was - a trade
that risked more (wider range) doesn't just accidentally win/lose more in
dollars than one that risked less."""

import pandas as pd


def simulate_equity(
    trades: pd.DataFrame, starting_equity: float = 100_000.0, risk_pct: float = 0.005
) -> pd.DataFrame:
    """Returns trades sorted by exit_time with added columns: r_multiple,
    risk_amount (equity at the time, x risk_pct), pnl_dollar, equity (after
    this trade). No compounding within a single overlapping day (this
    strategy is one-trade-at-a-time by construction - see engine.py), so a
    simple sequential walk is correct here, unlike a multi-position engine."""

    if trades.empty:
        return trades.assign(r_multiple=pd.Series(dtype=float), pnl_dollar=pd.Series(dtype=float), equity=pd.Series(dtype=float))

    out = trades.sort_values("exit_time").reset_index(drop=True).copy()
    sign = out["direction"].map({"long": 1, "short": -1})
    price_move = sign * (out["exit_price"] - out["entry_price"])
    out["r_multiple"] = price_move / out["stop_distance"]

    equity = starting_equity
    risk_amounts, pnl_dollars, equities = [], [], []
    for r in out["r_multiple"]:
        risk_amount = equity * risk_pct
        pnl = r * risk_amount
        equity += pnl
        risk_amounts.append(risk_amount)
        pnl_dollars.append(pnl)
        equities.append(equity)

    out["risk_amount"] = risk_amounts
    out["pnl_dollar"] = pnl_dollars
    out["equity"] = equities
    return out
