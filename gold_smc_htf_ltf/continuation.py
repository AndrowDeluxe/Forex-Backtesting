"""Continuation ("trade WITH the trend") strategy: H4 (invalidation) -> H1
(trend-filtered BOS = the qualifying continuation signal) -> M5 (entry, 2
variants) -> TP at the opposing H4 liquidity level or a flat ATR-multiple
(2 testable modes). Based on the user's mentor example set (chat
2026-08-14, "CTL Beispeil.pdf"): H4 BOS to the upside -> M5 inducement
zone -> entry, target the next external H4 range (near-11R in the
example).

Trend filter: "BOS ist der weitere Bruch eines Swing Highs/Lows in die
trendende Richtung" - an H1 structural break (is_bos, see structure.py)
only counts as a tradeable continuation signal if it agrees with an
independently-computed trend direction (trend.py), evaluated on whatever
timeframe is passed in as `trend_df` (the user's own suggestion: decouple
the trend gauge's timeframe, e.g. M15/M30, from the H4/H1 structure
timeframes - tested as a parameter here, not hardcoded).

M5 entry, "the swing that made the Higher-High/Lower-Low": at the moment
an H1 BOS confirms (say, bullish - a fresh higher high), h1_ref_level is
the LAST confirmed H1 swing low - the pullback origin that preceded and
enabled this impulsive leg (exactly what track_external_range_liquidity's
erl_low already tracks at that instant, so no extra bookkeeping needed).

  - Variant "direct": enter on the M5 sweep-and-reject of h1_ref_level
    (page 2 example: "M5 BOS und Entry über dem letzten High (Inducement)").
  - Variant "double": wait for a SECOND M5-level break after that sweep (an
    M5 BOS following the first M5 sweep), entering at the break of the M5
    swing that made THAT second M5 BOS (page 4 example: "Entry nach
    zweifachem M5 BOS über dem High, was den BOS gemacht hat (Early
    Ones)").

Invalidation: H4's own (untfiltered) structural bias flipping against the
trade direction - "Invalidiert wird unser Trade, wenn wir im H4 einen
weiteren Bruch des Trends eingeleitet haben."

IMPORTANT caller requirement (found via smoke test, chat 2026-08-14):
`vwap` (h1_target) is read FRESH by strategy.backtest.simulate_trades at
every bar of an open trade, not frozen at entry - if the H1 context
expires and a NEW, OPPOSING signal fires while an M5 trade from the OLD
context is still open, h1_target can jump to the wrong side for that open
trade, producing a spurious/nonsensical "target" exit. Since simulate_
trades is shared infrastructure used by many other strategies, this isn't
patched there - callers of this pipeline MUST cap trade lifetime with
BacktestConfig(max_hold_bars=...) set to roughly `htf_valid_bars` H1 bars
converted to M5 bars (x12), so a trade can't outlive the H1 context that
justified it.
"""

import numpy as np
import pandas as pd

from gold_smc_htf_ltf.mean_reversion import compute_double_bos_count
from gold_smc_htf_ltf.structure import compute_market_structure
from gold_smc_htf_ltf.trend import TREND_INDICATORS
from strategy.indicators import compute_adx


def _bar_length(index: pd.DatetimeIndex) -> pd.Timedelta:
    """Modal (most common) gap between consecutive bars - robust to
    occasional weekend/holiday gaps that a single index[i+1]-index[i]
    sample could land on."""
    diffs = pd.Series(index[1:] - index[:-1])
    return diffs.mode().iloc[0]


