"""BTC EMA9/21: optimization-pass helpers (Kelly sizing, dynamic/vol-scaled
risk management, take-profit + regime-filter variants), factored out of
scripts/research_ema_9_21_cross_optimization.py (2026-08-15) so the
Streamlit dashboard reuses the exact tested implementation. See that
script's docstring and knowledge/resources/trend-following-momentum.md
(Nachtrag 2026-08-15 (2)) for the full research log and findings - none of
these were adopted as defaults; kept here for the dashboard's comparison
tables."""

import numpy as np
import pandas as pd

from btc_ema_cross.engine import COMMISSION
from strategy.indicators import compute_adx, compute_atr


def kelly_from_trades(trades: list[dict], label: str) -> dict:
    """trades: list of dicts with an 'r' key (R-multiple), as returned by
    simulate_risk_sized's 'trades' entry. Same formula/convention as
    scripts/research_kelly_ou_model.py: f* = win_rate - (1-win_rate)/b,
    b = avg_win_R / abs(avg_loss_R)."""
    r = np.array([t["r"] for t in trades])
    n = len(r)
    wins, losses = r[r > 0], r[r <= 0]
    p = len(wins) / n if n else float("nan")
    q = 1 - p
    avg_win_r = wins.mean() if len(wins) else float("nan")
    avg_loss_r = losses.mean() if len(losses) else float("nan")
    b = avg_win_r / abs(avg_loss_r) if len(losses) and avg_loss_r != 0 else float("nan")
    kelly_f = p - q / b if b == b and b != 0 else float("nan")
    return {
        "label": label, "n_trades": n, "win_rate": p, "avg_win_r": avg_win_r,
        "avg_loss_r": avg_loss_r, "payoff_ratio_b": b, "kelly_f": kelly_f,
        "half_kelly_f": kelly_f / 2 if kelly_f == kelly_f else float("nan"),
        "quarter_kelly_f": kelly_f / 4 if kelly_f == kelly_f else float("nan"),
    }


