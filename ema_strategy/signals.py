"""Signal generation on the trigger timeframe (default H4, e.g. also H12)."""

from ema_strategy.indicators import double_ema


def build_signals(h4, ema_length=50, ema_smooth=15,
                   min_rejection_atr: float = 0.0,
                   require_htf_slope: bool = False):
    """
    min_rejection_atr: 0.0 = any close beyond the EMA counts as a rejection.
        >0 additionally requires the close to come back at least
        `min_rejection_atr` * ATR(14) past the EMA -- filters out weak,
        marginal fake touches.
    require_htf_slope: False = only price vs. EMA decides bias. True
        additionally requires the weekly AND daily EMA to be sloped in the
        trade direction (no trade in flat/sideways regimes).
    """
    df = h4.copy()
    df["trigger_ema"] = double_ema(df["Close"], ema_length, ema_smooth)

    touched_from_above = (df["Low"] <= df["trigger_ema"]) & (df["Close"] > df["trigger_ema"])
    touched_from_below = (df["High"] >= df["trigger_ema"]) & (df["Close"] < df["trigger_ema"])

    if min_rejection_atr > 0:
        atr = (df["High"] - df["Low"]).rolling(14).mean()
        rejection_up = (df["Close"] - df["trigger_ema"]) >= min_rejection_atr * atr
        rejection_down = (df["trigger_ema"] - df["Close"]) >= min_rejection_atr * atr
        touched_from_above &= rejection_up
        touched_from_below &= rejection_down

    long_cond = (
        (df["weekly_bias"] == 1)
        & (df["daily_bias"] == 1)
        & touched_from_above
    )
    short_cond = (
        (df["weekly_bias"] == -1)
        & (df["daily_bias"] == -1)
        & touched_from_below
    )

    if require_htf_slope:
        long_cond &= (df["weekly_slope"] > 0) & (df["daily_slope"] > 0)
        short_cond &= (df["weekly_slope"] < 0) & (df["daily_slope"] < 0)

    df["signal"] = 0
    df.loc[long_cond, "signal"] = 1
    df.loc[short_cond, "signal"] = -1
    return df