def _sweep_and_reject(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    swept_low = (df["low"] < df["erl_low"]) & (df["close"] > df["erl_low"])
    swept_high = (df["high"] > df["erl_high"]) & (df["close"] < df["erl_high"])
    return swept_low, swept_high


def _merge_asof_shifted(base_index: pd.DatetimeIndex, series: pd.Series, shift: pd.Timedelta, col_name: str) -> np.ndarray:
    """Shifts `series` forward by `shift` (only knowable once that bar has
    closed) and merge_asof's it (backward) onto `base_index` - the same
    no-lookahead HTF->LTF alignment used throughout gold_smc_htf_ltf."""
    shifted = series.copy()
    shifted.index = (shifted.index + shift).as_unit("us")
    shifted = shifted.sort_index()
    left = pd.DataFrame(index=pd.DatetimeIndex(base_index).as_unit("us"))
    merged = pd.merge_asof(left, shifted.rename(col_name), left_index=True, right_index=True, direction="backward")
    return merged[col_name].to_numpy()


def _trendline_break_signal(merged: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """entry_variant="trendline" (chat 2026-08-19, derived from the user's
    own TradingView chart examples: a basing range forms WITHIN an ongoing
    trend, bounded by an internal counter-trend diagonal connecting two
    swing points that get progressively more extreme (lower highs in a
    downtrend, higher lows in an uptrend - "E-$" in the user's annotations)
    - price closing back through that diagonal, in the ORIGINAL trend
    direction, is the entry ("von Trendline zur Trendline", the LTF mirror
    of the H4-level "trade from liquidity to liquidity" target logic
    already used for TP here).

    Tracks, per bar and while h1_bias stays constant, the two most recent
    M5 swing highs (bearish continuation, h1_bias==-1) or swing lows
    (bullish, h1_bias==1) that are still moving WITH the trend (each new
    one more extreme than the last - a genuine counter-trend structure,
    not just any two swings). A straight line through those two points is
    extrapolated forward bar by bar; the first bar close crosses back
    through it (in the continuation direction) fires the entry, using that
    bar's own high/low as the stop reference. The swing pair resets
    whenever h1_bias changes, or whenever a new swing arrives that ISN'T
    more extreme (the "descending highs" premise just broke - no valid
    line anymore until a fresh pair forms)."""
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
    sh1_i, sh1_p, sh2_i, sh2_p = -1, np.nan, -1, np.nan
    sl1_i, sl1_p, sl2_i, sl2_p = -1, np.nan, -1, np.nan
    fired_bear, fired_bull = False, False
    for i in range(n):
        if h1_bias[i] != prev_bias:
            sh1_i, sh1_p, sh2_i, sh2_p = -1, np.nan, -1, np.nan
            sl1_i, sl1_p, sl2_i, sl2_p = -1, np.nan, -1, np.nan
            fired_bear, fired_bull = False, False
            prev_bias = h1_bias[i]

        if h1_bias[i] == -1:
            if swing_high_confirmed[i]:
                if sh2_i == -1 or swing_high_price[i] < sh2_p:
                    sh1_i, sh1_p, sh2_i, sh2_p = sh2_i, sh2_p, i, swing_high_price[i]
                else:
                    sh1_i, sh1_p, sh2_i, sh2_p = -1, np.nan, i, swing_high_price[i]
                fired_bear = False
            if sh1_i != -1 and sh2_i != -1 and i > sh2_i and not fired_bear:
                slope = (sh2_p - sh1_p) / (sh2_i - sh1_i)
                trendline_val = sh2_p + slope * (i - sh2_i)
                if close[i] < trendline_val:
                    entry_bear[i], stop_bear[i], fired_bear = True, high[i], True
        elif h1_bias[i] == 1:
            if swing_low_confirmed[i]:
                if sl2_i == -1 or swing_low_price[i] > sl2_p:
                    sl1_i, sl1_p, sl2_i, sl2_p = sl2_i, sl2_p, i, swing_low_price[i]
                else:
                    sl1_i, sl1_p, sl2_i, sl2_p = -1, np.nan, i, swing_low_price[i]
                fired_bull = False
            if sl1_i != -1 and sl2_i != -1 and i > sl2_i and not fired_bull:
                slope = (sl2_p - sl1_p) / (sl2_i - sl1_i)
                trendline_val = sl2_p + slope * (i - sl2_i)
                if close[i] > trendline_val:
                    entry_bull[i], stop_bull[i], fired_bull = True, low[i], True

    idx = merged.index
    return pd.Series(entry_bull, index=idx), pd.Series(entry_bear, index=idx), pd.Series(stop_bull, index=idx), pd.Series(stop_bear, index=idx)


def compute_h1_context(
    h1_df: pd.DataFrame,
    h4_df: pd.DataFrame,
    trend_df: pd.DataFrame,
    trend_indicator: str = "ema_cross",
    trend_kwargs: dict | None = None,
    k: int = 2,
    htf_valid_bars: int = 24,
    h1_bos_min: int = 1,
    require_h4_manipulation: bool = False,
    h4_manip_confirm_bars: int = 20,
) -> pd.DataFrame:
    """H1-level structure + trend-aligned BOS -> h1_bias/h1_target/
    h1_ref_level, expiring either when the target is reached or when H4's
    own structural bias flips against the trade direction (invalidation).

    h1_target is the H4 (not H1!) opposing external-liquidity level - "TP
    ist entweder H4 Swing High/Low" (chat 2026-08-14). The H1 break that
    triggers the signal consumes the H1-level erl boundary (it's the level
    JUST broken, now behind price), so it cannot double as a forward
    target - the real, still-unreached target one level up is H4's own
    (still-unbroken) erl_high/erl_low, carried onto the H1 index the same
    no-lookahead way h4_bias already is.

    `require_h4_manipulation` (chat 2026-08-20, from the user's own real
    trade chart: "Entry durch H4 Manipulation bestaetigt im H4" - a
    formal H4-level confirmation step that was missing here, unlike
    reversal_cascade.py's H4 exhaustion phase): additionally requires a
    RECENT (within h4_manip_confirm_bars) H4 sweep-and-reject in the
    SAME direction as the trend being continued - a bullish continuation
    needs a sweep-and-reject of H4's erl_low (a stop-hunt shakeout below
    support, liquidity grabbed, then rejected back up before resuming the
    uptrend), a bearish one needs erl_high swept the same way. Mirrors
    reversal_cascade's sweep mechanic exactly, just read as confirmation
    of the EXISTING trend instead of a fade trigger."""
    trend_kwargs = trend_kwargs or {}
    h1 = compute_market_structure(h1_df, k=k).sort_index()

    trend_fn = TREND_INDICATORS[trend_indicator]
    trend_series = trend_fn(trend_df, **trend_kwargs)
    ext_trend = _merge_asof_shifted(h1.index, trend_series, _bar_length(trend_df.index), "ext_trend")

    h4 = compute_market_structure(h4_df, k=k).sort_index()
    h4_shift = _bar_length(h4.index)
    h4_bias_on_h1 = _merge_asof_shifted(h1.index, h4["bias"], h4_shift, "h4_bias")
    h4_erl_high_on_h1 = _merge_asof_shifted(h1.index, h4["erl_high"], h4_shift, "h4_erl_high")
    h4_erl_low_on_h1 = _merge_asof_shifted(h1.index, h4["erl_low"], h4_shift, "h4_erl_low")
    h4_erl_high_broken_on_h1 = _merge_asof_shifted(h1.index, h4["erl_high_broken"], h4_shift, "h4_ehb").astype(bool)
    h4_erl_low_broken_on_h1 = _merge_asof_shifted(h1.index, h4["erl_low_broken"], h4_shift, "h4_elb").astype(bool)

    # h1_bos_min (chat 2026-08-19, mirroring reversal_cascade.py's own
    # h1_bos_min investigation): default 1 preserves the original single-
    # BOS behaviour exactly (bos_count is already >=1 at the instant
    # is_bos fires); >1 additionally requires this to be at least the
    # Nth consecutive same-direction BOS since the last CHoCH - a
    # stronger, rarer continuation confirmation.
    h1["bos_count"] = compute_double_bos_count(h1)
    is_bos_aligned = h1["is_bos"].to_numpy() & (h1["bias"].to_numpy() == ext_trend) & (h1["bos_count"].to_numpy() >= h1_bos_min)

    if require_h4_manipulation:
        swept_low_h4, swept_high_h4 = _sweep_and_reject(h4)
        recent_swept_low_h4 = swept_low_h4.rolling(h4_manip_confirm_bars, min_periods=1).max().astype(bool)
        recent_swept_high_h4 = swept_high_h4.rolling(h4_manip_confirm_bars, min_periods=1).max().astype(bool)
        h4_manip_bull_on_h1 = _merge_asof_shifted(h1.index, recent_swept_low_h4, h4_shift, "h4mb").astype(bool)
        h4_manip_bear_on_h1 = _merge_asof_shifted(h1.index, recent_swept_high_h4, h4_shift, "h4ms").astype(bool)
        bias_np_pre = h1["bias"].to_numpy()
        manip_ok = np.where(bias_np_pre == 1, h4_manip_bull_on_h1, np.where(bias_np_pre == -1, h4_manip_bear_on_h1, False))
        is_bos_aligned = is_bos_aligned & manip_ok
    bias_np = h1["bias"].to_numpy()
    signal = np.where(is_bos_aligned & (bias_np == 1), 1, np.where(is_bos_aligned & (bias_np == -1), -1, 0))

    n = len(h1)
    h1_erl_high, h1_erl_low = h1["erl_high"].to_numpy(), h1["erl_low"].to_numpy()

    h1_bias = np.zeros(n, dtype=int)
    h1_target = np.full(n, np.nan)
    h1_ref_level = np.full(n, np.nan)
    cur_bias, cur_target, cur_ref, remaining = 0, np.nan, np.nan, 0
    for i in range(n):
        if remaining > 0 and cur_bias != 0:
            target_reached = (cur_bias == 1 and h4_erl_high_broken_on_h1[i]) or (cur_bias == -1 and h4_erl_low_broken_on_h1[i])
            h4_invalidated = not np.isnan(h4_bias_on_h1[i]) and h4_bias_on_h1[i] != 0 and h4_bias_on_h1[i] == -cur_bias
            if target_reached or h4_invalidated:
                remaining = 0
                cur_bias = 0
        if signal[i] != 0:
            cur_bias = int(signal[i])
            cur_target = h4_erl_high_on_h1[i] if cur_bias == 1 else h4_erl_low_on_h1[i]
            cur_ref = h1_erl_low[i] if cur_bias == 1 else h1_erl_high[i]
            remaining = htf_valid_bars
        if remaining > 0:
            h1_bias[i], h1_target[i], h1_ref_level[i] = cur_bias, cur_target, cur_ref
            remaining -= 1
        else:
            h1_bias[i], h1_target[i], h1_ref_level[i] = 0, np.nan, np.nan
            cur_bias = 0

    h1["h1_bias"] = h1_bias
    h1["h1_target"] = h1_target
    h1["h1_ref_level"] = h1_ref_level
    return h1


def run_pipeline(
    h4_df: pd.DataFrame,
    h1_df: pd.DataFrame,
    m5_df: pd.DataFrame,
    trend_df: pd.DataFrame,
    trend_indicator: str = "ema_cross",
    trend_kwargs: dict | None = None,
    k: int = 2,
    htf_valid_bars: int = 24,
    h1_bos_min: int = 1,
    require_h4_manipulation: bool = False,
    h4_manip_confirm_bars: int = 20,
    entry_variant: str = "direct",
    m5_confirm_bars: int = 20,
    atr_n: int = 30,
    min_target_distance_atr: float = 1.0,
    zone_atr: float = 0.3,
) -> pd.DataFrame:
    """entry_variant: "direct" (M5 sweep-and-reject of h1_ref_level),
    "double" (wait for a second M5 break/BOS after that sweep, enter at
    the swing that made it), "zone" (chat 2026-08-19: "der Spike in die
    Zone reicht" - price only needs to reach within zone_atr ATRs of
    h1_ref_level, no full wick-beyond-and-close-back-inside required - a
    looser trigger than "direct"), or "repeat_sweep" (chat 2026-08-19:
    "nochmal unter/uber den Liq Spike im LTF" - like reversal_cascade's
    double-sweep idea, but applied to Continuation's own M5 entry: enter
    only on the SECOND sweep-and-reject of the same h1_ref_level, not the
    first), or "trendline" (chat 2026-08-19, derived from the user's own
    chart examples: a basing range within the trend bounded by an internal
    counter-trend diagonal through 2 swing points - "E-$" - entry on close
    breaking back through that diagonal in the trend direction; see
    _trendline_break_signal). TP mode (h4_level vs. flat ATR) and stop mode
    are chosen entirely via the BacktestConfig passed to simulate_trades
    downstream (vwap=h1_target always set for the h4_level/use_vwap_target
    option; prev_low/prev_high always set to the swept M5 reference for
    the stop_atr_mult option) - both are just different BacktestConfig
    choices on the SAME signal, not different pipelines."""
    if entry_variant not in ("direct", "double", "zone", "repeat_sweep", "trendline"):
        raise ValueError(f"entry_variant must be 'direct', 'double', 'zone', 'repeat_sweep' or 'trendline', got {entry_variant!r}")

    h1 = compute_h1_context(h1_df, h4_df, trend_df, trend_indicator, trend_kwargs, k=k, htf_valid_bars=htf_valid_bars, h1_bos_min=h1_bos_min, require_h4_manipulation=require_h4_manipulation, h4_manip_confirm_bars=h4_manip_confirm_bars)
    h1_shifted = h1[["h1_bias", "h1_target", "h1_ref_level"]].copy()
    h1_shifted.index = h1_shifted.index + _bar_length(h1.index)

    m5 = compute_market_structure(m5_df, k=k).sort_index()
    m5 = compute_adx(m5, n=atr_n)

    m5.index = m5.index.as_unit("us")
    h1_shifted.index = h1_shifted.index.as_unit("us")
    h1_shifted = h1_shifted.sort_index()
    merged = pd.merge_asof(m5, h1_shifted, left_index=True, right_index=True, direction="backward")
    if not merged.index.equals(m5.index):
        merged.index = m5.index

    # M5 sweep-and-reject of the H1 reference level (bullish context sweeps
    # h1_ref_level as a LOW, bearish context sweeps it as a HIGH)
    swept_ref_bull = (merged["h1_bias"] == 1) & (merged["low"] < merged["h1_ref_level"]) & (merged["close"] > merged["h1_ref_level"])
    swept_ref_bear = (merged["h1_bias"] == -1) & (merged["high"] > merged["h1_ref_level"]) & (merged["close"] < merged["h1_ref_level"])
    merged["m5_swept_ref_level"] = np.where(swept_ref_bull, merged["low"], np.where(swept_ref_bear, merged["high"], np.nan))

    if entry_variant == "direct":
        entry_long = swept_ref_bull
        entry_short = swept_ref_bear
        stop_level_long = merged["m5_swept_ref_level"].where(swept_ref_bull)
        stop_level_short = merged["m5_swept_ref_level"].where(swept_ref_bear)
    elif entry_variant == "double":
        # after the M5 sweep of h1_ref_level, wait for a SECOND M5-level
        # break (m5's own is_bos, in the same direction) within
        # m5_confirm_bars, then enter at the M5 swing that made it (m5's
        # own erl_low/erl_high at that moment - same "swing that made the
        # BOS" logic as h1_ref_level, one timeframe down).
        swept_ref_bull_recent = swept_ref_bull.rolling(m5_confirm_bars, min_periods=1).max().astype(bool)
        swept_ref_bear_recent = swept_ref_bear.rolling(m5_confirm_bars, min_periods=1).max().astype(bool)
        m5_bos_bull = merged["is_bos"] & (merged["bias"] == 1)
        m5_bos_bear = merged["is_bos"] & (merged["bias"] == -1)

        entry_long = swept_ref_bull_recent & m5_bos_bull & (merged["h1_bias"] == 1)
        entry_short = swept_ref_bear_recent & m5_bos_bear & (merged["h1_bias"] == -1)
        stop_level_long = merged["erl_low"].where(entry_long)
        stop_level_short = merged["erl_high"].where(entry_short)
    elif entry_variant == "zone":
        # looser than "direct": price only needs to spike WITHIN zone_atr
        # ATRs of h1_ref_level, not fully wick beyond it and close back -
        # a "close enough" retest instead of a literal sweep-and-reject.
        entry_long = (merged["h1_bias"] == 1) & ((merged["low"] - merged["h1_ref_level"]).abs() <= zone_atr * merged["atr"]) & (merged["close"] >= merged["h1_ref_level"] - zone_atr * merged["atr"])
        entry_short = (merged["h1_bias"] == -1) & ((merged["high"] - merged["h1_ref_level"]).abs() <= zone_atr * merged["atr"]) & (merged["close"] <= merged["h1_ref_level"] + zone_atr * merged["atr"])
        stop_level_long = merged["low"].where(entry_long)
        stop_level_short = merged["high"].where(entry_short)
    elif entry_variant == "repeat_sweep":
        # like "direct", but only on the SECOND sweep-and-reject of the
        # SAME h1_ref_level (h1_ref_level is constant for the duration of
        # one H1 context window, so consecutive sweeps of it are directly
        # comparable) - the first sweep is treated as the inducement, entry
        # comes on the repeat.
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

        entry_long = _count_repeats(swept_ref_bull, merged["h1_ref_level"]) >= 2
        entry_short = _count_repeats(swept_ref_bear, merged["h1_ref_level"]) >= 2
        stop_level_long = merged["m5_swept_ref_level"].where(entry_long)
        stop_level_short = merged["m5_swept_ref_level"].where(entry_short)
    else:  # "trendline"
        entry_long, entry_short, stop_level_long, stop_level_short = _trendline_break_signal(merged)

    # H4's own structure confirms with a k-bar lag, so right after a fresh
    # H1 break the "opposing" H4 erl level can still be STALE - on the
    # wrong side of current price (H4 hasn't caught up yet). A target
    # behind price isn't a real target ("no eng. LIQ in target = no A+
    # Setup") - require it to be genuinely ahead, by at least
    # min_target_distance_atr ATRs (chat 2026-08-14 fix, same principle as
    # gold_smc_htf_ltf.pipeline's identical guard).
    target_ok_long = (merged["h1_target"] - merged["close"]) >= min_target_distance_atr * merged["atr"]
    target_ok_short = (merged["close"] - merged["h1_target"]) >= min_target_distance_atr * merged["atr"]

    entry_long = entry_long & merged["h1_target"].notna() & target_ok_long
    entry_short = entry_short & merged["h1_target"].notna() & target_ok_short

    merged["signal"] = np.where(entry_long, 1, np.where(entry_short, -1, 0))
    # BUGFIX (chat 2026-08-19, found via reversal_cascade.py chart review):
    # simulate_trades reads prev_low/prev_high at entry_i = signal_bar + 1,
    # but stop_level_long/short are sparse - only non-NaN AT the signal bar
    # itself. Without shift(1) the lookup misses almost every time: 65% of
    # OOS trades (17/26) had NaN initial_risk, i.e. no working stop-loss.
    merged["prev_low"] = stop_level_long.shift(1)
    merged["prev_high"] = stop_level_short.shift(1)
    merged["vwap"] = merged["h1_target"]
    merged["session"] = 0
    return merged
