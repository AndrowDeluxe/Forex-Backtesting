"""Trade simulation: a fork of ema_strategy.backtest.simulate_trades with one
addition — `exit_on_adx_exhaustion`, testing the ADX-VWAP paper's Foundation
3 (momentum decay = exhaustion) as an EXIT trigger for a trend-following
strategy, mirroring its role as an ENTRY trigger for the mean-reversion
strategy: if the trend was strong at entry (ADX >= threshold) and then
genuinely turns over (ADX falling for `adx_exhaustion_confirm_bars`
consecutive bars), the trend this trade is riding is losing steam, so exit
rather than wait for the slower price/bias-based invalidation.

Kept as a fork rather than a shared/parametrised function because the new
branch needs to sit inside the per-bar loop next to the existing
trend-invalidation check, not wrap the function from outside.
"""

import numpy as np
import pandas as pd


def simulate_trades(
    df: pd.DataFrame, risk_pct=0.01, rr=2.0, sl_buffer_atr=0.1,
    initial_equity=10_000.0, max_bars_in_trade=200,
    invalidation_confirm_bars: int = 1,
    sl_mode: str = "signal_extreme", atr_multiplier: float = 1.5,
    exit_on_htf_bias_flip: bool = False, htf_bias_col: str = "daily_bias",
    use_trailing_stop: bool = False, breakeven_trigger_r: float = 1.0,
    trail_atr_mult: float = 2.5, adx_col: str = "daily_adx",
    adx_threshold: float = 25.0,
    exit_on_adx_exhaustion: bool = False, adx_exhaustion_col: str = "daily_adx",
    adx_exhaustion_entry_threshold: float = 25.0, adx_exhaustion_confirm_bars: int = 2,
):
    """See ema_strategy.backtest.simulate_trades for the parameters this
    shares with the original. New parameters:

    exit_on_adx_exhaustion: if True, once in a trade where
        `adx_exhaustion_col` was >= `adx_exhaustion_entry_threshold` at
        entry, exit as soon as that column has fallen for
        `adx_exhaustion_confirm_bars` consecutive bars - independent of (and
        checked alongside) the existing price/bias trend-invalidation exit.
    """
    df = df.reset_index()
    n = len(df)
    atr = (df["High"] - df["Low"]).rolling(14).mean()
    adx_delta = df[adx_exhaustion_col].diff() if exit_on_adx_exhaustion else None

    equity = initial_equity
    equity_curve = np.full(n, np.nan)
    trades = []

    in_pos = False
    direction = 0
    entry_price = sl = tp = entry_idx = None
    pos_size = 0.0
    adverse_streak = 0
    adx_exhaustion_streak = 0
    adx_at_entry = None
    risk_per_unit = None
    trade_extreme = None
    trailing_active = False

    for i in range(n):
        equity_curve[i] = equity

        if in_pos:
            bar = df.iloc[i]
            exit_price = None
            reason = None

            if use_trailing_stop:
                if direction == 1:
                    trade_extreme = max(trade_extreme, bar["High"])
                    if not trailing_active and bar["High"] >= entry_price + breakeven_trigger_r * risk_per_unit:
                        trailing_active = True
                    if trailing_active:
                        chandelier_level = trade_extreme - trail_atr_mult * atr.iloc[i]
                        sl = max(sl, entry_price, chandelier_level)
                else:
                    trade_extreme = min(trade_extreme, bar["Low"])
                    if not trailing_active and bar["Low"] <= entry_price - breakeven_trigger_r * risk_per_unit:
                        trailing_active = True
                    if trailing_active:
                        chandelier_level = trade_extreme + trail_atr_mult * atr.iloc[i]
                        sl = min(sl, entry_price, chandelier_level)

            if direction == 1:
                if bar["Low"] <= sl:
                    exit_price, reason = sl, "SL" if not trailing_active else "Trailing-Stop"
                elif tp is not None and bar["High"] >= tp:
                    exit_price, reason = tp, "TP"
                else:
                    if exit_on_htf_bias_flip:
                        adverse_cond = bar[htf_bias_col] != 1
                    else:
                        adverse_cond = bar["Close"] < bar["trigger_ema"]
                    adverse_streak = adverse_streak + 1 if adverse_cond else 0
                    if adverse_streak >= invalidation_confirm_bars:
                        exit_price, reason = bar["Close"], "Trend-Invalidierung"
            else:
                if bar["High"] >= sl:
                    exit_price, reason = sl, "SL" if not trailing_active else "Trailing-Stop"
                elif tp is not None and bar["Low"] <= tp:
                    exit_price, reason = tp, "TP"
                else:
                    if exit_on_htf_bias_flip:
                        adverse_cond = bar[htf_bias_col] != -1
                    else:
                        adverse_cond = bar["Close"] > bar["trigger_ema"]
                    adverse_streak = adverse_streak + 1 if adverse_cond else 0
                    if adverse_streak >= invalidation_confirm_bars:
                        exit_price, reason = bar["Close"], "Trend-Invalidierung"

            if (
                exit_price is None
                and exit_on_adx_exhaustion
                and adx_at_entry is not None
                and adx_at_entry >= adx_exhaustion_entry_threshold
            ):
                declining = adx_delta.iloc[i] < 0 if not np.isnan(adx_delta.iloc[i]) else False
                adx_exhaustion_streak = adx_exhaustion_streak + 1 if declining else 0
                if adx_exhaustion_streak >= adx_exhaustion_confirm_bars:
                    exit_price, reason = bar["Close"], "ADX-Erschöpfung"

            if exit_price is None and (i - entry_idx) >= max_bars_in_trade:
                exit_price, reason = bar["Close"], "Zeitlimit"

            if exit_price is not None:
                pnl = pos_size * (exit_price - entry_price) * direction
                equity += pnl
                trades.append({
                    "entry_time": df.loc[entry_idx, "Date"],
                    "exit_time": bar["Date"],
                    "direction": "LONG" if direction == 1 else "SHORT",
                    "entry": entry_price, "exit": exit_price, "sl": sl, "tp": tp,
                    "pnl": pnl,
                    "reason": reason,
                })
                in_pos = False
            continue

        if i < 1 or np.isnan(atr.iloc[i]):
            continue

        bar = df.iloc[i]
        if bar["signal"] == 1:
            direction = 1
            entry_idx = i + 1 if i + 1 < n else None
            if entry_idx is None:
                continue
            entry_price = df.loc[entry_idx, "Open"]
            if sl_mode == "atr_multiple":
                sl = entry_price - atr_multiplier * atr.iloc[i]
            else:
                sl = bar["Low"] - sl_buffer_atr * atr.iloc[i]
            risk_per_unit = entry_price - sl
            if risk_per_unit <= 0:
                continue
            tp = entry_price + rr * risk_per_unit
            if use_trailing_stop and bar.get(adx_col, np.nan) >= adx_threshold:
                tp = None
            risk_amount = equity * risk_pct
            pos_size = risk_amount / risk_per_unit
            in_pos = True
            adverse_streak = 0
            adx_exhaustion_streak = 0
            adx_at_entry = bar.get(adx_exhaustion_col, np.nan) if exit_on_adx_exhaustion else None
            trade_extreme = entry_price
            trailing_active = False
        elif bar["signal"] == -1:
            direction = -1
            entry_idx = i + 1 if i + 1 < n else None
            if entry_idx is None:
                continue
            entry_price = df.loc[entry_idx, "Open"]
            if sl_mode == "atr_multiple":
                sl = entry_price + atr_multiplier * atr.iloc[i]
            else:
                sl = bar["High"] + sl_buffer_atr * atr.iloc[i]
            risk_per_unit = sl - entry_price
            if risk_per_unit <= 0:
                continue
            tp = entry_price - rr * risk_per_unit
            if use_trailing_stop and bar.get(adx_col, np.nan) >= adx_threshold:
                tp = None
            risk_amount = equity * risk_pct
            pos_size = risk_amount / risk_per_unit
            in_pos = True
            adverse_streak = 0
            adx_exhaustion_streak = 0
            adx_at_entry = bar.get(adx_exhaustion_col, np.nan) if exit_on_adx_exhaustion else None
            trade_extreme = entry_price
            trailing_active = False

    trades_df = pd.DataFrame(trades)
    if not trades_df.empty:
        trades_df["r_multiple"] = trades_df["pnl"] / (initial_equity * risk_pct)
    eq = pd.Series(equity_curve, index=df["Date"])
    return trades_df, eq
