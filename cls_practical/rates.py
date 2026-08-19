"""Rates-Ampel (grün/gelb/rot) - the source playbook's "Rates" filter,
quantified against the best freely available intraday proxy: BUND vs.
USTBOND CFD price action over the Settle window (06:00-09:00 Berlin, same
window as strategy/cls_advanced.py). Disclosed substitution: this is a
LONG-END duration/term-premium signal (~10y Bund, ~15-25y UST future), not
the front-end/2y relative-rate-expectations signal the source material
describes ("Front End Rates oder kurze Zinserwartungen") - no free source
gives that at intraday resolution for both EUR and USD (checked 2026-08-11:
neither Dukascopy nor yfinance lists a EUR front-end/2y intraday feed).
Treat any "grün"/"rot" read below as a long-end proxy read, not a literal
2y-yield-spread read.

Sign convention: a bond's PRICE moves inversely to its yield. "EUR rates
strengthen" (page 6 of the source deck) means EUR yields rise, i.e. Bund
price FALLS. "USD rates weaken" means UST yields fall, i.e. UST price
RISES. Both support EUR/USD LONG. So:

    rate_support_score = ustbond_return - bund_return

is positive when USTBOND outperforms BUND in price (USD yields falling
relative to EUR yields) -> supports EUR/USD long; negative -> supports
EUR/USD short.
"""

import numpy as np
import pandas as pd

from strategy.cls_advanced import ASIA_END, SETTLE_END, to_berlin


def compute_rate_support_score(bund: pd.DataFrame, ustbond: pd.DataFrame) -> pd.Series:
    """Per Berlin calendar day: rate_support_score over the Settle window
    (06:00-09:00), see module docstring for sign convention. NaN on days
    where either instrument has no bars in the window (e.g. CFD-specific
    holiday gaps)."""
    rows = {}
    for label, df in (("bund", bund), ("ustbond", ustbond)):
        berlin = to_berlin(df.index)
        hour = berlin.hour + berlin.minute / 60.0
        date = pd.Series(berlin.date, index=df.index)
        d = pd.DataFrame({"date": date, "hour": hour, "close": df["close"].to_numpy(), "open": df["open"].to_numpy()})
        settle = d[(d["hour"] >= ASIA_END) & (d["hour"] < SETTLE_END)]
        by_day = settle.groupby("date").agg(open_=("open", "first"), close_=("close", "last"))
        ret = (by_day["close_"] / by_day["open_"] - 1).rename(label)
        rows[label] = ret

    joined = pd.concat(rows.values(), axis=1, join="outer")
    joined.columns = list(rows.keys())
    return (joined["ustbond"] - joined["bund"]).rename("rate_support_score")


def compute_daily_rate_score(bund: pd.DataFrame, ustbond: pd.DataFrame, lag_days: int = 1) -> pd.Series:
    """Daily-candle (not Settle-window) analogue of compute_rate_support_score
    (2026-08-19, user request: "wir hatten den Zinsfilter auf Tagesbasis
    schoneinmal gebaut" - referring to bond_yield_indicator/, which used
    FRED 10y yields and failed because 6 of 7 countries are only MONTHLY on
    FRED, see knowledge/projects/bond-yield-spread-indikator.md. Re-verified
    2026-08-19: DE's FRED series is still monthly, latest print 2026-06-01 -
    a "last daily candle" read is meaningless on a series that only moves
    once a month. BUND/USTBOND CFDs (already used by compute_rate_support_score
    above) update daily, so this reuses THAT data source instead of FRED,
    just over the FULL calendar day (00:00-24:00 Berlin open-to-close)
    instead of only the 06:00-09:00 Settle window.

    Same sign convention as compute_rate_support_score (ustbond_return -
    bund_return, positive = USD yields falling relative to EUR yields ->
    supports EUR/USD long). `lag_days` (default 1, "die Richtung der letzten
    Tageskerze") shifts the score forward so today's read only ever uses
    fully-closed PRIOR-day candle(s) - the whole point of a daily-candle
    validation is that it's a leading/independent read, not the same-day
    window compute_rate_support_score already provides."""
    rows = {}
    for label, df in (("bund", bund), ("ustbond", ustbond)):
        berlin = to_berlin(df.index)
        date = pd.Series(berlin.date, index=df.index)
        d = pd.DataFrame({"date": date, "close": df["close"].to_numpy(), "open": df["open"].to_numpy()})
        by_day = d.groupby("date").agg(open_=("open", "first"), close_=("close", "last"))
        ret = (by_day["close_"] / by_day["open_"] - 1).rename(label)
        rows[label] = ret

    joined = pd.concat(rows.values(), axis=1, join="outer")
    joined.columns = list(rows.keys())
    score = (joined["ustbond"] - joined["bund"]).rename("daily_rate_score")
    return score.shift(lag_days)


