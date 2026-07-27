"""Event-driven trade simulator for the composite signal.

Fidelity choices that deliberately diverge from a naive vectorised backtest
of the paper's Appendix A signal column:

1. Execution lag. S_t is only known at the close of bar t (it depends on
   close, vwap and adx *at* t). Trading at that same bar's close would be
   look-ahead. Entries fill at the *next* bar's open.
2. Single position at a time. A new signal while a trade is open is ignored,
   matching the paper's implicit one-trade-per-setup framing (Sec. 5.3).
3. Exit precedence, checked bar-by-bar from entry+1: session rollover (time
   exit, Sec 6.1) -> confirmed-close stop beyond the trigger extreme by a
   multiple of ATR (Sec 5.3) -> VWAP-cross target (Sec 5.3). First hit wins.
4. Costs are modelled as a half round-trip spread charged on both entry and
   exit, applied on the correct side of the market (short sells the bid,
   buys back the ask; long is the mirror) rather than netted as a single
   lump sum, so per-trade PnL matches what a broker statement would show.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class BacktestConfig:
    spread_bps: float = 0.3       # round-trip cost, basis points of price
    stop_atr_mult: float = 0.5    # stop = trigger level +/- this many ATRs
    min_atr: float = 1e-12        # guards against a degenerate (zero) stop


def simulate_trades(df: pd.DataFrame, config: BacktestConfig = BacktestConfig()) -> pd.DataFrame:
    required = {"open", "close", "vwap", "atr", "prev_high", "prev_low", "signal", "session"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"simulate_trades: missing columns {missing}")

    n = len(df)
    open_ = df["open"].to_numpy()
    close = df["close"].to_numpy()
    vwap = df["vwap"].to_numpy()
    atr = df["atr"].to_numpy()
    prev_high = df["prev_high"].to_numpy()
    prev_low = df["prev_low"].to_numpy()
    signal = df["signal"].to_numpy()
    session_codes = pd.factorize(df["session"].to_numpy())[0]
    times = df.index

    half_cost_frac = config.spread_bps / 10_000 / 2

    trades = []
    i = 0
    while i < n - 1:
        sig = signal[i]
        if sig == 0 or np.isnan(atr[i]) or atr[i] < config.min_atr:
            i += 1
            continue

        direction = int(sig)  # -1 short, +1 long
        entry_i = i + 1
        entry_session = session_codes[entry_i]

        raw_entry = open_[entry_i]
        cost = raw_entry * half_cost_frac
        entry_price = raw_entry - cost if direction == -1 else raw_entry + cost

        trigger_level = prev_high[entry_i] if direction == -1 else prev_low[entry_i]
        stop_level = (
            trigger_level + config.stop_atr_mult * atr[entry_i]
            if direction == -1
            else trigger_level - config.stop_atr_mult * atr[entry_i]
        )

        exit_i, exit_reason = None, None
        j = entry_i
        while j < n:
            if session_codes[j] != entry_session:
                exit_i, exit_reason = max(j - 1, entry_i), "session_end"
                break
            if direction == -1 and close[j] > stop_level:
                exit_i, exit_reason = j, "stop"
                break
            if direction == 1 and close[j] < stop_level:
                exit_i, exit_reason = j, "stop"
                break
            if direction == -1 and close[j] <= vwap[j]:
                exit_i, exit_reason = j, "target"
                break
            if direction == 1 and close[j] >= vwap[j]:
                exit_i, exit_reason = j, "target"
                break
            j += 1
        if exit_i is None:
            exit_i, exit_reason = n - 1, "data_end"

        raw_exit = close[exit_i]
        cost = raw_exit * half_cost_frac
        exit_price = raw_exit + cost if direction == -1 else raw_exit - cost

        ret = (entry_price - exit_price) / entry_price if direction == -1 else (exit_price - entry_price) / entry_price

        trades.append(
            {
                "entry_time": times[entry_i],
                "exit_time": times[exit_i],
                "direction": direction,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "return_pct": ret,
                "exit_reason": exit_reason,
                "hold_bars": exit_i - entry_i,
                "adx_at_entry": df["adx"].iloc[entry_i],
                "atr_at_entry": atr[entry_i],
            }
        )
        i = exit_i + 1

    return pd.DataFrame(trades)


def trades_to_daily_returns(trades: pd.DataFrame, index: pd.DatetimeIndex) -> pd.Series:
    """Compound same-day trade returns into a daily return series aligned to
    the full calendar span of `index` (0.0 on days with no trade)."""
    if trades.empty:
        days = pd.date_range(index.min().normalize(), index.max().normalize(), freq="D")
        return pd.Series(0.0, index=days)

    daily = trades.groupby(trades["exit_time"].dt.floor("D"))["return_pct"].apply(
        lambda r: np.prod(1 + r) - 1
    )
    days = pd.date_range(index.min().normalize(), index.max().normalize(), freq="D")
    return daily.reindex(days, fill_value=0.0)
