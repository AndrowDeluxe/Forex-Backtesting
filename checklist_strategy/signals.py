"""3-stage checklist state machine.

Stage 1 (armed): close breaks the NW-envelope upper band (-> short bias) or
lower band (-> long bias). Re-touching the *same* direction's band refreshes
the expiry clock without changing stage. A breakout in the *opposite*
direction overrides the current bias and restarts at stage 1, regardless of
how far the previous chain had progressed.

Stage 2 (confirmed): while armed, the RSI-Multi-Length average crosses/holds
beyond 70 (short bias) or 30 (long bias, symmetric).

Entry trigger: while confirmed, RSI(14) was above 70 (short) / below 30
(long) on the previous bar and crosses its own SMA(14) on this bar -
executes at the *next* bar's open (execution-lag convention, consistent
with strategy/backtest.py: the signal is only knowable at this bar's close).

Each completed chain immediately resets to "no bias" - independent chains
(and therefore overlapping trades) can form again right away, per the
strategy's own rules (no single-position restriction here).
"""

import numpy as np
import pandas as pd


def generate_checklist_signals(
    df: pd.DataFrame,
    confirm1_expiry_bars: int = 8,
    confirm2_expiry_bars: int = 8,
    rsi2_overbought: float = 70.0,
    rsi2_oversold: float = 30.0,
    rsi3_overbought: float = 70.0,
    rsi3_oversold: float = 30.0,
    require_regime_ok: bool = False,
) -> pd.DataFrame:
    """`df` must already have columns: close, env_upper, env_lower,
    avg_rsi (RSI Multi-Length), rsi, rsi_ma (RSI(14) + its SMA(14)), and,
    if `require_regime_ok=True`, a boolean `regime_ok` column (see
    `checklist_strategy.indicators.compute_regime_ok`).

    `require_regime_ok` gates only the final entry trigger, not the earlier
    stages: a checklist chain that completes while the regime filter says
    "no" still resolves (resets to no-bias) rather than firing - the RSI/MA
    cross is a point-in-time event, so there is nothing to usefully wait for.
    """
    close = df["close"].to_numpy()
    env_upper = df["env_upper"].to_numpy()
    env_lower = df["env_lower"].to_numpy()
    avg_rsi = df["avg_rsi"].to_numpy()
    rsi = df["rsi"].to_numpy()
    rsi_ma = df["rsi_ma"].to_numpy()
    regime_ok = df["regime_ok"].to_numpy() if require_regime_ok else None
    n = len(df)

    signal = np.zeros(n, dtype=int)
    bias = 0
    stage = 0
    stage_bar = -1

    for t in range(1, n):
        if np.isnan(env_upper[t]) or np.isnan(avg_rsi[t]) or np.isnan(rsi[t]) or np.isnan(rsi_ma[t]):
            continue

        if stage == 1 and (t - stage_bar) > confirm1_expiry_bars:
            stage, bias = 0, 0
        elif stage == 2 and (t - stage_bar) > confirm2_expiry_bars:
            stage, bias = 0, 0

        new_dir = -1 if close[t] > env_upper[t] else (1 if close[t] < env_lower[t] else 0)
        if new_dir != 0:
            if bias == 0 or new_dir != bias:
                bias, stage, stage_bar = new_dir, 1, t
            else:
                stage_bar = t

        if stage == 1:
            if bias == -1 and avg_rsi[t] > rsi2_overbought:
                stage, stage_bar = 2, t
            elif bias == 1 and avg_rsi[t] < rsi2_oversold:
                stage, stage_bar = 2, t

        if stage == 2:
            regime_pass = (not require_regime_ok) or bool(regime_ok[t])
            if (
                bias == -1
                and rsi[t - 1] > rsi_ma[t - 1]
                and rsi[t] <= rsi_ma[t]
                and rsi[t - 1] > rsi3_overbought
            ):
                if regime_pass:
                    signal[t] = -1
                stage, bias = 0, 0
            elif (
                bias == 1
                and rsi[t - 1] < rsi_ma[t - 1]
                and rsi[t] >= rsi_ma[t]
                and rsi[t - 1] < rsi3_oversold
            ):
                if regime_pass:
                    signal[t] = 1
                stage, bias = 0, 0

    out = df.copy()
    out["signal"] = signal
    return out
