"""3-timeframe REVERSAL cascade, from the user's own live-chart examples
(chat 2026-08-18): "im H4 Auftrend manipulieren wir zweimal über ein High,
im H1 machen wir zwei BOS, im M15 haben wir dann den Reversal-Entry über
dem High, was das letzte Low gemacht hat."

  1. H4 - EXHAUSTION: TWO sweep-and-reject events at the SAME (still-
     unbroken/unchanged) erl_high or erl_low within a window - a stronger
     signal than continuation.py's single-sweep HTF trigger. Establishes
     a FADE bias (double sweep at erl_high -> bearish fade; at erl_low ->
     bullish fade) and the opposing H4 level as target.
  2. H1 - CONFIRMATION: a DOUBLE BOS (mean_reversion.compute_double_bos_
     count >= 2) in the SAME direction as the H4 fade bias.
  3. M15 - ENTRY: sweep-and-reject of the H1 reference level (the swing
     that preceded the impulse the H1 double-BOS confirmed) - same
     mechanic as continuation.py's "direct" entry variant, just fading
     instead of following.

Hypothesis for why this should run cleanly, not just drift (chat
2026-08-18): each layer of REQUIRED confirmation (double sweep at H4,
double BOS at H1) filters out the low-quality, single-signal noise that
dominated mean_reversion.py's earlier single-confirmation attempt - this
only fires on genuinely, multiply-exhausted setups.

Optional confirmation layers, all off by default and independently
testable:
  - EMA touch/reject at H4 (reuses ema_strategy.indicators.double_ema -
    this repo's own already-built EMA S/R concept, chat 2026-08-18): the
    H4 exhaustion zone should also show a rejection off a smoothed EMA
    trigger line, not just the fractal swing level.
  - Real yield / COT sentiment (reuses gold_trend_pullback_atr.filters -
    generic post-hoc trade-level filters, not duplicated here).

TP: the opposing H4 liquidity level (literal price, same use_vwap_target
trick as continuation.py) or a flat ATR-multiple - both testable via the
caller's BacktestConfig, same as continuation.py.

IMPORTANT (same caller requirement as continuation.py): vwap/h4_target is
read fresh by simulate_trades at every open-trade bar, so cap trade
lifetime with BacktestConfig(max_hold_bars=...) to avoid the same
mid-trade target-drift bug found there.
"""

import numpy as np
import pandas as pd

from ema_strategy.indicators import double_ema
from gold_smc_htf_ltf.ema_ribbon import compute_ribbon, detect_ribbon_reversal_zone
from gold_smc_htf_ltf.mean_reversion import compute_double_bos_count
from gold_smc_htf_ltf.structure import compute_market_structure
from gold_smc_htf_ltf.trend import TREND_INDICATORS, trend_ema_cross
from gold_smc_htf_ltf.volume import compute_rolling_pressure_zscore
from strategy.indicators import compute_atr


def _level_age(level: pd.Series) -> np.ndarray:
    """Bars since `level` last changed value - a fresh vs. long-standing
    level."""
    level_np = level.to_numpy()
    n = len(level_np)
    age = np.zeros(n, dtype=int)
    cur_level, cur_age = np.nan, 0
    for i in range(n):
        if not np.isnan(level_np[i]) and level_np[i] != cur_level:
            cur_level, cur_age = level_np[i], 0
        else:
            cur_age += 1
        age[i] = cur_age
    return age


def _bar_length(index: pd.DatetimeIndex) -> pd.Timedelta:
    diffs = pd.Series(index[1:] - index[:-1])
    return diffs.mode().iloc[0]


