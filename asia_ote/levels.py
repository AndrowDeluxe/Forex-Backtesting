"""Asia-range levels for asia_ote (chat 2026-08-21, mentor material via
TradingView chart screenshots): same Asia window (00:00-06:00 Europe/Berlin)
as strategy/cls_advanced.py, but a different entry mechanism - a
Fibonacci retracement placed ON the Asia range itself (0=asia_low,
1=asia_high, standard ICT premium/discount convention: ratio>0.5 =
premium/sell zone, ratio<0.5 = discount/buy zone), the 6:00 candle's own
close read against those levels, and two target families (nearest
untested prior Asia range extreme, nearest un-touched monthly pivot
level) instead of a fixed time-exit.

Disclosed interpretation choices (the source is discretionary chart
material, not a written spec - same discipline as cls_advanced.py's own
docstring): the mentor's own Gann-Box fib levels from the screenshot
(0.12/0.268/0.438/0.5/0.568/0.718/0.86) are kept as the default candidate
set (MENTOR_FIB_LEVELS) alongside the textbook Fibonacci set
(STANDARD_FIB_LEVELS) so both can be swept, not just assumed correct."""

import numpy as np
import pandas as pd

ASIA_START, ASIA_END = 0.0, 6.0  # Berlin hours, same as strategy.cls_advanced

MENTOR_FIB_LEVELS = [0.12, 0.268, 0.438, 0.5, 0.568, 0.718, 0.86]
STANDARD_FIB_LEVELS = [0.236, 0.382, 0.5, 0.618, 0.786]


def _berlin_index(df: pd.DataFrame) -> pd.DatetimeIndex:
    idx = df.index
    return idx.tz_localize("UTC").tz_convert("Europe/Berlin") if idx.tz is None else idx.tz_convert("Europe/Berlin")


def compute_daily_asia_levels(m15_df: pd.DataFrame) -> pd.DataFrame:
    """One row per Berlin calendar day: asia_high/asia_low (00:00-06:00
    range) and the 6:00 M15 candle's own OHLC (06:00-06:15 bar - the first
    bar AFTER the Asia range closes, "die 6:00 Uhr Candle"). Rows with an
    incomplete Asia range or a missing 6:00 candle (holidays/data gaps) are
    dropped, not silently filled."""
    idx = _berlin_index(m15_df)
    hour = idx.hour + idx.minute / 60.0
    date = idx.date

    d = pd.DataFrame({
        "date": date, "hour": hour,
        "open": m15_df["open"].to_numpy(), "high": m15_df["high"].to_numpy(),
        "low": m15_df["low"].to_numpy(), "close": m15_df["close"].to_numpy(),
    })

    rows = []
    for day, g in d.groupby("date"):
        asia = g[(g["hour"] >= ASIA_START) & (g["hour"] < ASIA_END)]
        candle_0600 = g[(g["hour"] >= ASIA_END) & (g["hour"] < ASIA_END + 0.25)]
        if asia.empty or candle_0600.empty:
            continue
        asia_high, asia_low = float(asia["high"].max()), float(asia["low"].min())
        c = candle_0600.iloc[0]
        rows.append({
            "date": day, "asia_high": asia_high, "asia_low": asia_low,
            "c0600_open": float(c["open"]), "c0600_high": float(c["high"]),
            "c0600_low": float(c["low"]), "c0600_close": float(c["close"]),
        })
    out = pd.DataFrame(rows).set_index("date")
    rng = out["asia_high"] - out["asia_low"]
    out["c0600_ratio"] = (out["c0600_close"] - out["asia_low"]) / rng  # 0=asia_low .. 1=asia_high
    return out


def fib_price(asia_low: float, asia_high: float, ratio: float) -> float:
    """ratio=0 -> asia_low, ratio=1 -> asia_high (standard ICT premium/
    discount convention - premium is ratio>0.5, discount is ratio<0.5)."""
    return asia_low + ratio * (asia_high - asia_low)


