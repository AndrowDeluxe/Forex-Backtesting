"""Generalised, pair-specific currency-strength confirmation - extends
strategy.cls_advanced.compute_cross_confirmation (which only ever measured
"USD strength", hard-coded via _USD_IS_QUOTE, and therefore couldn't even
conceptually apply to a pair with no USD leg like EUR/JPY) to ANY pair.

User's own framing (2026-08-18, relaying the mentor's parallel cross-check
for the non-EUR/USD majors): "bei 2/4 Crosses mit aehnlicher Staerke gruenes
Licht, bei 4/4 erhoehen wir das Risiko" - plus a later refinement, "je mehr
Abstand zwischen den Indizes (mehr Staerke gegen Schwaeche), desto mehr
Risiko". Two deliberate design choices made explicit here rather than
guessing silently:
  1. "Pair-specific" basket (user's explicit choice over a fixed basket
     shared by all pairs): for XXX/YYY, only reference crosses that contain
     XXX or YYY count, not an unrelated currency's crosses.
  2. The discrete "X/4"-style count is kept (n_confirm/n_total) alongside a
     continuous strength_gap measure, so BOTH the graduated (2/4 vs 4/4) and
     the continuous (scale with distance) ideas can be built on the same
     output without re-deriving it twice.

Mechanism: for each of the two currencies in the traded pair, average the
sign-adjusted 06:00-09:00 move (see strategy.cls_advanced.compute_daily_
features) across every *other* available reference pair containing that
currency -> "how is this currency doing broadly, not just against its
counterpart in the traded pair". The traded pair's own break is confirmed
if the base currency is broadly strengthening while the quote currency is
broadly weakening (or the reverse, for a down-break) - the direct analogue
of the existing EUR/USD-vs-other-5-majors check, generalised to two
currencies instead of one.

EMPIRICAL RESULT (2026-08-18, scripts/research_cls_practical_pair_specific_cross.py):
this first version (06:00-09:00 settle-window, equal-weighted, >=50%
majority threshold) made results WORSE on all four re-tested instruments
(EUR/JPY, USD/CAD, AUD/USD, Gold) vs. the prior baseline - avg R per trade
went negative on every one, confounded with a simultaneous realistic-spread
change so the two effects aren't cleanly separated, but directionally
consistent with the (methodologically flawed) sanity check further down
this module's history: high confirm_ratio did NOT predict better outcomes.
NOT dropped, but NOT the recommended mechanism either - see
compute_cross_vote_confirmation / compute_currency_index_confirmation below
for the user's follow-up redesign (trend since DAY START, not just the
settle window; genuinely separate cross-count vs. liquidity-weighted-index
mechanisms instead of two numbers derived from the same computation).

Not wired into cls_practical/engine.py (the validated live path) - this is
research-stage, same discipline as every other research_cls_practical_*.py
extension in this repo: prove it out standalone first."""

from __future__ import annotations

import numpy as np
import pandas as pd


def pair_currencies(pair: str) -> tuple[str, str]:
    """'EURJPY' -> ('EUR', 'JPY'). Assumes the repo's standard 6-char pair
    convention (combined_strategy.data.INSTRUMENTS / strategy.cls_advanced.PAIRS)."""
    if len(pair) != 6:
        raise ValueError(f"expected a 6-char pair code like 'EURJPY', got {pair!r}")
    return pair[:3], pair[3:]


def signed_move(pair: str, ccy: str, move: pd.Series) -> pd.Series:
    """`move` (e.g. a pair's own move_06_09) re-signed so that positive
    always means `ccy` strengthening. `ccy` must be one of `pair`'s two
    currencies."""
    base, quote = pair_currencies(pair)
    if ccy == base:
        return move
    if ccy == quote:
        return -move
    raise ValueError(f"{ccy!r} is not part of pair {pair!r} ({base}/{quote})")


