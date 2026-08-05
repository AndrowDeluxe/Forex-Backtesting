"""Dollar-denominated portfolio simulation on a fixed starting account (default
100k), with risk-based position sizing -- mirrors the position-sizing pattern
already used by the live OU-Modell bot (OU-Modell-MT5-Bridge/sizing.py +
executor.calc_open_risk): each trade risks a fixed % of current equity against its
stop distance, and a portfolio-level cap limits aggregate open risk across all
concurrent positions. The paper itself doesn't specify sizing/capital, so this is
an explicit, realistic assumption layered on top of its entry/exit rules.

Same entry/exit rules as bollinger.py (band entry, MA/stop/max-holding exit), but
driven as a single chronological loop across the whole universe so positions share
one equity curve and one risk budget, instead of being backtested independently
per ticker.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

import config


@dataclass
class _Position:
    ticker: str
    direction: int  # 1 long, -1 short
    shares: float
    entry_price: float
    entry_date: pd.Timestamp
    last_price: float
    stop_price: float
    risk_dollars: float
    days_held: int = 0


def _precompute_indicators(panel: pd.DataFrame, tickers: list[str], lookback: int, k: float) -> dict:
    ind = {}
    for t in tickers:
        if t not in panel.columns:
            continue
        price = panel[t].dropna()
        ma = price.rolling(lookback).mean()
        std = price.rolling(lookback).std()
        ind[t] = {
            "price": price,
            "ma": ma,
            "std": std,
            "upper": ma + k * std,
            "lower": ma - k * std,
        }
    return ind


def simulate_portfolio(
    panel: pd.DataFrame,
    tickers: list[str],
    start: str,
    end: str,
    initial_equity: float = config.INITIAL_EQUITY,
    risk_pct: float = config.RISK_PCT_PER_TRADE,
    max_total_risk_pct: float = config.MAX_TOTAL_RISK_PCT,
    max_position_pct: float = config.MAX_POSITION_PCT,
    lookback: int = config.BB_LOOKBACK,
    k: float = config.BB_K,
    max_hold: int = config.MAX_HOLDING_DAYS,
    stop_sigma: float = config.STOP_LOSS_SIGMA,
) -> tuple[pd.Series, list[dict]]:
    ind = _precompute_indicators(panel, tickers, lookback, k)
    all_dates = panel.loc[start:end].index

    equity = initial_equity
    open_risk = 0.0
    positions: dict[str, _Position] = {}
    trades: list[dict] = []
    equity_points = []

    for date in all_dates:
        # 1. mark-to-market + process exits for open positions
        for t in list(positions.keys()):
            data = ind[t]
            if date not in data["price"].index:
                continue
            pos = positions[t]
            price_t = data["price"].loc[date]
            ma_t = data["ma"].loc[date]
            if pd.isna(ma_t):
                continue

            signed_change = (price_t - pos.last_price) if pos.direction == 1 else (pos.last_price - price_t)
            equity += pos.shares * signed_change
            pos.last_price = price_t
            pos.days_held += 1

            exit_now, reason = False, None
            if pos.direction == 1:
                if price_t <= pos.stop_price:
                    exit_now, reason = True, "stop_loss"
                elif price_t >= ma_t:
                    exit_now, reason = True, "mean_revert"
                elif pos.days_held >= max_hold:
                    exit_now, reason = True, "max_holding"
            else:
                if price_t >= pos.stop_price:
                    exit_now, reason = True, "stop_loss"
                elif price_t <= ma_t:
                    exit_now, reason = True, "mean_revert"
                elif pos.days_held >= max_hold:
                    exit_now, reason = True, "max_holding"

            if exit_now:
                pnl_dollars = pos.shares * (
                    (price_t - pos.entry_price) if pos.direction == 1 else (pos.entry_price - price_t)
                )
                trades.append(
                    {
                        "ticker": t,
                        "direction": "long" if pos.direction == 1 else "short",
                        "entry_date": pos.entry_date,
                        "exit_date": date,
                        "entry_price": pos.entry_price,
                        "exit_price": price_t,
                        "shares": pos.shares,
                        "days_held": pos.days_held,
                        "pnl_dollars": pnl_dollars,
                        "pnl_pct": pnl_dollars / (pos.shares * pos.entry_price),
                        "reason": reason,
                    }
                )
                open_risk -= pos.risk_dollars
                del positions[t]

        # 2. new entries for flat tickers
        for t in tickers:
            if t in positions or t not in ind:
                continue
            data = ind[t]
            if date not in data["price"].index:
                continue
            price_t = data["price"].loc[date]
            ma_t, std_t = data["ma"].loc[date], data["std"].loc[date]
            upper_t, lower_t = data["upper"].loc[date], data["lower"].loc[date]
            if pd.isna(ma_t) or pd.isna(std_t) or std_t == 0:
                continue

            direction = 0
            if price_t < lower_t:
                direction = 1
            elif price_t > upper_t:
                direction = -1
            if direction == 0:
                continue

            stop_distance = stop_sigma * std_t
            risk_dollars = equity * risk_pct
            if open_risk + risk_dollars > equity * max_total_risk_pct:
                continue  # portfolio-level risk cap reached, skip this signal

            shares = risk_dollars / stop_distance
            max_shares_by_notional = (equity * max_position_pct) / price_t
            shares = min(shares, max_shares_by_notional)
            shares = float(np.floor(shares))
            if shares <= 0:
                continue

            stop_price = price_t - stop_distance if direction == 1 else price_t + stop_distance
            positions[t] = _Position(
                ticker=t, direction=direction, shares=shares, entry_price=price_t,
                entry_date=date, last_price=price_t, stop_price=stop_price, risk_dollars=risk_dollars,
            )
            open_risk += risk_dollars

        equity_points.append((date, equity))

    equity_series = pd.Series(
        [e for _, e in equity_points], index=[d for d, _ in equity_points], name="equity"
    )
    return equity_series, trades
