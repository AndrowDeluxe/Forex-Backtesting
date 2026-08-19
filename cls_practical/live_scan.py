"""Live-Scan fuer cls_practical (Forward-Test-Vorbereitung, 2026-08-13) --
kein eigener Bot noch, nur ein Punkt-in-Zeit-Snapshot: laedt frische Daten
bis "jetzt" (kurzes Trailing-Fenster, nicht die volle 8-Jahre-Historie --
schnell genug fuer einen stuendlichen/taeglichen Scan), laesst
simulate_cls_practical() darueber laufen (exakt dieselbe Logik wie im
Backtest, keine Duplizierung der Entry/Exit-Regeln) und meldet:
- ist heute ein Continuation-/Reversal-/Kein-Signal-Tag (Tagesfilter-Status)?
- hat der Fractal/CHOCH-Trigger heute bereits gefuellt (falls ja: Entry/SL/TP)?

Trailing-Fenster 400 Kalendertage (gleiche Konvention wie
ou_paper_backtest/scanner.py) -- genug Vorlauf fuer SMA(100)/ADX(14)/ADR(14)-
Warmup, ohne die volle Historie neu laden zu muessen."""

import datetime as dt

import numpy as np
import pandas as pd

from asian_range_breakout.cls_settle import compute_adr
from strategy.cls_advanced import ASIA_END, ENTRY_HOUR, PAIRS, SETTLE_END, compute_cross_confirmation, compute_daily_features, to_berlin
from strategy.indicators import compute_adx, compute_atr

from .data import fetch_eurusd_entry_tf_berlin, fetch_major_m15_berlin, fetch_rate_instrument_m5_berlin
from .engine import _first_fractal, _minutes_of, simulate_cls_practical, trend_bias
from .rates import compute_daily_rate_risk_multiplier

OTHER_MAJORS = [p for p in PAIRS if p != "EURUSD"]
LOOKBACK_DAYS = 400


def scan_today() -> dict:
    today = dt.date.today()
    start = (today - dt.timedelta(days=LOOKBACK_DAYS)).isoformat()
    end = today.isoformat()

    eurusd_m5 = fetch_eurusd_entry_tf_berlin("M5", start, end, force_refresh=True)
    other_majors_m15 = {p: fetch_major_m15_berlin(p, start, end, force_refresh=True) for p in OTHER_MAJORS}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", start, end, force_refresh=True)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", start, end, force_refresh=True)

    if eurusd_m5.empty:
        return {"date": today.isoformat(), "status": "keine Daten (Wochenende/Feiertag/Fehler)"}

    # 1) Tagesfilter-Status fuer heute (unabhaengig davon, ob schon ein Trigger
    # gefeuert hat) -- dieselben Bausteine wie die Funnel-Diagnose.
    daily = compute_daily_features(eurusd_m5)
    daily_by_pair = {"EURUSD": daily}
    for pair, df in other_majors_m15.items():
        if not df.empty:
            daily_by_pair[pair] = compute_daily_features(df)
    cross_confirm = compute_cross_confirmation(daily_by_pair)["EURUSD"]

    berlin_today = pd.Timestamp(today)
    if berlin_today.date() not in daily.index:
        row = {"date": today.isoformat(), "status": "heute noch keine vollstaendige Settle-Range (vor 09:00 Berlin?)"}
    else:
        d = daily.loc[berlin_today.date()]
        direction = d["direction"]
        holds = d["holds_0915"]
        c_val = cross_confirm.get(berlin_today.date(), None)

        # Zins-Risiko-Skalierung (2026-08-19, uebernommen aus
        # scripts/research_cls_practical_daily_rate_risk_scaling.py) -- rein
        # informativ hier, aendert NICHTS an Trigger/Entry/SL/TP unten (die
        # haengen nur an use_rates_filter, das bleibt False); zeigt nur an,
        # ob die empfohlene Positionsgroesse heute ueber dem 1.0x-Standard
        # liegt (lag=2 Handelstage BUND/USTBOND, z>=0.5 -> 1.75x).
        rate_mult_series = compute_daily_rate_risk_multiplier(bund_m5, ustbond_m5, daily["direction"])
        rate_mult_today = rate_mult_series.get(berlin_today.date(), None)

        row = {
            "date": today.isoformat(),
            "break_direction": {1: "long", -1: "short", 0: "kein Break"}.get(direction, "n/a"),
            "holds_0915": bool(holds) if pd.notna(holds) else None,
            "cross_confirmed": bool(c_val) if c_val is not None else None,
            "rate_risk_multiplier": float(rate_mult_today) if rate_mult_today is not None and pd.notna(rate_mult_today) else None,
        }

    # 2) Tatsaechlicher Trigger heute? -- simulate_cls_practical() auf dem
    # Trailing-Fenster laufen lassen (identische Regeln wie Backtest), dann
    # prüfen ob ein Trade HEUTE entered hat.
    trades = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5)
    if not trades.empty:
        today_trades = trades[trades["entry_time"].dt.date == today]
    else:
        today_trades = trades

    if len(today_trades) > 0:
        t = today_trades.iloc[0]
        row.update({
            "triggered": True, "setup": t["setup"], "direction": t["direction"],
            "entry_time": str(t["entry_time"]), "entry_price": round(t["entry_price"], 5),
            "sl": round(t["sl"], 5), "tp": round(t["tp"], 5),
        })
    else:
        row["triggered"] = False

    return row


