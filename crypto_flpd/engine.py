"""Trading simulations for both test phases (see plan in
resources/crypto-hurst-wyckoff-cycles.md's Express section once results are
in). Same fill convention as btc_ema_cross/engine.py throughout: signal
evaluated on bar i-1's close, filled at bar i's open, 0.1%/side commission
(this repo's real BTC standard, more conservative than the paper's 0.04%
VIP-taker rate) - a bar-close strategy, not the paper's sub-5-second
execution-window assumption, which this repo's poll-based MT5-bridge
infrastructure could not realistically achieve anyway.

Phase A: `simulate_ema_cross_with_hurst_exit` - the EXACT
btc_ema_cross/engine.py::simulate_ema_cross baseline (copied, not
imported, so the paper's Hurst-collapse exit can be added as one extra
clause without touching the production module), plus an early exit when
Baustein 1's collapse signal fires while in a position - answers the open
crash-/trend-end-filter question from resources/trend-following-
momentum.md (Nachtrag 2026-08-14 (5)).

Phase B: `simulate_flpd` - a standalone long/short/flat engine using Psi
(Baustein 3, fed by Baustein 2's liquidity weight) for entries and the
Hurst collapse (Baustein 1) for exits, mirroring the paper's own Sec 5.4
strategy definition (Psi crosses its rolling 70th/30th percentile) as
closely as the available bar data allows."""

import numpy as np
import pandas as pd

COMMISSION = 0.001


def simulate_ema_cross_with_hurst_exit(
    df: pd.DataFrame, fast: int, slow: int, hurst_collapse: pd.Series, sim_from: pd.Timestamp | None = None
) -> dict:
    close = df["close"]
    open_ = df["open"]
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    above = ema_fast > ema_slow
    above_prev = above.shift(1, fill_value=False)

    go_long = (above & ~above_prev).to_numpy()
    go_flat_ema = (~above & above_prev).to_numpy()
    go_flat_hurst = hurst_collapse.reindex(df.index).fillna(False).to_numpy()
    go_flat = go_flat_ema | go_flat_hurst
    close_arr, open_arr = close.to_numpy(), open_.to_numpy()

    start_i = max(df.index.searchsorted(sim_from) if sim_from is not None else 1, 1)

    position = 0
    entry_price = None
    daily_returns = []
    trade_returns = []
    exit_reasons = []
    for i in range(start_i, len(df)):
        ret = 0.0
        if position == 0 and go_long[i - 1]:
            position = 1
            entry_price = open_arr[i] * (1 + COMMISSION)
            ret = close_arr[i] / entry_price - 1
        elif position == 1 and go_flat[i - 1]:
            exit_price = open_arr[i] * (1 - COMMISSION)
            ret = exit_price / close_arr[i - 1] - 1
            trade_returns.append(exit_price / entry_price - 1)
            exit_reasons.append("hurst_collapse" if go_flat_hurst[i - 1] else "ema_crossunder")
            position = 0
        elif position == 1:
            ret = close_arr[i] / close_arr[i - 1] - 1
        daily_returns.append(ret)

    daily_returns = pd.Series(daily_returns, index=df.index[start_i:])
    equity = (1 + daily_returns).cumprod()

    n_years = (df.index[-1] - df.index[start_i]).days / 365.25
    total_return = equity.iloc[-1] - 1
    cagr = equity.iloc[-1] ** (1 / n_years) - 1 if n_years > 0 else float("nan")
    max_dd = (equity / equity.cummax() - 1).min()

    wins = [t for t in trade_returns if t > 0]
    losses = [t for t in trade_returns if t <= 0]
    win_rate = len(wins) / len(trade_returns) if trade_returns else float("nan")
    profit_factor = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else float("nan")

    return {
        "fast": fast, "slow": slow, "n_trades": len(trade_returns),
        "win_rate": win_rate, "profit_factor": profit_factor,
        "total_return": total_return, "cagr": cagr, "max_dd": max_dd, "equity": equity,
        "exit_reason_counts": pd.Series(exit_reasons).value_counts().to_dict() if exit_reasons else {},
        "hurst_exit_mask": pd.Series(go_flat_hurst, index=df.index),
    }