def simulate_dynamic_vol_scaled(df: pd.DataFrame, capital: float, base_risk_pct: float,
                                 atr_period: int, atr_stop_mult: float, vol_lookback: int,
                                 scale_min: float, scale_max: float,
                                 sim_from: pd.Timestamp | None = None) -> dict:
    """Dynamic risk_pct: scales base_risk_pct by median(ATR, vol_lookback) /
    current ATR, clipped to [scale_min, scale_max] - risk LESS when current
    vol is elevated vs. its own recent median, MORE when vol is unusually
    calm. Note the ATR-based STOP DISTANCE already implicitly shrinks
    position size in high vol (wider stop -> fewer units for the same $
    risk) - this is a SEPARATE, additional lever on top of that: it changes
    the risk_pct itself, not just the stop distance. Finding (2026-08-15):
    marginally better PF/CAGR, marginally worse MaxDD/worst-day - roughly a
    wash, not a clear win."""
    close, open_, low = df["close"], df["open"], df["low"]
    ema_fast = close.ewm(span=9, adjust=False).mean()
    ema_slow = close.ewm(span=21, adjust=False).mean()
    above = ema_fast > ema_slow
    go_long = (above & ~above.shift(1).fillna(False)).to_numpy()
    go_flat = (~above & above.shift(1).fillna(False)).to_numpy()
    atr = compute_atr(df, atr_period)
    atr_median = atr.rolling(vol_lookback).median()
    vol_scale = (atr_median / atr).clip(scale_min, scale_max)

    start_i = max(df.index.searchsorted(sim_from) if sim_from is not None else 1, 1)

    cash = capital
    qty = 0.0
    entry_price = None
    stop_price = None
    trade_risk_dollar = None
    in_pos = False
    trades = []
    equity_curve = [capital]
    equity_dates = [df.index[start_i - 1]]

    for i in range(start_i, len(df)):
        exited_today = False
        if in_pos and go_flat[i - 1]:
            exit_fill = open_.iloc[i] * (1 - COMMISSION)
            pnl = qty * (exit_fill - entry_price)
            trades.append({"pnl": pnl, "r": pnl / trade_risk_dollar})
            cash += qty * exit_fill
            qty, in_pos, exited_today = 0.0, False, True
        elif in_pos and low.iloc[i] <= stop_price:
            exit_fill = stop_price * (1 - COMMISSION)
            pnl = qty * (exit_fill - entry_price)
            trades.append({"pnl": pnl, "r": pnl / trade_risk_dollar})
            cash += qty * exit_fill
            qty, in_pos, exited_today = 0.0, False, True

        if not in_pos and not exited_today and go_long[i - 1] and pd.notna(atr.iloc[i - 1]) and pd.notna(vol_scale.iloc[i - 1]):
            raw_entry = open_.iloc[i]
            entry_fill = raw_entry * (1 + COMMISSION)
            stop_dist = atr_stop_mult * atr.iloc[i - 1]
            if stop_dist > 0:
                effective_risk_pct = base_risk_pct * vol_scale.iloc[i - 1]
                target_qty = (cash * effective_risk_pct) / stop_dist
                max_qty = cash / entry_fill
                qty = min(target_qty, max_qty)
                entry_price = entry_fill
                stop_price = raw_entry - stop_dist
                trade_risk_dollar = qty * stop_dist
                cash -= qty * entry_fill
                in_pos = True

        equity_curve.append(cash + (qty * close.iloc[i] if in_pos else 0.0))
        equity_dates.append(df.index[i])

    equity = pd.Series(equity_curve, index=equity_dates)
    n_years = (equity_dates[-1] - equity_dates[0]).days / 365.25
    cagr = (equity.iloc[-1] / capital) ** (1 / n_years) - 1 if n_years > 0 else float("nan")
    max_dd = (equity / equity.cummax() - 1).min()
    pnls = [t["pnl"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    profit_factor = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else float("nan")
    daily_ret = equity.pct_change().fillna(0.0)
    return {
        "n_trades": len(trades), "profit_factor": profit_factor, "cagr": cagr, "max_dd": max_dd,
        "end_equity": equity.iloc[-1], "worst_day_pct": daily_ret.min() * 100,
    }


def simulate_with_tp_and_filters(df: pd.DataFrame, capital: float, risk_pct: float,
                                  atr_period: int, atr_stop_mult: float,
                                  tp_r_mult: float | None = None,
                                  adx_min: float | None = None, adx_period: int = 14,
                                  trend_sma: int | None = None,
                                  sim_from: pd.Timestamp | None = None) -> dict:
    """Extends simulate_risk_sized with an optional fixed take-profit
    (tp_r_mult * stop distance) and optional entry filters: adx_min (skip
    entries below this ADX(adx_period) reading) and trend_sma (skip longs
    when close < close's own trend_sma-day SMA). Findings (2026-08-15): ANY
    take-profit level tested makes results worse (both IS and OOS) - the
    edge lives in occasional large winners a TP would cap. Neither ADX nor
    the SMA200 trend filter is robustly confirmed OOS (looks good IS, thin
    and inconsistent OOS samples, n=13-24) - not adopted."""
    close, open_, high, low = df["close"], df["open"], df["high"], df["low"]
    ema_fast = close.ewm(span=9, adjust=False).mean()
    ema_slow = close.ewm(span=21, adjust=False).mean()
    above = ema_fast > ema_slow
    go_long = (above & ~above.shift(1).fillna(False)).to_numpy()
    go_flat = (~above & above.shift(1).fillna(False)).to_numpy()
    atr = compute_atr(df, atr_period)
    adx = compute_adx(df, adx_period)["adx"] if adx_min is not None else None
    sma = close.rolling(trend_sma).mean() if trend_sma is not None else None

    start_i = max(df.index.searchsorted(sim_from) if sim_from is not None else 1, 1)

    cash = capital
    qty = 0.0
    entry_price = None
    stop_price = None
    tp_price = None
    trade_risk_dollar = None
    in_pos = False
    trades = []
    equity_curve = [capital]
    equity_dates = [df.index[start_i - 1]]

    for i in range(start_i, len(df)):
        exited_today = False
        if in_pos and go_flat[i - 1]:
            exit_fill = open_.iloc[i] * (1 - COMMISSION)
            pnl = qty * (exit_fill - entry_price)
            trades.append({"pnl": pnl, "r": pnl / trade_risk_dollar})
            cash += qty * exit_fill
            qty, in_pos, exited_today = 0.0, False, True
        elif in_pos and low.iloc[i] <= stop_price:
            exit_fill = stop_price * (1 - COMMISSION)
            pnl = qty * (exit_fill - entry_price)
            trades.append({"pnl": pnl, "r": pnl / trade_risk_dollar})
            cash += qty * exit_fill
            qty, in_pos, exited_today = 0.0, False, True
        elif in_pos and tp_price is not None and high.iloc[i] >= tp_price:
            exit_fill = tp_price * (1 - COMMISSION)
            pnl = qty * (exit_fill - entry_price)
            trades.append({"pnl": pnl, "r": pnl / trade_risk_dollar})
            cash += qty * exit_fill
            qty, in_pos, exited_today = 0.0, False, True

        if not in_pos and not exited_today and go_long[i - 1] and pd.notna(atr.iloc[i - 1]):
            filter_ok = True
            if adx is not None and (pd.isna(adx.iloc[i - 1]) or adx.iloc[i - 1] < adx_min):
                filter_ok = False
            if sma is not None and (pd.isna(sma.iloc[i - 1]) or close.iloc[i - 1] < sma.iloc[i - 1]):
                filter_ok = False
            if filter_ok:
                raw_entry = open_.iloc[i]
                entry_fill = raw_entry * (1 + COMMISSION)
                stop_dist = atr_stop_mult * atr.iloc[i - 1]
                if stop_dist > 0:
                    target_qty = (cash * risk_pct) / stop_dist
                    max_qty = cash / entry_fill
                    qty = min(target_qty, max_qty)
                    entry_price = entry_fill
                    stop_price = raw_entry - stop_dist
                    tp_price = raw_entry + tp_r_mult * stop_dist if tp_r_mult is not None else None
                    trade_risk_dollar = qty * stop_dist
                    cash -= qty * entry_fill
                    in_pos = True

        equity_curve.append(cash + (qty * close.iloc[i] if in_pos else 0.0))
        equity_dates.append(df.index[i])

    equity = pd.Series(equity_curve, index=equity_dates)
    n_years = (equity_dates[-1] - equity_dates[0]).days / 365.25
    cagr = (equity.iloc[-1] / capital) ** (1 / n_years) - 1 if n_years > 0 else float("nan")
    max_dd = (equity / equity.cummax() - 1).min()
    pnls = [t["pnl"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    win_rate = len(wins) / len(trades) if trades else float("nan")
    profit_factor = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else float("nan")
    return {
        "n_trades": len(trades), "win_rate": win_rate, "profit_factor": profit_factor,
        "cagr": cagr, "max_dd": max_dd, "end_equity": equity.iloc[-1],
    }
