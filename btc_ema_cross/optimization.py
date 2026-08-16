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
    above_prev = above.shift(1, fill_value=False)

    go_long = (above & ~above_prev).to_numpy()

    go_flat = (~above & above_prev).to_numpy()
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
    above_prev = above.shift(1, fill_value=False)

    go_long = (above & ~above_prev).to_numpy()

    go_flat = (~above & above_prev).to_numpy()
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


def simulate_chandelier_exit(df: pd.DataFrame, capital: float, risk_pct: float,
                              atr_period: int, atr_stop_mult: float, chandelier_mult: float,
                              sim_from: pd.Timestamp | None = None) -> dict:
    """ATR-based TRAILING stop (Chandelier Exit): stop = highest close since
    entry - chandelier_mult * current ATR, ratcheting up only (never loosens
    below the initial fixed ATR stop). Unlike a fixed take-profit this
    doesn't cap upside at a hard target - it lets the trade run to new highs
    while progressively locking in some profit. Finding (2026-08-15):
    consistently WORSE than the plain crossunder+fixed-stop baseline across
    every tested multiplier (2.0x-4.0x), both IS and OOS - same mechanism as
    the take-profit: it exits before the actual trend-reversal crossunder,
    capping exactly the large trend trades the edge depends on."""
    close, open_, low = df["close"], df["open"], df["low"]
    ema_fast = close.ewm(span=9, adjust=False).mean()
    ema_slow = close.ewm(span=21, adjust=False).mean()
    above = ema_fast > ema_slow
    above_prev = above.shift(1, fill_value=False)

    go_long = (above & ~above_prev).to_numpy()

    go_flat = (~above & above_prev).to_numpy()
    atr = compute_atr(df, atr_period)

    start_i = max(df.index.searchsorted(sim_from) if sim_from is not None else 1, 1)

    cash = capital
    qty = 0.0
    entry_price = None
    stop_price = None
    trade_risk_dollar = None
    highest_close_since_entry = None
    in_pos = False
    trades = []
    equity_curve = [capital]
    equity_dates = [df.index[start_i - 1]]

    for i in range(start_i, len(df)):
        exited_today = False
        if in_pos:
            highest_close_since_entry = max(highest_close_since_entry, close.iloc[i - 1])
            chandelier_stop = highest_close_since_entry - chandelier_mult * atr.iloc[i - 1]
            stop_price = max(stop_price, chandelier_stop)

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

        if not in_pos and not exited_today and go_long[i - 1] and pd.notna(atr.iloc[i - 1]):
            raw_entry = open_.iloc[i]
            entry_fill = raw_entry * (1 + COMMISSION)
            stop_dist = atr_stop_mult * atr.iloc[i - 1]
            if stop_dist > 0:
                target_qty = (cash * risk_pct) / stop_dist
                max_qty = cash / entry_fill
                qty = min(target_qty, max_qty)
                entry_price = entry_fill
                stop_price = raw_entry - stop_dist
                trade_risk_dollar = qty * stop_dist
                highest_close_since_entry = raw_entry
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


def simulate_volume_exhaustion_exit(df: pd.DataFrame, capital: float, risk_pct: float,
                                     atr_period: int, atr_stop_mult: float, vol_lookback: int,
                                     vol_threshold: float, min_r_to_check: float,
                                     sim_from: pd.Timestamp | None = None) -> dict:
    """Exit early (at next open) when today's volume falls below
    vol_threshold * its own vol_lookback-day average WHILE the trade is at
    least min_r_to_check R in profit - "participation is drying up, take
    the win." Finding (2026-08-15): near-neutral at a tight threshold
    (<30%, rarely fires) but clearly harmful at looser thresholds
    (50-70%) - same pattern as the take-profit/Chandelier tests: cuts off
    the large trend trades the edge depends on."""
    close, open_, low, vol = df["close"], df["open"], df["low"], df["volume"]
    ema_fast = close.ewm(span=9, adjust=False).mean()
    ema_slow = close.ewm(span=21, adjust=False).mean()
    above = ema_fast > ema_slow
    above_prev = above.shift(1, fill_value=False)

    go_long = (above & ~above_prev).to_numpy()

    go_flat = (~above & above_prev).to_numpy()
    atr = compute_atr(df, atr_period)
    vol_ratio = vol / vol.rolling(vol_lookback).mean()

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
        if in_pos:
            unrealized_r = (close.iloc[i - 1] - entry_price) / (trade_risk_dollar / qty)
            if unrealized_r >= min_r_to_check and pd.notna(vol_ratio.iloc[i - 1]) and vol_ratio.iloc[i - 1] < vol_threshold:
                exit_fill = open_.iloc[i] * (1 - COMMISSION)
                pnl = qty * (exit_fill - entry_price)
                trades.append({"pnl": pnl, "r": pnl / trade_risk_dollar})
                cash += qty * exit_fill
                qty, in_pos, exited_today = 0.0, False, True

        if in_pos and not exited_today and go_flat[i - 1]:
            exit_fill = open_.iloc[i] * (1 - COMMISSION)
            pnl = qty * (exit_fill - entry_price)
            trades.append({"pnl": pnl, "r": pnl / trade_risk_dollar})
            cash += qty * exit_fill
            qty, in_pos, exited_today = 0.0, False, True
        elif in_pos and not exited_today and low.iloc[i] <= stop_price:
            exit_fill = stop_price * (1 - COMMISSION)
            pnl = qty * (exit_fill - entry_price)
            trades.append({"pnl": pnl, "r": pnl / trade_risk_dollar})
            cash += qty * exit_fill
            qty, in_pos, exited_today = 0.0, False, True

        if not in_pos and not exited_today and go_long[i - 1] and pd.notna(atr.iloc[i - 1]):
            raw_entry = open_.iloc[i]
            entry_fill = raw_entry * (1 + COMMISSION)
            stop_dist = atr_stop_mult * atr.iloc[i - 1]
            if stop_dist > 0:
                target_qty = (cash * risk_pct) / stop_dist
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
    win_rate = len(wins) / len(trades) if trades else float("nan")
    profit_factor = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else float("nan")
    return {
        "n_trades": len(trades), "win_rate": win_rate, "profit_factor": profit_factor,
        "cagr": cagr, "max_dd": max_dd, "end_equity": equity.iloc[-1],
    }