def simulate_flpd(
    df: pd.DataFrame,
    psi: pd.Series,
    hurst_collapse: pd.Series,
    entry_window: int = 30 * 24,
    upper_q: float = 0.70,
    lower_q: float = 0.30,
    sim_from: pd.Timestamp | None = None,
    entry_target_override: pd.Series | None = None,
) -> dict:
    """`entry_target_override` (values in {-1, 0, 1}, aligned to `df.index`):
    if given, REPLACES the Psi-derived entry signal entirely (used by
    significance.signal_timing_significance to re-simulate under a
    shuffled entry-timing null while holding every other rule fixed) -
    default None reproduces the paper's own Sec 5.4 rule (Psi crosses its
    rolling upper/lower percentile)."""
    close, open_ = df["close"], df["open"]
    close_arr, open_arr = close.to_numpy(), open_.to_numpy()
    psi = psi.reindex(df.index)
    collapse = hurst_collapse.reindex(df.index).fillna(False).to_numpy()

    min_p = min(max(entry_window // 2, 10), entry_window)
    upper = psi.rolling(entry_window, min_periods=min_p).quantile(upper_q)
    lower = psi.rolling(entry_window, min_periods=min_p).quantile(lower_q)
    median = psi.rolling(entry_window, min_periods=min_p).quantile(0.5)

    cross_median_down = ((psi < median) & (psi.shift(1) >= median.shift(1))).fillna(False).to_numpy()
    cross_median_up = ((psi > median) & (psi.shift(1) <= median.shift(1))).fillna(False).to_numpy()

    if entry_target_override is not None:
        entry_target = entry_target_override.reindex(df.index).fillna(0).to_numpy()
    else:
        cross_up = ((psi > upper) & (psi.shift(1) <= upper.shift(1))).fillna(False).to_numpy()
        cross_down = ((psi < lower) & (psi.shift(1) >= lower.shift(1))).fillna(False).to_numpy()
        entry_target = np.where(cross_up, 1, np.where(cross_down, -1, 0))

    start_i = max(df.index.searchsorted(sim_from) if sim_from is not None else entry_window, entry_window)

    side = 0
    entry_price = None
    entry_i = None
    daily_returns = []
    trade_returns = []
    trade_log = []
    for i in range(start_i, len(df)):
        ret = 0.0
        was_side = side
        exit_signal = was_side != 0 and (
            (was_side == 1 and (collapse[i - 1] or cross_median_down[i - 1]))
            or (was_side == -1 and (collapse[i - 1] or cross_median_up[i - 1]))
        )
        if exit_signal:
            exit_price = open_arr[i] * (1 - COMMISSION if was_side == 1 else 1 + COMMISSION)
            trade_ret = was_side * (exit_price / entry_price - 1)
            trade_returns.append(trade_ret)
            trade_log.append(
                {
                    "entry_time": df.index[entry_i], "exit_time": df.index[i],
                    "side": was_side, "ret": trade_ret,
                    "exit_reason": "hurst_collapse" if collapse[i - 1] else "psi_median_cross",
                }
            )
            ret += was_side * (exit_price / close_arr[i - 1] - 1)
            side = 0

        if side == 0:
            target = int(entry_target[i - 1])
            if target != 0:
                entry_price = open_arr[i] * (1 + COMMISSION if target == 1 else 1 - COMMISSION)
                ret += target * (close_arr[i] / entry_price - 1)
                side = target
                entry_i = i
        else:
            ret = side * (close_arr[i] / close_arr[i - 1] - 1)

        daily_returns.append(ret)

    daily_returns = pd.Series(daily_returns, index=df.index[start_i:])
    equity = (1 + daily_returns).cumprod()
    n_years = (df.index[-1] - df.index[start_i]).days / 365.25
    total_return = equity.iloc[-1] - 1
    cagr = equity.iloc[-1] ** (1 / n_years) - 1 if n_years > 0 else float("nan")
    max_dd = (equity / equity.cummax() - 1).min()

    wins = [t for t in trade_returns if t > 0]
    losses = [t for t in trade_returns if t <= 0]
    win_rate = len(wins) / len(trade_returns) if trade_returns else float("nan")
    profit_factor = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else float("nan")

    return {
        "n_trades": len(trade_returns), "win_rate": win_rate, "profit_factor": profit_factor,
        "total_return": total_return, "cagr": cagr, "max_dd": max_dd, "equity": equity,
        "trades": pd.DataFrame(trade_log),
        "entry_target": pd.Series(entry_target, index=df.index),
    }