def compute_pair_specific_confirmation(
    traded_pair: str,
    traded_daily: pd.DataFrame,
    daily_by_ref_pair: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """`traded_daily`: strategy.cls_advanced.compute_daily_features() output
    for the traded pair itself (needs 'direction', date-indexed).
    `daily_by_ref_pair`: {pair_code: compute_daily_features() output} for
    every available reference cross (must include the traded pair's own two
    currencies somewhere in the code, e.g. base_ccy+X or X+quote_ccy;
    pairs unrelated to either currency are silently skipped). The traded
    pair itself, if present in this dict, is also skipped (it's not its own
    reference).

    Returns a date-indexed frame with:
      base_strength, quote_strength: mean sign-adjusted move_06_09 across all
        *other* reference pairs containing that currency (NaN if none found).
      strength_gap: base_strength - quote_strength (positive -> broad
        support for an UP break; the continuous "distance between indices"
        measure for continuous risk scaling).
      n_confirm / n_total: how many of the individual reference pairs
        (summed over both currencies' baskets) agree with the traded pair's
        OWN break direction / how many were available that day at all - the
        discrete "X of N" analogue of the mentor's "2/4"/"4/4".
      confirm_ratio: n_confirm / n_total.
      confirmed / strong_confirmed: confirm_ratio >= 0.5 / >= 0.99 (majority
        vs. near-unanimous), the two graduated tiers from the user's spec.
    """
    base, quote = pair_currencies(traded_pair)
    direction = traded_daily["direction"]
    idx = direction.index

    agree_count = pd.Series(0, index=idx, dtype=float)
    total_count = pd.Series(0, index=idx, dtype=float)
    base_signed_parts: list[pd.Series] = []
    quote_signed_parts: list[pd.Series] = []

    for ref_pair, ref_daily in daily_by_ref_pair.items():
        if ref_pair == traded_pair:
            continue
        ref_base, ref_quote = pair_currencies(ref_pair)
        involves_base = base in (ref_base, ref_quote)
        involves_quote = quote in (ref_base, ref_quote)
        if not involves_base and not involves_quote:
            continue  # irrelevant cross, e.g. GBP/CHF when trading EUR/JPY

        move = ref_daily["move_06_09"].reindex(idx)

        if involves_base:
            s = signed_move(ref_pair, base, move)
            base_signed_parts.append(s)
            agree = (np.sign(s) == direction) & direction.ne(0) & s.notna()
            agree_count = agree_count.add(agree.astype(float), fill_value=0.0)
            total_count = total_count.add(s.notna().astype(float), fill_value=0.0)

        if involves_quote:
            s = signed_move(ref_pair, quote, move)
            quote_signed_parts.append(s)
            # quote WEAKENING (negative quote-strength) supports an up-break
            agree = (np.sign(s) == -direction) & direction.ne(0) & s.notna()
            agree_count = agree_count.add(agree.astype(float), fill_value=0.0)
            total_count = total_count.add(s.notna().astype(float), fill_value=0.0)

    base_strength = (pd.concat(base_signed_parts, axis=1).mean(axis=1)
                      if base_signed_parts else pd.Series(np.nan, index=idx))
    quote_strength = (pd.concat(quote_signed_parts, axis=1).mean(axis=1)
                       if quote_signed_parts else pd.Series(np.nan, index=idx))

    out = pd.DataFrame({
        "base_strength": base_strength,
        "quote_strength": quote_strength,
        "strength_gap": base_strength - quote_strength,
        "n_confirm": agree_count,
        "n_total": total_count,
    })
    out["confirm_ratio"] = out["n_confirm"] / out["n_total"].replace(0, np.nan)
    out["confirmed"] = out["confirm_ratio"] >= 0.5
    out["strong_confirmed"] = out["confirm_ratio"] >= 0.99
    return out


def risk_multiplier(
    confirmation: pd.DataFrame,
    base_mult: float = 1.0,
    strong_mult: float = 1.5,
    gap_scale: float | None = None,
    gap_cap_mult: float = 2.0,
) -> pd.Series:
    """Turns compute_pair_specific_confirmation()'s output into a per-day
    risk multiplier, applied on top of the strategy's normal risk_pct.

    Discrete step (user's original spec): base_mult below strong-confirmation,
    strong_mult at strong_confirmed (~4/4-style near-unanimous agreement).
    Unconfirmed days get multiplier 0 (no trade) - filtering, not sizing,
    happens upstream via `confirmed`, this function assumes it's only
    evaluated on days that already passed that gate.

    Continuous refinement (user's later request, 2026-08-18): if
    `gap_scale` is given, ADD an extra multiplier proportional to
    abs(strength_gap) / gap_scale on top of the discrete step, capped at
    `gap_cap_mult`. `gap_scale` should be set to a typical/median
    abs(strength_gap) for the pair (e.g. from the IS period only, to avoid
    OOS leakage) so the scaling is comparable across pairs with different
    native move magnitudes (JPY-crosses move in bigger raw percentages than
    e.g. EUR/CHF, for instance) - NOT given a default value here on purpose,
    a wrong guess would silently miscalibrate every pair identically.
    """
    step = np.where(confirmation["strong_confirmed"], strong_mult, base_mult)
    mult = pd.Series(step, index=confirmation.index, dtype=float)

    if gap_scale is not None and gap_scale > 0:
        extra = (confirmation["strength_gap"].abs() / gap_scale).clip(upper=gap_cap_mult - 1.0)
        mult = (mult + extra).clip(upper=gap_cap_mult)

    return mult


# ======================================================================
# 2026-08-18 redesign: genuinely separate Cross-Filter (equal-weighted
# majority vote) vs. Index-Filter (liquidity-weighted continuous index),
# both using each reference pair's own trend since DAY START (00:00
# Berlin), not just the 06:00-09:00 settle window used above - user's own
# correction after the settle-window version tested worse on all four
# re-tested instruments (see module docstring).
# ======================================================================

DAY_START_HOUR = 0.0

# Named windows for the 2026-08-18 sweep request ("Crosses in der Asia oder
# Crosses von 6:00-9:00 Uhr" -- i.e. is the reference pairs' own trend read
# from the Asia range, the settle window, or since day start). "settle"
# reproduces compute_pair_specific_confirmation's ORIGINAL (empirically
# worse-performing) window for a clean apples-to-apples comparison point.
WINDOWS = {
    "asia": (0.0, 6.0),      # Asia range only
    "settle": (6.0, 9.0),    # 06:00-09:00, the first (rejected) version's window
    "day_start": (0.0, None),  # 00:00 -> checkpoint_hour (current default)
}


def _window_move(df: pd.DataFrame, window_start_hour: float, window_end_hour: float | None) -> pd.Series:
    """Per Berlin-calendar-day: (close of the last bar before window_end_hour)
    / (open of the first bar at/after window_start_hour) - 1.
    window_end_hour=None means "up to whatever the caller reindexes to" is
    NOT supported here - callers must resolve it to an actual hour
    (typically the confirmation checkpoint) before calling. `df` must be
    OHLC with a Berlin-tz-aware (or naive-but-already-Berlin) DatetimeIndex."""
    from strategy.cls_advanced import to_berlin

    if window_end_hour is None:
        raise ValueError("window_end_hour must be resolved to a concrete hour before calling _window_move")

    berlin = to_berlin(df.index)
    hour = berlin.hour + berlin.minute / 60.0
    date = berlin.date

    d = pd.DataFrame({"date": date, "hour": hour, "open": df["open"].to_numpy(), "close": df["close"].to_numpy()})
    rows: dict = {}
    for day, g in d.groupby("date"):
        in_window = g[(g["hour"] >= window_start_hour) & (g["hour"] < window_end_hour)]
        if in_window.empty:
            continue
        window_open = in_window["open"].iloc[0]
        window_close = in_window["close"].iloc[-1]
        if window_open:
            rows[day] = window_close / window_open - 1
    return pd.Series(rows, dtype=float)


def _day_start_to_checkpoint_move(df: pd.DataFrame, checkpoint_hour: float) -> pd.Series:
    """Backwards-compatible alias: the original 00:00-to-checkpoint window."""
    return _window_move(df, 0.0, checkpoint_hour)


def cross_vote_breakdown(
    traded_pair: str,
    traded_direction: pd.Series,
    ref_price_data: dict[str, pd.DataFrame],
    checkpoint_hour: float = 9.25,
    window: str = "day_start",
) -> pd.DataFrame:
    """Per-(day, reference-pair) detail behind compute_cross_vote_confirmation
    (2026-08-19, user request: a page to see day-by-day WHICH crosses are
    voting which way, not just the aggregate ratio) - long-format, one row
    per reference pair actually used that day: which of the traded pair's
    two currencies it was checked against, its own signed move over
    `window`, and whether that move agrees with the traded pair's actual
    break direction that day. Reimplements compute_cross_vote_confirmation's
    inner loop rather than refactor it, so the validated aggregate function
    stays byte-for-byte untouched - this is a display/diagnostics helper
    only, not used by cls_practical/engine.py."""
    if window not in WINDOWS:
        raise ValueError(f"window must be one of {list(WINDOWS)}, got {window!r}")
    win_start, win_end = WINDOWS[window]

    base, quote = pair_currencies(traded_pair)
    idx = traded_direction.index

    rows = []
    for ref_pair, ref_df in ref_price_data.items():
        if ref_pair == traded_pair:
            continue
        ref_base, ref_quote = pair_currencies(ref_pair)
        involves_base = base in (ref_base, ref_quote)
        involves_quote = quote in (ref_base, ref_quote)
        if not involves_base and not involves_quote:
            continue
        move = _window_move(ref_df, win_start, win_end if win_end is not None else checkpoint_hour).reindex(idx)

        if involves_base:
            s = signed_move(ref_pair, base, move)
            agree = (np.sign(s) == traded_direction) & traded_direction.ne(0) & s.notna()
            for day in idx[s.notna() & traded_direction.ne(0)]:
                rows.append({"date": day, "ref_pair": ref_pair, "checked_currency": base,
                             "move_pct": s.loc[day], "vote_agrees": bool(agree.loc[day])})
        if involves_quote:
            s = signed_move(ref_pair, quote, move)
            agree = (np.sign(s) == -traded_direction) & traded_direction.ne(0) & s.notna()
            for day in idx[s.notna() & traded_direction.ne(0)]:
                rows.append({"date": day, "ref_pair": ref_pair, "checked_currency": quote,
                             "move_pct": s.loc[day], "vote_agrees": bool(agree.loc[day])})

    return pd.DataFrame(rows, columns=["date", "ref_pair", "checked_currency", "move_pct", "vote_agrees"])


def compute_cross_vote_confirmation(
    traded_pair: str,
    traded_direction: pd.Series,
    ref_price_data: dict[str, pd.DataFrame],
    checkpoint_hour: float = 9.25,
    window: str = "day_start",
    confirm_threshold: float = 0.5,
) -> pd.DataFrame:
    """Cross-Filter: mentor-style discrete majority vote. For each reference
    pair (equal weight, one pair = one vote), is ITS OWN price trending -
    over `window` (2026-08-18 sweep request: "asia" = 00:00-06:00, "settle"
    = 06:00-09:00 i.e. compute_pair_specific_confirmation's original,
    empirically worse window, "day_start" (default) = 00:00-checkpoint_hour)
    - in the direction that would support the traded pair's own break?
    `traded_direction`: date-indexed {-1,0,1} from strategy.cls_advanced.
    compute_daily_features()['direction']. `confirm_threshold` (2026-08-18
    sweep request, e.g. 0.4 vs 0.5 vs 0.6): fraction of available reference
    pairs that must agree for `confirmed` - looser than 0.5 lets more days
    through at the cost of weaker individual agreement, stricter does the
    opposite. Output columns match compute_pair_specific_confirmation's
    discrete half (n_confirm/n_total/confirm_ratio/confirmed/strong_confirmed)
    so all these mechanisms plug into risk_multiplier() / engine.py the
    same way."""
    if window not in WINDOWS:
        raise ValueError(f"window must be one of {list(WINDOWS)}, got {window!r}")
    win_start, win_end = WINDOWS[window]

    base, quote = pair_currencies(traded_pair)
    idx = traded_direction.index

    agree_count = pd.Series(0.0, index=idx)
    total_count = pd.Series(0.0, index=idx)

    for ref_pair, ref_df in ref_price_data.items():
        if ref_pair == traded_pair:
            continue
        ref_base, ref_quote = pair_currencies(ref_pair)
        if base not in (ref_base, ref_quote) and quote not in (ref_base, ref_quote):
            continue
        move = _window_move(ref_df, win_start, win_end if win_end is not None else checkpoint_hour).reindex(idx)

        if base in (ref_base, ref_quote):
            s = signed_move(ref_pair, base, move)
            agree = (np.sign(s) == traded_direction) & traded_direction.ne(0) & s.notna()
            agree_count = agree_count.add(agree.astype(float), fill_value=0.0)
            total_count = total_count.add(s.notna().astype(float), fill_value=0.0)
        if quote in (ref_base, ref_quote):
            s = signed_move(ref_pair, quote, move)
            agree = (np.sign(s) == -traded_direction) & traded_direction.ne(0) & s.notna()
            agree_count = agree_count.add(agree.astype(float), fill_value=0.0)
            total_count = total_count.add(s.notna().astype(float), fill_value=0.0)

    out = pd.DataFrame({"n_confirm": agree_count, "n_total": total_count})
    out["confirm_ratio"] = out["n_confirm"] / out["n_total"].replace(0, np.nan)
    out["confirmed"] = out["confirm_ratio"] >= confirm_threshold
    out["strong_confirmed"] = out["confirm_ratio"] >= 0.99
    return out


# Hasbrouck & Levich (2019, SSRN 2912976), Table 5, "Relative Spread x
# 10^4 (bp)", 2016 column - the most recent CLS-settlement-based spread
# estimate the paper reports. Used as an inverse-liquidity weight below,
# the same principle real currency indices (DXY etc.) use to weight
# constituents by trade importance rather than counting each equally.
PAPER_RELATIVE_SPREAD_BPS_2016 = {
    "AUDJPY": 1.196, "AUDUSD": 0.925, "EURCHF": 1.099, "EURGBP": 0.886,
    "EURJPY": 0.732, "EURUSD": 0.444, "GBPJPY": 1.098, "GBPUSD": 0.697,
    "NZDUSD": 1.459, "USDCAD": 0.854, "USDCHF": 1.040, "USDJPY": 0.540,
    "USDMXN": 3.180,
}


def _liquidity_weight(pair: str) -> float:
    """1 / paper spread (bp). Pairs the paper doesn't cover (it studied 13
    majors only - most of the EUR/GBP/JPY/CAD/AUD cross baskets used
    elsewhere in this module aren't in it) fall back to the MEDIAN weight
    of the covered pairs - a neutral, disclosed choice, not a privileging
    or penalising guess."""
    spread = PAPER_RELATIVE_SPREAD_BPS_2016.get(pair)
    if spread is None:
        spread = float(np.median(list(PAPER_RELATIVE_SPREAD_BPS_2016.values())))
    return 1.0 / spread


def compute_currency_index_confirmation(
    traded_pair: str,
    traded_direction: pd.Series,
    ref_price_data: dict[str, pd.DataFrame],
    checkpoint_hour: float = 9.25,
    window: str = "day_start",
) -> pd.DataFrame:
    """Index-Filter: ONE liquidity-weighted currency-index move per
    currency (base/quote of the traded pair), built over `window` (see
    compute_cross_vote_confirmation's docstring for the "asia"/"settle"/
    "day_start" options) across all available reference pairs containing
    that currency, weighted by _liquidity_weight instead of counted
    equally - genuinely different arithmetic from
    compute_cross_vote_confirmation's equal-weighted vote (a naive
    unweighted index and an equal-weighted average are mathematically
    identical for simple returns; the weighting is what makes this a
    distinct, separately-testable mechanism, not just a rename).
    Confirmed if the resulting base-index move minus quote-index move
    (index_gap) agrees in sign with the traded pair's own break."""
    if window not in WINDOWS:
        raise ValueError(f"window must be one of {list(WINDOWS)}, got {window!r}")
    win_start, win_end = WINDOWS[window]

    base, quote = pair_currencies(traded_pair)
    idx = traded_direction.index

    base_parts, base_weights = [], []
    quote_parts, quote_weights = [], []

    for ref_pair, ref_df in ref_price_data.items():
        if ref_pair == traded_pair:
            continue
        ref_base, ref_quote = pair_currencies(ref_pair)
        if base not in (ref_base, ref_quote) and quote not in (ref_base, ref_quote):
            continue
        move = _window_move(ref_df, win_start, win_end if win_end is not None else checkpoint_hour).reindex(idx)
        w = _liquidity_weight(ref_pair)

        if base in (ref_base, ref_quote):
            base_parts.append(signed_move(ref_pair, base, move) * w)
            base_weights.append(w)
        if quote in (ref_base, ref_quote):
            quote_parts.append(signed_move(ref_pair, quote, move) * w)
            quote_weights.append(w)

    # NB: the denominator is the FULL basket weight, even on days where one
    # constituent is missing (NaN) and .sum(axis=1, skipna=True) silently
    # drops it - a disclosed simplification (slightly understates the index
    # on those days) rather than a per-day dynamic renormalisation.
    base_index = (pd.concat(base_parts, axis=1).sum(axis=1) / sum(base_weights)
                  if base_parts else pd.Series(np.nan, index=idx))
    quote_index = (pd.concat(quote_parts, axis=1).sum(axis=1) / sum(quote_weights)
                   if quote_parts else pd.Series(np.nan, index=idx))

    # Degenerate gracefully if one side has literally no reference pairs at
    # all (e.g. Gold: "XAU" never appears in any FX cross, only the USD
    # side exists) - fall back to the single available side instead of
    # letting a NaN half silently zero out every confirmation.
    if base_parts and quote_parts:
        index_gap = base_index - quote_index
    elif base_parts:
        index_gap = base_index
    elif quote_parts:
        index_gap = -quote_index
    else:
        index_gap = pd.Series(np.nan, index=idx)

    out = pd.DataFrame({"base_index_move": base_index, "quote_index_move": quote_index, "index_gap": index_gap})
    out["confirmed"] = (np.sign(out["index_gap"]) == traded_direction) & traded_direction.ne(0)
    return out
