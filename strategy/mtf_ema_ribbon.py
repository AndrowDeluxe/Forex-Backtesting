"""Multi-timeframe EMA ribbon trend filter.

Ported from a user-supplied TradingView Pine Script v6 indicator ("Custom
MTF EMA Ribbon"): four EMAs computed on higher timeframes than the base
chart (default 4H-50, 1D-50, 1W-50, 1D-200) via
`request.security(..., lookahead=barmerge.lookahead_off)`, i.e. each HTF
EMA only updates once its own bar has closed. Reproduced here with the
same no-lookahead `merge_asof(..., direction="backward")` pattern already
used in `ema_strategy.data.attach_htf_bias`, generalised to an arbitrary
list of (label, timeframe, length) levels instead of a single one.

The Pine script itself only plots the four lines. `ribbon_bias` and
`apply_mtf_ribbon_filter` turn that into a directional filter (long only
while price closes above the entire stack, short only while it closes
below the entire stack) -- an interpretation added here, not present in
the source script. Like the Kalman-filter/FX-liquidity Bausteine, this is
an independent, uncalibrated building block: no backtest result is
claimed until it has been run against a concrete strategy.
"""

import pandas as pd

DEFAULT_LEVELS = [
    ("ema_4h_50", "4h", 50),
    ("ema_1d_50", "1D", 50),
    ("ema_1w_50", "1W", 50),
    ("ema_1d_200", "1D", 200),
]


def resample_close(close: pd.Series, rule: str) -> pd.Series:
    """Last traded price per HTF bar (right-closed/right-labelled, i.e. the
    label timestamp is the bar's close time)."""
    return close.resample(rule, label="right", closed="right").last().dropna()


def htf_ema(close: pd.Series, rule: str, length: int) -> pd.Series:
    """EMA of `length` bars computed on `close` resampled to `rule`."""
    return resample_close(close, rule).ewm(span=length, adjust=False).mean()


def attach_mtf_ema_ribbon(
    df: pd.DataFrame,
    levels: list[tuple[str, str, int]] = DEFAULT_LEVELS,
    price_col: str = "close",
) -> pd.DataFrame:
    """No-lookahead merge of each (label, timeframe, length) HTF EMA onto
    `df`'s own (base/chart) timeframe -- one column per level, named after
    its label. Only a fully closed HTF bar's EMA value is visible to any
    given base-timeframe row (merge_asof, direction="backward"), matching
    how `barmerge.lookahead_off` behaves in the source Pine script."""
    out = df.copy()
    ts_col = out.index.name or "index"
    base = out.reset_index().rename(columns={ts_col: "_ts"})

    for label, rule, length in levels:
        ema = htf_ema(df[price_col], rule, length).rename(label).reset_index()
        ema.columns = ["_ts", label]
        base = pd.merge_asof(
            base.sort_values("_ts"), ema.sort_values("_ts"),
            on="_ts", direction="backward", allow_exact_matches=True,
        )

    return base.set_index("_ts").rename_axis(ts_col)


def ribbon_bias(
    df: pd.DataFrame,
    price_col: str = "close",
    levels: list[tuple[str, str, int]] = DEFAULT_LEVELS,
) -> pd.Series:
    """+1 where price closes above every ribbon EMA (bullish stack), -1
    where it closes below every one (bearish stack), 0 otherwise -- either
    the lines disagree (no directional bias) or a level's HTF history
    hasn't started yet. Always 0/-1/1 (never NaN), so it can be combined
    directly with a position series without an extra dropna/fillna step."""
    cols = [label for label, _, _ in levels]
    price = df[price_col]
    has_data = df[cols].notna().all(axis=1)
    above_all = pd.concat([price > df[c] for c in cols], axis=1).all(axis=1)
    below_all = pd.concat([price < df[c] for c in cols], axis=1).all(axis=1)

    bias = pd.Series(0, index=df.index)
    bias[has_data & above_all] = 1
    bias[has_data & below_all] = -1
    return bias


def apply_mtf_ribbon_filter(position: pd.Series, bias: pd.Series) -> pd.Series:
    """Zeros out any position that contradicts the ribbon bias (long while
    bias is -1/0, short while bias is +1/0) -- keeps only trades aligned
    with the full HTF EMA stack. Same convention as
    `triple_ma_strategy.filters.apply_regime_filter`: acts on a position
    series (-1/0/1), not on already-closed trades."""
    aligned = ((position > 0) & (bias > 0)) | ((position < 0) & (bias < 0))
    return position.where(aligned, 0)