def _sweep_and_reject(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    swept_low = (df["low"] < df["erl_low"]) & (df["close"] > df["erl_low"])
    swept_high = (df["high"] > df["erl_high"]) & (df["close"] < df["erl_high"])
    return swept_low, swept_high


def _merge_asof_shifted(base_index: pd.DatetimeIndex, series: pd.Series, shift: pd.Timedelta, col_name: str) -> np.ndarray:
    shifted = series.copy()
    shifted.index = (shifted.index + shift).as_unit("us")
    shifted = shifted.sort_index()
    left = pd.DataFrame(index=pd.DatetimeIndex(base_index).as_unit("us"))
    merged = pd.merge_asof(left, shifted.rename(col_name), left_index=True, right_index=True, direction="backward")
    return merged[col_name].to_numpy()


def detect_double_sweep(df: pd.DataFrame, confirm_bars: int = 50, level_tolerance_atr: float = 0.0, atr_n: int = 14) -> tuple[pd.Series, pd.Series]:
    """Two sweep-and-reject events at (approximately) the SAME erl_high/
    erl_low value within `confirm_bars` bars - tracked by level value, not
    just event count, so a sweep of a freshly-updated (meaningfully
    different) level never accidentally counts as the second sweep of an
    old one.

    `level_tolerance_atr` (chat 2026-08-19, "viel zu wenig Trades" - visual
    chart review showed far fewer setups than expected): 0.0 preserves the
    original exact-float-match behaviour (diagnosed as the single biggest
    bottleneck - only 59 of 381 H4 sweep-and-reject events over 2 years
    qualified). >0 treats the second sweep as "the same level" if it's
    within that many ATRs of the first, since a minor fresh fractal swing
    can nudge erl_high/erl_low by a few ticks without it being a genuinely
    different liquidity zone."""
    swept_low, swept_high = _sweep_and_reject(df)
    atr = compute_atr(df, n=atr_n).to_numpy() if level_tolerance_atr > 0 else None

    def _count_same_level(swept: pd.Series, level: pd.Series) -> pd.Series:
        swept_np, level_np = swept.to_numpy(), level.to_numpy()
        n = len(swept_np)
        count = np.zeros(n, dtype=int)
        cur_level, cur_count = np.nan, 0
        for i in range(n):
            if not np.isnan(level_np[i]):
                if np.isnan(cur_level):
                    cur_level = level_np[i]
                else:
                    tol = level_tolerance_atr * atr[i] if atr is not None and not np.isnan(atr[i]) else 0.0
                    if abs(level_np[i] - cur_level) > tol:
                        cur_level, cur_count = level_np[i], 0
            if swept_np[i]:
                cur_count += 1
            count[i] = cur_count
        return pd.Series(count, index=df.index)

    high_count = _count_same_level(swept_high, df["erl_high"])
    low_count = _count_same_level(swept_low, df["erl_low"])
    double_swept_low = (low_count >= 2).rolling(confirm_bars, min_periods=1).max().astype(bool)
    double_swept_high = (high_count >= 2).rolling(confirm_bars, min_periods=1).max().astype(bool)
    return double_swept_low, double_swept_high


def _trendline_break_signal(merged: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """m15_entry_mode="trendline" (chat 2026-08-19, "die Reversal Logik ist
    auch [dafuer da] um moeglichst hoch/tief in die Trendwende einzusteigen"
    - mirrors continuation.py's _trendline_break_signal, but for catching a
    REVERSAL as close to the actual high/low as possible instead of
    continuing an established trend. The OLD (about-to-reverse) trend's own
    internal structure is what gets tracked: h1_bias==1 (bullish fade,
    aiming to catch a LOW) tracks the old downtrend's own DESCENDING swing
    highs (lower highs on the way down) and fires LONG the moment price
    closes back above that diagonal - the earliest sign the down-push just
    exhausted, rather than waiting for a full sweep-and-reject. h1_bias==-1
    (bearish fade) is the mirror: tracks ASCENDING swing lows, fires SHORT
    on a break back below."""
    n = len(merged)
    close, high, low = merged["close"].to_numpy(), merged["high"].to_numpy(), merged["low"].to_numpy()
    swing_high_confirmed = merged["swing_high_confirmed"].to_numpy()
    swing_high_price = merged["swing_high_price"].to_numpy()
    swing_low_confirmed = merged["swing_low_confirmed"].to_numpy()
    swing_low_price = merged["swing_low_price"].to_numpy()
    h1_bias = merged["h1_bias"].to_numpy()

    entry_bull, entry_bear = np.zeros(n, dtype=bool), np.zeros(n, dtype=bool)
    stop_bull, stop_bear = np.full(n, np.nan), np.full(n, np.nan)

    prev_bias = 0
    sh1_i, sh1_p, sh2_i, sh2_p = -1, np.nan, -1, np.nan  # descending highs (bias==1 -> long on break up)
    sl1_i, sl1_p, sl2_i, sl2_p = -1, np.nan, -1, np.nan  # ascending lows (bias==-1 -> short on break down)
    fired_bull, fired_bear = False, False
    for i in range(n):
        if h1_bias[i] != prev_bias:
            sh1_i, sh1_p, sh2_i, sh2_p = -1, np.nan, -1, np.nan
            sl1_i, sl1_p, sl2_i, sl2_p = -1, np.nan, -1, np.nan
            fired_bull, fired_bear = False, False
            prev_bias = h1_bias[i]

        if h1_bias[i] == 1:
            if swing_high_confirmed[i]:
                if sh2_i == -1 or swing_high_price[i] < sh2_p:
                    sh1_i, sh1_p, sh2_i, sh2_p = sh2_i, sh2_p, i, swing_high_price[i]
                else:
                    sh1_i, sh1_p, sh2_i, sh2_p = -1, np.nan, i, swing_high_price[i]
                fired_bull = False
            if sh1_i != -1 and sh2_i != -1 and i > sh2_i and not fired_bull:
                slope = (sh2_p - sh1_p) / (sh2_i - sh1_i)
                trendline_val = sh2_p + slope * (i - sh2_i)
                if close[i] > trendline_val:
                    entry_bull[i], stop_bull[i], fired_bull = True, low[i], True
        elif h1_bias[i] == -1:
            if swing_low_confirmed[i]:
                if sl2_i == -1 or swing_low_price[i] > sl2_p:
                    sl1_i, sl1_p, sl2_i, sl2_p = sl2_i, sl2_p, i, swing_low_price[i]
                else:
                    sl1_i, sl1_p, sl2_i, sl2_p = -1, np.nan, i, swing_low_price[i]
                fired_bear = False
            if sl1_i != -1 and sl2_i != -1 and i > sl2_i and not fired_bear:
                slope = (sl2_p - sl1_p) / (sl2_i - sl1_i)
                trendline_val = sl2_p + slope * (i - sl2_i)
                if close[i] < trendline_val:
                    entry_bear[i], stop_bear[i], fired_bear = True, high[i], True

    idx = merged.index
    return pd.Series(entry_bull, index=idx), pd.Series(entry_bear, index=idx), pd.Series(stop_bull, index=idx), pd.Series(stop_bear, index=idx)


def compute_h4_exhaustion(
    h4_df: pd.DataFrame,
    k: int = 2,
    confirm_bars: int = 50,
    sweep_mode: str = "double",
    level_tolerance_atr: float = 0.0,
    require_ema_reject: bool = False,
    ema_length: int = 50,
    ema_smooth: int = 15,
    require_ribbon_stretch: bool = False,
    d1_df: pd.DataFrame | None = None,
    w1_df: pd.DataFrame | None = None,
    ribbon_extension_atr_min: float = 3.0,
    require_h4_trend_confirm: bool = False,
    trend_confirm_indicator: str = "ema_cross",
    trend_fast: int = 20,
    trend_slow: int = 50,
    require_magnitude: bool = False,
    magnitude_atr_min: float = 3.0,
    require_volume_exhaustion: bool = False,
    vol_exhaustion_zscore_max: float = 0.0,
    vol_sum_window: int = 15,
    vol_zscore_window: int = 100,
    require_level_age: bool = False,
    min_level_age_bars: int = 5,
) -> pd.DataFrame:
    """Phase 1: double-sweep exhaustion -> h4_fade_bias (1=fade-to-bullish
    after a double sweep of erl_high, -1=fade-to-bearish after erl_low) +
    h4_target (opposing, still-unbroken erl level).

    `require_ema_reject`: additionally requires the SAME bar's close to
    have rejected off a double-smoothed EMA (ema_strategy.indicators.
    double_ema, this repo's own EMA S/R trigger concept, chat 2026-08-18) -
    a bearish fade needs close < that EMA (price rejected back below a
    dynamic resistance), a bullish fade needs close > it.

    `require_ribbon_stretch`: additionally requires price to be stretched
    >= ribbon_extension_atr_min ATRs from the user's own MTF EMA ribbon
    (H4/D1/D1-slow/W1, see ema_ribbon.py, chat 2026-08-18) in the direction
    being faded - needs d1_df/w1_df.

    `require_h4_trend_confirm` (chat 2026-08-19, "EMA Crosses vor allem im
    H4"): additionally requires an EMA(trend_fast)/EMA(trend_slow) cross on
    H4 itself (trend.py's trend_ema_cross, reused as-is) to currently show
    the trend being faded actually existed - a double sweep of erl_high is
    only a credible bearish fade if H4 was genuinely trending UP into it
    (fast EMA > slow EMA), and symmetrically for erl_low.

    `sweep_mode` (chat 2026-08-19, "viel zu wenig Trades" - visual review
    found far fewer setups than expected): "double" (default) requires the
    TWO-sweep exhaustion pattern (optionally zone-tolerant via
    `level_tolerance_atr`, see detect_double_sweep). "single" drops the
    second-sweep requirement entirely - any sweep-and-reject of erl_high/
    erl_low is treated as exhaustion on its own, a weaker but far more
    frequent signal class, tested separately (not blended) so IS/OOS can
    show which actually carries the edge.

    Three more optional pre-filters (chat 2026-08-19, "wir brauchen noch
    einen Filter fur Highs/Lows die ein Reversal einleiten konnten") - each
    asks whether the swept erl_high/erl_low was ever a PLAUSIBLE reversal
    candidate in the first place, before the H1/M15 cascade even looks at
    it:
      `require_magnitude`: the current unbroken range (erl_high - erl_low)
        must be >= magnitude_atr_min ATRs - reject sweeps of a small,
        insignificant recent chop range.
      `require_volume_exhaustion`: reuses volume.py's signed-pressure
        z-score - a bearish fade needs WEAK buying pressure into the high
        (z-score <= vol_exhaustion_zscore_max, i.e. price made a new high
        without real demand behind it - divergence), symmetric for bullish
        fade / erl_low.
      `require_level_age`: the level must have stood unbroken for >=
        min_level_age_bars H4 bars before being swept - reject freshly-
        formed levels with no real history as liquidity."""
    h4 = compute_market_structure(h4_df, k=k)
    if sweep_mode == "double":
        double_swept_low, double_swept_high = detect_double_sweep(h4, confirm_bars=confirm_bars, level_tolerance_atr=level_tolerance_atr)
    elif sweep_mode == "single":
        swept_low, swept_high = _sweep_and_reject(h4)
        double_swept_low = swept_low.rolling(confirm_bars, min_periods=1).max().astype(bool)
        double_swept_high = swept_high.rolling(confirm_bars, min_periods=1).max().astype(bool)
    else:
        raise ValueError(f"sweep_mode must be 'double' or 'single', got {sweep_mode!r}")

    if require_ema_reject:
        ema = double_ema(h4["close"], length=ema_length, smooth=ema_smooth)
        double_swept_low = double_swept_low & (h4["close"] > ema)
        double_swept_high = double_swept_high & (h4["close"] < ema)

    if require_h4_trend_confirm:
        # trend_confirm_indicator (chat 2026-08-20, mirroring continuation.
        # py's own ema_adx_combo win): "ema_cross" (default, unchanged) is a
        # pure direction read - always picks a side. "ema_adx_combo" (trend.
        # py) additionally requires ADX strength, withholding an opinion (0)
        # in choppy H4 conditions instead of forcing a direction - tested
        # here since the SAME "selectivity, not direction" hypothesis that
        # improved continuation.py might also help this H4 confirmation gate.
        trend_fn = TREND_INDICATORS[trend_confirm_indicator]
        h4_trend = trend_fn(h4, fast=trend_fast, slow=trend_slow)
        # fading erl_high (bearish fade) needs a prior UPtrend; fading erl_low needs a prior DOWNtrend
        double_swept_high = double_swept_high & (h4_trend == 1)
        double_swept_low = double_swept_low & (h4_trend == -1)

    if require_ribbon_stretch:
        if d1_df is None or w1_df is None:
            raise ValueError("require_ribbon_stretch=True needs d1_df and w1_df")
        h4 = compute_ribbon(h4, d1_df, w1_df)
        stretched_up, stretched_down = detect_ribbon_reversal_zone(h4, extension_atr_min=ribbon_extension_atr_min)
        # fading a bullish exhaustion (double_swept_high, bearish bias) needs
        # price stretched UP from the ribbon; symmetric for double_swept_low
        double_swept_high = double_swept_high & stretched_up
        double_swept_low = double_swept_low & stretched_down

    if require_magnitude:
        atr_mag = compute_atr(h4, n=14)
        range_size = (h4["erl_high"] - h4["erl_low"]) / atr_mag
        big_enough = range_size >= magnitude_atr_min
        double_swept_low = double_swept_low & big_enough
        double_swept_high = double_swept_high & big_enough

    if require_volume_exhaustion:
        pressure_z = compute_rolling_pressure_zscore(h4, sum_window=vol_sum_window, zscore_window=vol_zscore_window)
        # bearish fade (sweep of erl_high) needs WEAK buying pressure into
        # the high (divergence); bullish fade (sweep of erl_low) needs weak
        # selling pressure into the low
        double_swept_high = double_swept_high & (pressure_z <= vol_exhaustion_zscore_max)
        double_swept_low = double_swept_low & (pressure_z >= -vol_exhaustion_zscore_max)

    if require_level_age:
        high_age = _level_age(h4["erl_high"])
        low_age = _level_age(h4["erl_low"])
        double_swept_high = double_swept_high & (high_age >= min_level_age_bars)
        double_swept_low = double_swept_low & (low_age >= min_level_age_bars)

    signal = np.where(double_swept_low, 1, np.where(double_swept_high, -1, 0))

    n = len(h4)
    erl_high, erl_low = h4["erl_high"].to_numpy(), h4["erl_low"].to_numpy()
    erl_high_broken, erl_low_broken = h4["erl_high_broken"].to_numpy(), h4["erl_low_broken"].to_numpy()

    h4_bias = np.zeros(n, dtype=int)
    h4_target = np.full(n, np.nan)
    cur_bias, cur_target, remaining = 0, np.nan, 0
    for i in range(n):
        if remaining > 0 and cur_bias != 0:
            # the fade thesis dies if the ORIGINAL trend resumes (a fresh
            # break in the pre-fade direction, i.e. the opposite of our bias)
            thesis_dead = (cur_bias == 1 and erl_low_broken[i]) or (cur_bias == -1 and erl_high_broken[i])
            if thesis_dead:
                remaining, cur_bias = 0, 0
        if signal[i] != 0:
            cur_bias = int(signal[i])
            cur_target = erl_high[i] if cur_bias == 1 else erl_low[i]
            remaining = confirm_bars
        if remaining > 0:
            h4_bias[i], h4_target[i] = cur_bias, cur_target
            remaining -= 1
        else:
            h4_bias[i], h4_target[i] = 0, np.nan
            cur_bias = 0

    h4["h4_fade_bias"] = h4_bias
    h4["h4_target"] = h4_target
    return h4


def _first_bos_level(h1: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """For each bar, the erl_low/erl_high value as of the FIRST is_bos
    event in the current same-direction streak (bos_count going 0->1),
    frozen and carried forward until the streak resets (bias flips /
    bos_count drops to 0) - not H1's live/latest erl_low/erl_high, which
    tracks whatever the newest unbroken swing is (chat 2026-08-19: "nochmal
    unter das erste Low/High bevor der Entry validiert wurde" - the
    double-BOS filter is only meaningful together with a subsequent
    inducement sweep of the level that started the whole move, not a
    recent minor pullback level)."""
    bos_count = h1["bos_count"].to_numpy()
    erl_low, erl_high = h1["erl_low"].to_numpy(), h1["erl_high"].to_numpy()
    n = len(h1)
    first_low = np.full(n, np.nan)
    first_high = np.full(n, np.nan)
    cur_low, cur_high, prev_count = np.nan, np.nan, 0
    for i in range(n):
        if bos_count[i] == 0:
            cur_low, cur_high = np.nan, np.nan
        elif prev_count == 0 and bos_count[i] == 1:
            cur_low, cur_high = erl_low[i], erl_high[i]
        first_low[i], first_high[i] = cur_low, cur_high
        prev_count = bos_count[i]
    return first_low, first_high


def compute_h1_context(h1_df: pd.DataFrame, h4_df: pd.DataFrame, k: int = 2, h4_confirm_bars: int = 50, h1_valid_bars: int = 24, h1_bos_min: int = 2, require_h1_inducement: bool = False, **h4_kwargs) -> pd.DataFrame:
    """Phase 2: H1 structure + a DOUBLE BOS in the SAME direction as the
    (merged-on) H4 fade bias -> h1_bias/h1_target/h1_ref_level.

    h1_bias/h1_ref_level (used only to gate a FRESH M15 entry) expire after
    h1_valid_bars, as before. h1_target is tracked SEPARATELY and does NOT
    share that countdown - it persists until the target is actually reached
    or the thesis is invalidated, with no arbitrary timeout. Diagnosed
    (chat 2026-08-19): simulate_trades re-reads vwap/h1_target fresh on
    every open-trade bar, so when the two were on one shared countdown, a
    trade entered late within the h1_valid_bars window could lose its
    target reference (h1_target -> NaN) long before the trade itself was
    anywhere near max_hold_bars - 8/10 max_hold exits in one OOS run had
    this happen, 4 of them in well under half the position's lifetime -
    leaving the trade coasting with no way to exit except stop/breakeven/
    max_hold for the rest of its life."""
    h1 = compute_market_structure(h1_df, k=k)
    h1["bos_count"] = compute_double_bos_count(h1)
    first_bos_low, first_bos_high = _first_bos_level(h1)

    h4 = compute_h4_exhaustion(h4_df, k=k, confirm_bars=h4_confirm_bars, **h4_kwargs)
    h4_shift = _bar_length(h4.index)
    h4_bias_on_h1 = _merge_asof_shifted(h1.index, h4["h4_fade_bias"], h4_shift, "h4_bias")
    h4_target_on_h1 = _merge_asof_shifted(h1.index, h4["h4_target"], h4_shift, "h4_target")
    h4_erl_high_broken_on_h1 = _merge_asof_shifted(h1.index, h4["erl_high_broken"], h4_shift, "hehb").astype(bool)
    h4_erl_low_broken_on_h1 = _merge_asof_shifted(h1.index, h4["erl_low_broken"], h4_shift, "helb").astype(bool)

    # h1_bos_min (chat 2026-08-19): the ">= 2" default is nearly always
    # true on its own (~78% of all H1 bars in a 2yr sample) - barely a
    # filter. Kept adjustable to test whether requiring MORE consecutive
    # BOS events (a stronger, rarer confirmation) does more useful work
    # than the H4 double-sweep side of the cascade.
    double_bos = h1["bos_count"].to_numpy() >= h1_bos_min
    bias_np = h1["bias"].to_numpy()
    inducement_ok = np.where(bias_np == 1, ~np.isnan(first_bos_low), ~np.isnan(first_bos_high)) if require_h1_inducement else np.ones(len(h1), dtype=bool)
    signal = np.where(double_bos & (bias_np == 1) & (h4_bias_on_h1 == 1) & inducement_ok, 1, np.where(double_bos & (bias_np == -1) & (h4_bias_on_h1 == -1) & inducement_ok, -1, 0))

    n = len(h1)
    h1_erl_high, h1_erl_low = h1["erl_high"].to_numpy(), h1["erl_low"].to_numpy()

    h1_bias = np.zeros(n, dtype=int)
    h1_target = np.full(n, np.nan)
    h1_ref_level = np.full(n, np.nan)
    cur_bias, cur_ref, remaining = 0, np.nan, 0  # entry-gating: expires after h1_valid_bars
    active_bias, active_target = 0, np.nan  # target-tracking: expires only on target-reached / thesis-dead
    for i in range(n):
        if active_bias != 0:
            target_reached = (active_bias == 1 and h4_erl_high_broken_on_h1[i]) or (active_bias == -1 and h4_erl_low_broken_on_h1[i])
            h4_context_gone = not np.isnan(h4_bias_on_h1[i]) and h4_bias_on_h1[i] != active_bias
            if target_reached or h4_context_gone:
                active_bias, active_target = 0, np.nan
        if remaining > 0 and cur_bias != 0:
            target_reached = (cur_bias == 1 and h4_erl_high_broken_on_h1[i]) or (cur_bias == -1 and h4_erl_low_broken_on_h1[i])
            h4_context_gone = not np.isnan(h4_bias_on_h1[i]) and h4_bias_on_h1[i] != cur_bias
            if target_reached or h4_context_gone:
                remaining, cur_bias = 0, 0
        if signal[i] != 0:
            cur_bias = int(signal[i])
            if require_h1_inducement:
                cur_ref = first_bos_low[i] if cur_bias == 1 else first_bos_high[i]
            else:
                cur_ref = h1_erl_low[i] if cur_bias == 1 else h1_erl_high[i]
            remaining = h1_valid_bars
            active_bias, active_target = cur_bias, h4_target_on_h1[i]
        if remaining > 0:
            h1_bias[i], h1_ref_level[i] = cur_bias, cur_ref
            remaining -= 1
        else:
            h1_bias[i], h1_ref_level[i] = 0, np.nan
            cur_bias = 0
        h1_target[i] = active_target if active_bias != 0 else np.nan

    h1["h1_bias"] = h1_bias
    h1["h1_target"] = h1_target
    h1["h1_ref_level"] = h1_ref_level
    return h1


def run_pipeline(
    h4_df: pd.DataFrame,
    h1_df: pd.DataFrame,
    m15_df: pd.DataFrame,
    k: int = 2,
    h4_confirm_bars: int = 50,
    h1_valid_bars: int = 24,
    h1_bos_min: int = 2,
    require_h1_inducement: bool = False,
    atr_n: int = 30,
    min_target_distance_atr: float = 1.0,
    sweep_mode: str = "double",
    level_tolerance_atr: float = 0.0,
    require_ema_reject: bool = False,
    ema_length: int = 50,
    ema_smooth: int = 15,
    require_ribbon_stretch: bool = False,
    d1_df: pd.DataFrame | None = None,
    w1_df: pd.DataFrame | None = None,
    ribbon_extension_atr_min: float = 3.0,
    require_h4_trend_confirm: bool = False,
    trend_confirm_indicator: str = "ema_cross",
    trend_fast: int = 20,
    trend_slow: int = 50,
    require_magnitude: bool = False,
    magnitude_atr_min: float = 3.0,
    require_volume_exhaustion: bool = False,
    vol_exhaustion_zscore_max: float = 0.0,
    vol_sum_window: int = 15,
    vol_zscore_window: int = 100,
    require_level_age: bool = False,
    min_level_age_bars: int = 5,
    m15_entry_mode: str = "sweep",
    m15_ema_fast: int = 12,
    m15_ema_slow: int = 26,
    m15_ema_length: int = 50,
    m15_ema_touch_atr: float = 0.3,
) -> pd.DataFrame:
    """`m15_entry_mode` (chat 2026-08-19, "wie sieht der neue EMA Filter als
    Entry Logik aus? Ein Cross oder Touch des Kurses an die EMA"):
    "sweep" (default, unchanged) - M15 sweep-and-reject of h1_ref_level.
    "ema_cross" - a genuine EMA(m15_ema_fast)/EMA(m15_ema_slow) crossover
    EVENT on M15 (not a state, unlike require_ema_reject/require_h4_trend_
    confirm elsewhere in this module), in the h1_bias direction. "ema_touch"
    - price reaches within m15_ema_touch_atr ATRs of a single EMA
    (m15_ema_length), a dynamic S/R retest. Both new modes use the
    triggering bar's own low/high as the stop reference (h1_ref_level is
    not part of the trigger in these modes, only h1_bias for direction)."""
    from strategy.indicators import compute_adx

    h1 = compute_h1_context(
        h1_df, h4_df, k=k, h4_confirm_bars=h4_confirm_bars, h1_valid_bars=h1_valid_bars, h1_bos_min=h1_bos_min, require_h1_inducement=require_h1_inducement,
        sweep_mode=sweep_mode, level_tolerance_atr=level_tolerance_atr,
        require_magnitude=require_magnitude, magnitude_atr_min=magnitude_atr_min,
        require_volume_exhaustion=require_volume_exhaustion, vol_exhaustion_zscore_max=vol_exhaustion_zscore_max, vol_sum_window=vol_sum_window, vol_zscore_window=vol_zscore_window,
        require_level_age=require_level_age, min_level_age_bars=min_level_age_bars,
        require_ema_reject=require_ema_reject, ema_length=ema_length, ema_smooth=ema_smooth,
        require_ribbon_stretch=require_ribbon_stretch, d1_df=d1_df, w1_df=w1_df, ribbon_extension_atr_min=ribbon_extension_atr_min,
        require_h4_trend_confirm=require_h4_trend_confirm, trend_confirm_indicator=trend_confirm_indicator, trend_fast=trend_fast, trend_slow=trend_slow,
    )
    h1_shifted = h1[["h1_bias", "h1_target", "h1_ref_level"]].copy()
    h1_shifted.index = h1_shifted.index + _bar_length(h1.index)

    m15 = compute_market_structure(m15_df, k=k).sort_index()
    m15 = compute_adx(m15, n=atr_n)

    m15.index = m15.index.as_unit("us")
    h1_shifted.index = h1_shifted.index.as_unit("us")
    h1_shifted = h1_shifted.sort_index()
    merged = pd.merge_asof(m15, h1_shifted, left_index=True, right_index=True, direction="backward")
    if not merged.index.equals(m15.index):
        merged.index = m15.index

    if m15_entry_mode == "sweep":
        entry_trigger_bull = (merged["h1_bias"] == 1) & (merged["low"] < merged["h1_ref_level"]) & (merged["close"] > merged["h1_ref_level"])
        entry_trigger_bear = (merged["h1_bias"] == -1) & (merged["high"] > merged["h1_ref_level"]) & (merged["close"] < merged["h1_ref_level"])
    elif m15_entry_mode == "ema_cross":
        ema_fast = merged["close"].ewm(span=m15_ema_fast, adjust=False).mean()
        ema_slow = merged["close"].ewm(span=m15_ema_slow, adjust=False).mean()
        cross_up = (ema_fast > ema_slow) & (ema_fast.shift(1) <= ema_slow.shift(1))
        cross_down = (ema_fast < ema_slow) & (ema_fast.shift(1) >= ema_slow.shift(1))
        entry_trigger_bull = (merged["h1_bias"] == 1) & cross_up
        entry_trigger_bear = (merged["h1_bias"] == -1) & cross_down
    elif m15_entry_mode == "ema_touch":
        ema = merged["close"].ewm(span=m15_ema_length, adjust=False).mean()
        entry_trigger_bull = (merged["h1_bias"] == 1) & ((merged["low"] - ema).abs() <= m15_ema_touch_atr * merged["atr"]) & (merged["close"] >= ema - m15_ema_touch_atr * merged["atr"])
        entry_trigger_bear = (merged["h1_bias"] == -1) & ((merged["high"] - ema).abs() <= m15_ema_touch_atr * merged["atr"]) & (merged["close"] <= ema + m15_ema_touch_atr * merged["atr"])
    elif m15_entry_mode == "trendline":
        entry_trigger_bull, entry_trigger_bear, _, _ = _trendline_break_signal(merged)
    elif m15_entry_mode == "repeat_sweep":
        # chat 2026-08-19: "Nur der LTF Entry um ein besseres CRV zu catchen
        # nutzt die 2x ueber den selben Punkt Logik" - like continuation.
        # py's repeat_sweep entry_variant: enter only on the SECOND M15
        # sweep-and-reject of the SAME h1_ref_level (constant for the
        # duration of one H1 context window), not the first - a tighter,
        # later entry closer to the level for a better risk/reward.
        sweep_bull = (merged["h1_bias"] == 1) & (merged["low"] < merged["h1_ref_level"]) & (merged["close"] > merged["h1_ref_level"])
        sweep_bear = (merged["h1_bias"] == -1) & (merged["high"] > merged["h1_ref_level"]) & (merged["close"] < merged["h1_ref_level"])

        def _count_repeats(swept: pd.Series, level: pd.Series) -> pd.Series:
            swept_np, level_np = swept.to_numpy(), level.to_numpy()
            count = np.zeros(len(swept_np), dtype=int)
            cur_level, cur_count = np.nan, 0
            for i in range(len(swept_np)):
                if not np.isnan(level_np[i]) and level_np[i] != cur_level:
                    cur_level, cur_count = level_np[i], 0
                if swept_np[i]:
                    cur_count += 1
                count[i] = cur_count
            return pd.Series(count, index=swept.index)

        entry_trigger_bull = _count_repeats(sweep_bull, merged["h1_ref_level"]) >= 2
        entry_trigger_bear = _count_repeats(sweep_bear, merged["h1_ref_level"]) >= 2
    else:
        raise ValueError(f"m15_entry_mode must be 'sweep', 'ema_cross', 'ema_touch', 'trendline' or 'repeat_sweep', got {m15_entry_mode!r}")

    target_ok_long = (merged["h1_target"] - merged["close"]) >= min_target_distance_atr * merged["atr"]
    target_ok_short = (merged["close"] - merged["h1_target"]) >= min_target_distance_atr * merged["atr"]

    entry_long = entry_trigger_bull & merged["h1_target"].notna() & target_ok_long
    entry_short = entry_trigger_bear & merged["h1_target"].notna() & target_ok_short

    merged["signal"] = np.where(entry_long, 1, np.where(entry_short, -1, 0))
    # BUGFIX (chat 2026-08-19): simulate_trades reads prev_low/prev_high at
    # entry_i = signal_bar + 1 (see strategy/backtest.py), but the trigger
    # conditions above (and therefore this sparse .where()) are only True
    # AT the signal bar itself. Without shift(1), the stop reference lands
    # one row too early and simulate_trades finds NaN there almost every
    # time - found via chart review: 62% of trades (26/42 OOS) had NaN
    # initial_risk, meaning no working stop-loss at all. Canonical
    # convention (strategy/indicators.py's session-based prev_high/prev_low)
    # is a DENSE column valid at every bar; this sparse one-bar version
    # needs the shift to land on the bar simulate_trades actually reads.
    merged["prev_low"] = merged["low"].where(entry_trigger_bull).shift(1)
    merged["prev_high"] = merged["high"].where(entry_trigger_bear).shift(1)
    merged["vwap"] = merged["h1_target"]
    merged["session"] = 0
    return merged
