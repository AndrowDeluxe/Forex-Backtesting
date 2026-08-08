"""Multi-asset mean-reversion pullback system, per Beluská & Vojtko (2026):
200-day uptrend filter + N-consecutive-down-day trigger + 1-day hold,
applied to several assets SIMULTANEOUSLY with dynamic equal-weight sizing
across whichever signals fire together on the same trigger day (weight =
1/N_active that day) - this is the key structural difference from
gold_pullback_ma's single-asset version tested earlier, and the reason this
package exists separately rather than just extending that one."""

import numpy as np
import pandas as pd

from gold_pullback_ma.engine import _consecutive_down_days


def simulate_multiasset_pullback(
    data: dict[str, pd.DataFrame], ma_window: int = 200, n_down_days: int = 2, cost_bps: float = 5.0
) -> pd.Series:
    signals = {}
    common_index = None
    for name, df in data.items():
        close = df["close"]
        uptrend = close > close.rolling(ma_window).mean()
        consec_down = _consecutive_down_days(close)
        signals[name] = uptrend & (consec_down == n_down_days)
        common_index = close.index if common_index is None else common_index.intersection(close.index)
    common_index = common_index.sort_values()

    n_active = pd.Series(0, index=common_index)
    aligned_signals = {}
    for name in data:
        sig = signals[name].reindex(common_index).fillna(False)
        aligned_signals[name] = sig
        n_active += sig.astype(int)

    portfolio_ret = pd.Series(0.0, index=common_index)
    n_bars = len(common_index)
    for name, df in data.items():
        df_aligned = df.reindex(common_index)
        open_ = df_aligned["open"].to_numpy()
        close_ = df_aligned["close"].to_numpy()
        trigger_positions = np.where(aligned_signals[name].to_numpy())[0]
        for p in trigger_positions:
            if p + 1 >= n_bars:
                continue
            n = n_active.iloc[p]
            if n == 0:
                continue
            entry_price, exit_price = open_[p + 1], close_[p + 1]
            if np.isnan(entry_price) or np.isnan(exit_price) or entry_price <= 0:
                continue
            gross = (exit_price - entry_price) / entry_price
            portfolio_ret.iloc[p + 1] += (gross - cost_bps / 1e4) / n

    return portfolio_ret