def find_pending_setup(
    eurusd_m5: pd.DataFrame,
    other_majors_m15: dict[str, pd.DataFrame],
    sma_window: int = 100,
    adr_period: int = 14,
    adr_mult: float = 0.35,
    min_sl_atr_mult: float = 1.0,
    entry_cutoff: str = "12:00",
    min_adx: float | None = 15.0,
    adx_period: int = 14,
    use_cross_filter: bool = True,
    as_of_date: dt.date | None = None,
) -> dict | None:
    """Built 2026-08-13 for the live execution bots (CLS-Practical-Bridge,
    separate private project) -- NOT used by the Live-Log page (scan_today()
    above is unchanged). Unlike simulate_cls_practical(), which only ever
    returns a trade once its resting stop order has actually been FILLED
    (_continuation_trigger()/_reversal_trigger() return None until price
    touches trigger_level), this returns the pending order's parameters as
    soon as the triggering fractal is CONFIRMED, regardless of whether price
    has reached it yet -- the bots need this to place a genuine broker-side
    Buy-Stop/Sell-Stop at the fractal level (closest replication of the
    backtest's own "was the level ever touched" fill condition, evaluated by
    the broker's live feed instead of bar-by-bar after the fact).

    Deliberately reimplements only the short pivot-finding half of
    _continuation_trigger()/_reversal_trigger() (the "still_outside"/
    "Rueckkehr in die Range" checks, a dozen lines) rather than changing
    those functions -- they stay exactly as the backtest uses them. Reuses
    _first_fractal() directly (already lookahead-safe, module-level).

    Hardcodes the CURRENT LOCKED default configuration (see
    app_pages/cls_practical_strategy.py "Weg dorthin": SMA100+ADX>=15 trend
    filter, rates filter off, cross filter on, AND-mode, no break-even, no
    execution overlay, ADR-based TP) rather than exposing the full research
    parameter surface simulate_cls_practical() does -- this is for live
    execution of the one validated configuration, not for sweeps.

    Disclosed approximation: the ATR-floor check (min_sl_atr_mult) uses ATR
    at the fractal's OWN confirmation bar, not at the eventual fill bar (the
    backtest can use the fill bar's ATR since it already knows when/if the
    fill happened -- a live pending order doesn't know its own future fill
    time). ATR rarely moves enough over a same-morning window for this to
    flip the floor check, but it is a real, disclosed difference from the
    backtest's own gating.

    Returns None if no daily filter passes yet, or a filter passes but no
    fractal has been confirmed yet today. Otherwise: {"setup":
    "continuation"|"reversal", "direction": "long"|"short", "entry":
    trigger_level, "sl": sl_level, "tp": adr-based target, "pivot_time":
    ISO string of the confirming fractal's own bar}. entry/sl/tp are RAW
    price levels (no synthetic spread/slippage adjustment, unlike the
    backtest's entry_price/exit_price bookkeeping) -- the broker applies its
    own real spread at actual fill.

    as_of_date: defaults to today (live use) -- overridable so this can be
    tested against a known historical day (compare against
    simulate_cls_practical()'s own trades for that date: entry/sl must match
    exactly, since both paths compute trigger_level/sl_level identically)."""

    today = as_of_date if as_of_date is not None else dt.date.today()

    daily = compute_daily_features(eurusd_m5)
    if today not in daily.index:
        return None
    row = daily.loc[today]
    direction = row["direction"]
    holds = row["holds_0915"]
    if direction == 0 or pd.isna(holds):
        return None

    daily_by_pair = {"EURUSD": daily}
    for pair, df in other_majors_m15.items():
        if not df.empty:
            daily_by_pair[pair] = compute_daily_features(df)
    cross_confirm = compute_cross_confirmation(daily_by_pair)["EURUSD"]
    c_val = cross_confirm.get(today, np.nan)

    berlin_idx = to_berlin(eurusd_m5.index)
    date_series = pd.Series(berlin_idx.date, index=eurusd_m5.index)
    daily_close = eurusd_m5["close"].groupby(date_series).last()
    trend = trend_bias(daily_close, sma_window=sma_window, ma_type="sma")
    t_val = trend.get(today, np.nan)

    if pd.isna(c_val) or pd.isna(t_val):
        return None

    if min_adx is not None:
        daily_ohlc = eurusd_m5[["open", "high", "low", "close"]].groupby(date_series).agg(
            {"open": "first", "high": "max", "low": "min", "close": "last"}
        )
        daily_adx = compute_adx(daily_ohlc, n=adx_period)["adx"].shift(1)
        adx_val = daily_adx.get(today, np.nan)
        if pd.isna(adx_val) or adx_val < min_adx:
            return None

    trend_ok_cont = t_val == direction
    trend_ok_rev = t_val == -direction
    cross_ok_cont = bool(c_val) if use_cross_filter else True
    cross_ok_rev = (not bool(c_val)) if use_cross_filter else True
    cont_pass = trend_ok_cont and cross_ok_cont
    rev_pass = trend_ok_rev and cross_ok_rev

    setup, d = None, 0
    if holds and cont_pass:
        setup, d = "continuation", direction
    elif (not holds) and rev_pass:
        setup, d = "reversal", -direction
    if setup is None:
        return None

    minutes = (eurusd_m5.index.hour * 60 + eurusd_m5.index.minute).to_numpy()
    dates_arr = berlin_idx.date
    high = eurusd_m5["high"].to_numpy()
    low = eurusd_m5["low"].to_numpy()
    close = eurusd_m5["close"].to_numpy()
    times = eurusd_m5.index
    cutoff_min = _minutes_of(entry_cutoff)
    entry_hour_min = int(ENTRY_HOUR * 60)

    day_mask = dates_arr == today
    if not day_mask.any():
        return None
    day_idx = np.where(day_mask)[0]
    day_start, day_end = int(day_idx[0]), int(day_idx[-1]) + 1

    entry_start_i = day_start
    while entry_start_i < day_end and minutes[entry_start_i] < entry_hour_min:
        entry_start_i += 1
    if entry_start_i >= day_end:
        return None

    if setup == "continuation":
        fractal_kind = "low" if direction == 1 else "high"
        search_start = entry_start_i
        pivot_i = None
        while True:
            candidate_pivot, _confirm_i = _first_fractal(high, low, minutes, search_start, day_end, cutoff_min, fractal_kind)
            if candidate_pivot is None:
                return None  # no confirmed fractal yet today
            still_outside = (
                (low[candidate_pivot] > row["asia_high"]) if direction == 1 else (high[candidate_pivot] < row["asia_low"])
            )
            if still_outside:
                pivot_i = candidate_pivot
                break
            search_start = candidate_pivot + 1
        trigger_level = high[pivot_i] if direction == 1 else low[pivot_i]
        sl_level = low[pivot_i] if direction == 1 else high[pivot_i]
    else:  # reversal
        half_asia_end_min, half_settle_end_min = int(ASIA_END * 60), int(SETTLE_END * 60)
        settle_mask_start = day_start
        while settle_mask_start < day_end and minutes[settle_mask_start] < half_asia_end_min:
            settle_mask_start += 1
        settle_mask_end = day_start
        while settle_mask_end < day_end and minutes[settle_mask_end] < half_settle_end_min:
            settle_mask_end += 1
        if settle_mask_end <= settle_mask_start:
            return None
        sweep_level = (
            high[settle_mask_start:settle_mask_end].max() if direction == 1 else low[settle_mask_start:settle_mask_end].min()
        )

        j = entry_start_i
        return_i = None
        while j < day_end and minutes[j] < cutoff_min:
            if row["asia_low"] < close[j] < row["asia_high"]:
                return_i = j
                break
            if direction == 1 and close[j] < row["asia_low"]:
                return None  # blew straight through - not a clean return
            if direction == -1 and close[j] > row["asia_high"]:
                return None
            j += 1
        if return_i is None:
            return None  # no return-into-range yet today

        fractal_kind = "low" if direction == 1 else "high"
        pivot_i, _confirm_i = _first_fractal(high, low, minutes, return_i, day_end, cutoff_min, fractal_kind)
        if pivot_i is None:
            return None  # returned into range, but no structure-shift fractal confirmed yet
        trigger_level = low[pivot_i] if direction == 1 else high[pivot_i]
        sl_level = sweep_level

    sl_dist = abs(trigger_level - sl_level)
    m5_atr = compute_atr(eurusd_m5, n=adr_period).to_numpy()
    atr_val = m5_atr[pivot_i] if pivot_i < len(m5_atr) else np.nan
    min_sl_dist = min_sl_atr_mult * atr_val if pd.notna(atr_val) else np.nan
    if sl_dist <= 0 or pd.isna(min_sl_dist) or sl_dist < min_sl_dist:
        return None

    adr = compute_adr(eurusd_m5, n=adr_period)
    adr_val = adr[day_start] if day_start < len(adr) else np.nan
    if pd.isna(adr_val) or adr_val <= 0:
        return None
    tp_dist = adr_mult * adr_val

    tp = trigger_level + tp_dist if d == 1 else trigger_level - tp_dist
    sl = trigger_level - sl_dist if d == 1 else trigger_level + sl_dist

    return {
        "date": today.isoformat(),
        "setup": setup,
        "direction": "long" if d == 1 else "short",
        "entry": float(trigger_level),
        "sl": float(sl),
        "tp": float(tp),
        "pivot_time": str(times[pivot_i]),
    }
