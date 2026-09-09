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
    trades: pd.DataFrame,
    starting_equity: float = 100_000.0,
    risk_pct: float = 0.005,
    risk_multiplier: pd.Series | None = None,
) -> pd.DataFrame:
    """Returns trades sorted by exit_time with added columns: r_multiple,
    risk_amount (equity at the time, x risk_pct [x risk_multiplier]),
    pnl_dollar, equity (after this trade). No compounding within a single
    overlapping day (this strategy is one-trade-at-a-time by construction -
    see engine.py), so a simple sequential walk is correct here, unlike a
    multi-position engine.

    risk_multiplier (2026-09-09, cross-asset rate-momentum research):
    date-indexed Series (index = plain `datetime.date`, matching
    cls_practical.rates' convention), keyed by the trade's own ENTRY date
    (not exit) since that's when the rate-momentum reading is available
    without lookahead. If given, each trade's risk_amount is risk_pct-of-
    equity times risk_multiplier.get(that entry date, 1.0) instead of the
    flat amount - same "scale, don't gate" pattern as
    cls_practical/engine.py::simulate_cls_practical(risk_multiplier=...).
    None (default) leaves the flat-risk behaviour byte-for-byte unchanged."""

    if trades.empty:
        return trades.assign(r_multiple=pd.Series(dtype=float), pnl_dollar=pd.Series(dtype=float), equity=pd.Series(dtype=float))

    out = trades.sort_values("exit_time").reset_index(drop=True).copy()
    sign = out["direction"].map({"long": 1, "short": -1})
    price_move = sign * (out["exit_price"] - out["entry_price"])
    out["r_multiple"] = price_move / out["stop_distance"]
    entry_dates = out["entry_time"].dt.tz_localize(None).dt.date

    equity = starting_equity
    risk_amounts, pnl_dollars, equities = [], [], []
    for r, entry_date in zip(out["r_multiple"], entry_dates):
        mult = risk_multiplier.get(entry_date, 1.0) if risk_multiplier is not None else 1.0
        risk_amount = equity * risk_pct * mult
        pnl = r * risk_amount
        equity += pnl
        risk_amounts.append(risk_amount)
        pnl_dollars.append(pnl)
        equities.append(equity)

    out["risk_amount"] = risk_amounts
    out["pnl_dollar"] = pnl_dollars
    out["equity"] = equities
    return out
