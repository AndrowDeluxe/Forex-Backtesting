"""Dual-momentum rotation between Gold and Bitcoin, per Vojtko & Dujava
(2026): at each weekly rebalance, hold whichever of Gold/Bitcoin had the
higher X-week return, but only if that return is also positive (the
absolute-momentum gate) - otherwise go flat (cash, 0% return). An optional
volatility cap sizes the position down (never up) to keep annualized
volatility under a ceiling, using only the selected asset's own trailing
realized volatility as of the decision date (no lookahead). An optional
per-asset round-trip transaction cost is charged only when the HELD asset
actually changes (cash<->gold<->btc) - not on every weekly vol-cap resize -
scaled by that week's position weight, since you only pay cost on the
notional actually traded."""

import numpy as np
import pandas as pd


def simulate_dual_momentum(
    weekly: pd.DataFrame,
    lookback_weeks: int,
    vol_cap: float | None = None,
    vol_lookback_weeks: int = 12,
    switch_cost_bps: dict[str, float] | None = None,
) -> pd.DataFrame:
    weekly_ret = weekly[["gold", "btc"]].pct_change()
    mom = weekly[["gold", "btc"]].pct_change(lookback_weeks)

    long_btc = (mom["btc"] > mom["gold"]) & (mom["btc"] > 0)
    long_gold = (mom["gold"] > mom["btc"]) & (mom["gold"] > 0)
    position = pd.Series(np.where(long_btc, "btc", np.where(long_gold, "gold", "cash")), index=weekly.index)

    # Position decided using momentum as of week i is HELD over week i -> i+1;
    # the realized return therefore lands on row i+1 (weekly_ret.iloc[i+1] is
    # already "return from close i to close i+1"), so shift the decision forward.
    held_position = position.shift(1)
    chosen_ret = np.select(
        [held_position == "btc", held_position == "gold"],
        [weekly_ret["btc"], weekly_ret["gold"]],
        default=0.0,
    )
    strat_ret = pd.Series(chosen_ret, index=weekly.index)

    weight = pd.Series(1.0, index=weekly.index)
    if vol_cap is not None:
        gold_vol = weekly_ret["gold"].rolling(vol_lookback_weeks).std() * np.sqrt(52)
        btc_vol = weekly_ret["btc"].rolling(vol_lookback_weeks).std() * np.sqrt(52)
        selected_vol = np.select([position == "btc", position == "gold"], [btc_vol, gold_vol], default=np.nan)
        weight = np.clip(vol_cap / selected_vol, a_min=None, a_max=1.0)
        weight = pd.Series(weight, index=weekly.index).shift(1).fillna(0.0)
        strat_ret = strat_ret * weight

    if switch_cost_bps is not None:
        prev_held = held_position.shift(1)
        cost = pd.Series(0.0, index=weekly.index)
        for i in range(1, len(weekly)):
            old, new = prev_held.iloc[i], held_position.iloc[i]
            if old == new:
                continue
            leg_cost = 0.0
            if old in switch_cost_bps:
                leg_cost += switch_cost_bps[old] / 2
            if new in switch_cost_bps:
                leg_cost += switch_cost_bps[new] / 2
            cost.iloc[i] = leg_cost / 1e4 * weight.iloc[i]
        strat_ret = strat_ret - cost

    out = weekly.copy()
    out["position"] = position
    out["held_position"] = held_position
    out["weight"] = weight
    out["strategy_return"] = strat_ret
    return out