def compute_monthly_pivots(d1_df: pd.DataFrame) -> pd.DataFrame:
    """Standard floor-trader pivot (PP, R1/R2, S1/S2) computed from the
    PREVIOUS complete calendar month's H/L/C, held constant for every day
    of the current month (the conventional monthly-pivot convention - not
    recalculated intra-month)."""
    idx = _berlin_index(d1_df)
    monthly = pd.DataFrame({
        "high": d1_df["high"].to_numpy(), "low": d1_df["low"].to_numpy(), "close": d1_df["close"].to_numpy(),
    }, index=idx.tz_localize(None))
    m = monthly.resample("MS").agg({"high": "max", "low": "min", "close": "last"})
    pp = (m["high"] + m["low"] + m["close"]) / 3
    r1 = 2 * pp - m["low"]
    s1 = 2 * pp - m["high"]
    r2 = pp + (m["high"] - m["low"])
    s2 = pp - (m["high"] - m["low"])
    piv = pd.DataFrame({"pp": pp, "r1": r1, "s1": s1, "r2": r2, "s2": s2})
    # BUGFIX (chat 2026-08-21, caught by user question "Pivot-Methode
    # ueberpruft?"): row "2024-02-01" starts out holding February's OWN
    # H/L/C-derived pivot - .shift(1) alone already moves January's pivot
    # into that row (correct: Feb trades on Jan's pivot). The previous code
    # ALSO added +1 MonthBegin to the index afterwards, re-labelling that
    # already-correct row as March - a double shift that made every month
    # trade on the pivot from TWO months prior, not one. Fix: shift(1) only.
    piv = piv.shift(1)
    return piv


def daily_pivot_levels(daily_index: pd.DatetimeIndex, monthly_pivots: pd.DataFrame) -> pd.DataFrame:
    """Broadcasts compute_monthly_pivots()'s one-row-per-month table onto
    one row per day in `daily_index` (asof, using the pivot set active for
    that day's calendar month)."""
    month_starts = pd.DatetimeIndex([pd.Timestamp(d).replace(day=1) for d in daily_index])
    return monthly_pivots.reindex(month_starts).set_axis(daily_index)


def untested_asia_targets(daily_levels: pd.DataFrame) -> pd.DataFrame:
    """For each day (in chronological order), the nearest PRIOR day's
    asia_high still untouched by any bar since it formed (a valid upside
    target) and nearest prior asia_low still untouched (valid downside
    target) - "unmitigated" in ICT terms. A level is removed from the
    untested pool the first day price closes beyond it (conservative:
    close-based mitigation, matching the "Candle Closes" discipline)."""
    dates = daily_levels.index
    asia_high = daily_levels["asia_high"].to_numpy()
    asia_low = daily_levels["asia_low"].to_numpy()
    c0600_close = daily_levels["c0600_close"].to_numpy()  # daily reference close for mitigation checks

    n = len(dates)
    nearest_untested_high = np.full(n, np.nan)
    nearest_untested_low = np.full(n, np.nan)

    open_highs: list[float] = []  # untested asia_high levels (resistance candidates)
    open_lows: list[float] = []   # untested asia_low levels (support candidates)

    for i in range(n):
        px = c0600_close[i]
        # mitigate: any open level the price has now closed beyond is no longer "untested"
        open_highs = [lv for lv in open_highs if px < lv]
        open_lows = [lv for lv in open_lows if px > lv]

        above = [lv for lv in open_highs if lv > px]
        below = [lv for lv in open_lows if lv < px]
        nearest_untested_high[i] = min(above) if above else np.nan
        nearest_untested_low[i] = max(below) if below else np.nan

        open_highs.append(asia_high[i])
        open_lows.append(asia_low[i])

    return pd.DataFrame({"untested_high": nearest_untested_high, "untested_low": nearest_untested_low}, index=dates)