def classify_rates_ampel(
    rate_support_score: pd.Series, direction: pd.Series, z_window: int = 60, z_threshold: float = 0.5
) -> pd.Series:
    """grün (score supports the day's break direction, |z|>=threshold),
    rot (score opposes it, |z|>=threshold), gelb (everything else -
    including days with too little rolling history for a z-score yet).
    z-score is computed against a trailing window of PRIOR days' scores
    only (shift(1) before rolling) - no lookahead, and no fixed "typical
    daily move" assumed since bond-CFD volatility regimes drift over a
    multi-year backtest."""
    prior = rate_support_score.shift(1)
    rolling_std = prior.rolling(z_window, min_periods=z_window // 2).std()
    z = rate_support_score / rolling_std

    aligned = pd.Series(index=rate_support_score.index, dtype=object)
    z_al, dir_al = z.align(direction, join="left")
    sign_matches = np.sign(z_al) == dir_al
    confirmed = sign_matches & (z_al.abs() >= z_threshold)
    contradicted = (~sign_matches) & (z_al.abs() >= z_threshold) & dir_al.notna() & (dir_al != 0)

    out = pd.Series("gelb", index=rate_support_score.index)
    out[confirmed.fillna(False)] = "grün"
    out[contradicted.fillna(False)] = "rot"
    out[z_al.isna()] = "gelb"
    return out


def compute_daily_rate_risk_multiplier(
    bund: pd.DataFrame,
    ustbond: pd.DataFrame,
    direction: pd.Series,
    lag_days: int = 2,
    z_window: int = 60,
    z_threshold: float = 0.5,
    confirmed_mult: float = 1.75,
    base_mult: float = 1.0,
) -> pd.Series:
    """ADOPTED 2026-08-19 (user: "sehr gut so uebernehmen wir das! Gerne die
    1,75x Variante") - the risk-SCALING use of the daily-candle rates score
    (compute_daily_rate_score), as opposed to using it as a hard trade gate.
    Promoted out of scripts/research_cls_practical_daily_rate_risk_scaling.py
    into a reusable function once validated: at a flat 1% base risk_pct, all
    203 EUR/USD baseline trades kept (n unchanged - unlike the AND-gate
    variant, this does NOT shrink the sample), scaling risk to `confirmed_mult`
    (1.75x) on days classify_rates_ampel reads "grün" at z_threshold=0.5
    (lag=2 calendar days) improved EVERY equity-curve metric simultaneously,
    on Gesamt/IS/OOS all three: Sharpe 0.75->0.84, Calmar 0.38->0.48, total
    PnL $73,559->$115,585 - at the cost of a somewhat deeper max drawdown
    (-13.37%->-14.70%, expected: literally bigger positions on ~24% of days).
    The whole 9-cell (z_threshold x multiplier) grid tested moved monotonically
    in the same direction, which is why this was adopted rather than treated
    as a lucky single cell.

    Returns a date-indexed float Series: `confirmed_mult` where the daily
    rate score (BUND/USTBOND CFD, full prior trading day, lagged `lag_days`)
    agrees with the day's break `direction` beyond `z_threshold` rolling
    standard deviations, `base_mult` (1.0, i.e. no change) everywhere else -
    feed straight into simulate_cls_practical(risk_multiplier=...). Does NOT
    touch use_rates_filter/filter gating at all (that stays False, i.e. no
    trades are dropped) - this is purely a position-size overlay on top of
    the existing, unchanged trade-selection logic."""
    score = compute_daily_rate_score(bund, ustbond, lag_days=lag_days)
    ampel = classify_rates_ampel(score, direction, z_window=z_window, z_threshold=z_threshold)
    mult = pd.Series(base_mult, index=ampel.index)
    mult[ampel == "grün"] = confirmed_mult
    return mult