def simulate_asymmetric_short(df: pd.DataFrame, capital: float, risk_pct: float, short_frac: float,
                               atr_period: int, atr_stop_mult: float,
                               sim_from: pd.Timestamp | None = None) -> dict:
    """Instead of going flat at the crossunder, opens a SMALL short sized at
    short_frac * risk_pct (e.g. 0.25 = quarter-size short), mirroring the
    long leg's ATR-stop mechanics. Finding (2026-08-15): the short leg loses
    money at EVERY tested short_frac (0.1x-1.0x), both IS and OOS, with no
    sign flip anywhere in the range - not a small-sample fluke, a
    consistent drag that scales smoothly with size. Flat remains strictly
    better than any short admixture, however small. Same root cause as the
    full long/short test: a crossunder only means "momentum has cooled",
    not reliably "a sustained downtrend is starting" - BTC's structural
    upward drift makes shorting that signal a negative-expectancy bet
    regardless of position size."""
    close, open_, low, high = df["close"], df["open"], df["low"], df["high"]
    ema_fast = close.ewm(span=9, adjust=False).mean()
    ema_slow = close.ewm(span=21, adjust=False).mean()
    above = ema_fast > ema_slow
    above_prev = above.shift(1, fill_value=False)
    go_long = (above & ~above_prev).to_numpy()
    go_short = (~above & above_prev).to_numpy()
    atr = compute_atr(df, atr_period)

    start_i = max(df.index.searchsorted(sim_from) if sim_from is not None else 1, 1)

    cash = capital
    qty = 0.0
    side = 0  # 0 flat, 1 long, -1 short
    entry_price = None
    stop_price = None
    trade_risk_dollar = None
    trades = []
    equity_curve = [capital]
    equity_dates = [df.index[start_i - 1]]

    for i in range(start_i, len(df)):
        exited_today = False
        if side == 1 and go_short[i - 1]:
            exit_fill = open_.iloc[i] * (1 - COMMISSION)
            pnl = qty * (exit_fill - entry_price)
            trades.append({"pnl": pnl, "r": pnl / trade_risk_dollar, "side": "long"})
            cash += qty * exit_fill
            qty, side, exited_today = 0.0, 0, True
        elif side == 1 and low.iloc[i] <= stop_price:
            exit_fill = stop_price * (1 - COMMISSION)
            pnl = qty * (exit_fill - entry_price)
            trades.append({"pnl": pnl, "r": pnl / trade_risk_dollar, "side": "long"})
            cash += qty * exit_fill
            qty, side, exited_today = 0.0, 0, True
        elif side == -1 and go_long[i - 1]:
            exit_fill = open_.iloc[i] * (1 + COMMISSION)
            pnl = qty * (entry_price - exit_fill)
            trades.append({"pnl": pnl, "r": pnl / trade_risk_dollar, "side": "short"})
            cash += pnl
            qty, side, exited_today = 0.0, 0, True
        elif side == -1 and high.iloc[i] >= stop_price:
            exit_fill = stop_price * (1 + COMMISSION)
            pnl = qty * (entry_price - exit_fill)
            trades.append({"pnl": pnl, "r": pnl / trade_risk_dollar, "side": "short"})
            cash += pnl
            qty, side, exited_today = 0.0, 0, True

        if side == 0 and not exited_today and go_long[i - 1] and pd.notna(atr.iloc[i - 1]):
            raw_entry = open_.iloc[i]
            entry_fill = raw_entry * (1 + COMMISSION)
            stop_dist = atr_stop_mult * atr.iloc[i - 1]
            if stop_dist > 0:
                target_qty = (cash * risk_pct) / stop_dist
                max_qty = cash / entry_fill
                qty = min(target_qty, max_qty)
                entry_price = entry_fill
                stop_price = raw_entry - stop_dist
                trade_risk_dollar = qty * stop_dist
                cash -= qty * entry_fill
                side = 1
        elif side == 0 and not exited_today and go_short[i - 1] and pd.notna(atr.iloc[i - 1]) and short_frac > 0:
            raw_entry = open_.iloc[i]
            entry_fill = raw_entry * (1 - COMMISSION)
            stop_dist = atr_stop_mult * atr.iloc[i - 1]
            if stop_dist > 0:
                qty = (cash * risk_pct * short_frac) / stop_dist
                entry_price = entry_fill
                stop_price = raw_entry + stop_dist
                trade_risk_dollar = qty * stop_dist
                side = -1

        if side == 1:
            equity_curve.append(cash + qty * close.iloc[i])
        elif side == -1:
            equity_curve.append(cash + qty * (entry_price - close.iloc[i]))
        else:
            equity_curve.append(cash)
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
    n_short = sum(1 for t in trades if t["side"] == "short")
    short_pnl = sum(t["pnl"] for t in trades if t["side"] == "short")
    return {
        "n_trades": len(trades), "n_short": n_short, "short_pnl": short_pnl,
        "win_rate": win_rate, "profit_factor": profit_factor,
        "cagr": cagr, "max_dd": max_dd, "end_equity": equity.iloc[-1],
    }
