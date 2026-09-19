"""NY-Open ORB: signal frame assembly + the four entry mechanics + a shared
exit simulator.

Split into `find_entries` (per entry_type: WHEN/WHERE/WHICH direction a trade
triggers, one row per session at most - "one trade per day", matching the
classic ORB framing already used by orb_strategy/pipeline.py) and `simulate`
(a single shared bar-by-bar exit loop, keyed off those entry records, so the
stop/target/time-exit machinery isn't duplicated four times). All bar-level
work happens on the M5 execution frame produced by `build_frame`.

Entry mechanics (see knowledge/projects/ny-open-orb-sp500.md for rationale
and findings):

- stop_breakout: resting stop at orb_high/orb_low, intrabar fill at the
  level the moment M5 high/low crosses it (research_orb_intrabar_stop.py's
  intrabar-fill convention - a close-only check lets losses run too far
  past the trigger before a stop engine even sees them).
- confirmed_retest: first M5 BODY close beyond a level, then the first
  subsequent bar whose wick returns to retest that level, then the earliest
  bar (retest bar itself or the next one) whose close is back beyond the
  level again - modelled on scripts/research_london_range_bos_retest.py's
  breakout -> retest -> confirmation day-loop.
- limit_in_range: resting limits at BOTH orb_low (long) and orb_high
  (short) from the moment the range forms; whichever is touched first that
  day fires (a pure range-fade bet, no breakout precondition).
- fractal_reversal: bar-by-bar, no whole-day lookahead - if a confirmed
  breakout closes beyond either level FIRST, this entry type stands down
  for the rest of that day (that is now confirmed_retest's territory, kept
  disjoint on purpose). Otherwise, the first M5 fractal
  (gold_smc_htf_ltf.structure.detect_fractal_swings, k=2) that CONFIRMS with
  its extreme beyond a level (a wick-tested-but-never-closed-through level)
  fires a fade entry in the reversal direction.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gold_smc_htf_ltf.structure import detect_fractal_swings
from ny_open_orb.indicators import relative_volume_at_time
from ny_open_orb.range import attach_orb_levels, compute_session_range
from strategy.indicators import compute_adx

ENTRY_TYPES = ("stop_breakout", "close_breakout", "confirmed_retest", "limit_in_range", "fractal_reversal")


def build_frame(m15: pd.DataFrame, m_exec: pd.DataFrame, range_bars: int = 1, rvol_lookback_days: int = 20, fractal_k: int = 2) -> pd.DataFrame:
    """Assembles the execution frame (`m_exec` - M5 by default, but M1/M15
    work identically, see Stage 4's entry-timeframe sweep): opening-range
    levels (always from `m15`, per the strategy's own definition - only the
    EXECUTION granularity varies), the M15 ATR/ADX captured at the moment
    the range closes (broadcast constant per session - only bars already
    closed by range_end feed it, no lookahead), a fractal on `m_exec`
    (`fractal_k` - keep in mind a k-bar fractal spans a different real time
    window at M1 vs M5 vs M15), and RVOL@time computed on `m_exec`."""
    m15 = compute_adx(m15, n=14)  # also fills in 'atr' (Wilder ATR, same calc compute_atr would give)
    session_range = compute_session_range(m15, range_bars=range_bars)
    last_range_bar = session_range["range_end"] - pd.Timedelta(minutes=15)
    session_range["atr"] = m15["atr"].reindex(last_range_bar).to_numpy()
    session_range["adx"] = m15["adx"].reindex(last_range_bar).to_numpy()

    out = attach_orb_levels(m_exec, session_range)
    out["atr"] = out["session"].map(session_range["atr"])
    out["adx"] = out["session"].map(session_range["adx"])
    out = relative_volume_at_time(out, lookback_days=rvol_lookback_days)
    out = detect_fractal_swings(out, k=fractal_k)
    return out


def _tradeable_window(df: pd.DataFrame) -> pd.DataFrame:
    return df[df.index >= df["range_end"]]


def find_entries(
    df: pd.DataFrame, entry_type: str, confirm_within_bars: int = 6,
    entry_cutoff_minutes: float | None = None,
) -> pd.DataFrame:
    """entry_cutoff_minutes: if set, only bars within this many minutes of
    range_end are eligible to fire an entry (e.g. 60 = "only trade in the
    first hour after the range forms") - restricts session_close to
    range_end + cutoff for the purposes of entry-scanning only; exits in
    `simulate` still run to the full session_close regardless."""
    if entry_type not in ENTRY_TYPES:
        raise ValueError(f"unknown entry_type {entry_type!r}, expected one of {ENTRY_TYPES}")

    rows = []
    for session, day in _tradeable_window(df).groupby("session"):
        if day.empty or pd.isna(day["orb_high"].iloc[0]):
            continue
        cutoff = day["session_close"].iloc[0]
        if entry_cutoff_minutes is not None:
            cutoff = min(cutoff, day["range_end"].iloc[0] + pd.Timedelta(minutes=entry_cutoff_minutes))
        day = day[day.index < cutoff]
        if day.empty:
            continue

        entry = _find_entries_by_type[entry_type](day, confirm_within_bars)
        if entry is not None:
            rows.append(entry)

    cols = ["entry_time", "session", "direction", "entry_price", "orb_high", "orb_low", "orb_width", "atr"]
    entries = pd.DataFrame(rows, columns=cols)
    entries["entry_type"] = entry_type
    return entries


def _find_stop_breakout(day: pd.DataFrame, confirm_within_bars: int) -> dict | None:
    orb_high, orb_low = day["orb_high"].iloc[0], day["orb_low"].iloc[0]
    broke_up = day["high"] >= orb_high
    broke_down = day["low"] <= orb_low
    fires = (broke_up & ~broke_down) | (broke_down & ~broke_up)
    if not fires.any():
        return None
    i = day.index[fires][0]
    direction = 1 if broke_up.loc[i] else -1
    entry_price = orb_high if direction == 1 else orb_low
    return _entry_row(day, i, direction, entry_price)


def _find_confirmed_retest(day: pd.DataFrame, confirm_within_bars: int) -> dict | None:
    orb_high, orb_low = day["orb_high"].iloc[0], day["orb_low"].iloc[0]
    close = day["close"]
    broke_up = close > orb_high
    broke_down = close < orb_low
    breakout_mask = broke_up | broke_down
    if not breakout_mask.any():
        return None
    bo_i = day.index[breakout_mask][0]
    direction = 1 if broke_up.loc[bo_i] else -1
    level = orb_high if direction == 1 else orb_low

    after_bo = day.loc[day.index > bo_i]
    retest_mask = (after_bo["low"] <= level) if direction == 1 else (after_bo["high"] >= level)
    if not retest_mask.any():
        return None
    retest_i = after_bo.index[retest_mask][0]

    candidates = after_bo.loc[after_bo.index >= retest_i].iloc[:confirm_within_bars]
    confirm_mask = (candidates["close"] > level) if direction == 1 else (candidates["close"] < level)
    if not confirm_mask.any():
        return None
    confirm_i = candidates.index[confirm_mask][0]
    entry_price = candidates.loc[confirm_i, "close"]
    return _entry_row(day, confirm_i, direction, entry_price)


def _find_limit_in_range(day: pd.DataFrame, confirm_within_bars: int) -> dict | None:
    orb_high, orb_low = day["orb_high"].iloc[0], day["orb_low"].iloc[0]
    touch_low = day["low"] <= orb_low
    touch_high = day["high"] >= orb_high
    fires = touch_low | touch_high
    ambiguous = touch_low & touch_high
    fires = fires & ~ambiguous
    if not fires.any():
        return None
    i = day.index[fires][0]
    direction = 1 if touch_low.loc[i] else -1
    entry_price = orb_low if direction == 1 else orb_high
    return _entry_row(day, i, direction, entry_price)


def _find_fractal_reversal(day: pd.DataFrame, confirm_within_bars: int) -> dict | None:
    orb_high, orb_low = day["orb_high"].iloc[0], day["orb_low"].iloc[0]
    for i, bar in day.iterrows():
        if bar["close"] > orb_high or bar["close"] < orb_low:
            return None  # confirmed breakout happened first - not this variant's territory today
        if bar["swing_high_confirmed"] and bar["swing_high_price"] >= orb_high:
            return _entry_row(day, i, -1, bar["close"])
        if bar["swing_low_confirmed"] and bar["swing_low_price"] <= orb_low:
            return _entry_row(day, i, 1, bar["close"])
    return None


def _find_close_breakout(day: pd.DataFrame, confirm_within_bars: int) -> dict | None:
    """Wie _find_stop_breakout, aber mit BESTAETIGUNG durch den Bar-Schluss
    statt intrabar am Level (2026-09-14, Nutzerfrage nach dem Candle-Close-
    Mechanismus).

    Unterschied in einem Satz: stop_breakout stellt eine ruhende Order ins
    Buch und wird gefuellt, sobald der Kurs das Level beruehrt --
    close_breakout wartet ab, ob die Bar JENSEITS des Levels schliesst, und
    steigt dann zu deren Schlusskurs ein.

    Der Tausch dahinter: man filtert Fehlausbruche heraus (eine Bar, die das
    Level nur anpiekst und darunter schliesst, feuert hier nicht), bezahlt
    dafuer aber den Weg vom Level bis zum Bar-Schluss. Der ist gemessen und
    nicht klein -- 6-18 % der Stopdistanz im Median, je Instrument
    (scripts/research_orb_cost_probe.py).

    Keine Mehrdeutigkeit noetig: ein Schlusskurs liegt entweder ueber oder
    unter dem Level, nie beides -- anders als bei high/low, wo eine Bar beide
    Seiten beruehren kann und stop_breakout deshalb einen ~-Filter braucht."""
    orb_high, orb_low = day["orb_high"].iloc[0], day["orb_low"].iloc[0]
    close = day["close"]
    broke_up = close > orb_high
    broke_down = close < orb_low
    fires = broke_up | broke_down
    if not fires.any():
        return None
    i = day.index[fires][0]
    direction = 1 if broke_up.loc[i] else -1
    return _entry_row(day, i, direction, float(close.loc[i]))


def _entry_row(day: pd.DataFrame, i: pd.Timestamp, direction: int, entry_price: float) -> dict:
    return {
        "entry_time": i,
        "session": day["session"].iloc[0],
        "direction": direction,
        "entry_price": entry_price,
        "orb_high": day["orb_high"].iloc[0],
        "orb_low": day["orb_low"].iloc[0],
        "orb_width": day["orb_width"].iloc[0],
        "atr": day["atr"].iloc[0],
    }


_find_entries_by_type = {
    "stop_breakout": _find_stop_breakout,
    "close_breakout": _find_close_breakout,
    "confirmed_retest": _find_confirmed_retest,
    "limit_in_range": _find_limit_in_range,
    "fractal_reversal": _find_fractal_reversal,
}


def simulate(
    df: pd.DataFrame,
    entries: pd.DataFrame,
    stop_atr_mult: float = 1.5,
    stop_mode: str = "atr",
    target_mode: str | None = "r_multiple",
    target_r_mult: float = 4.0,
    target_range_mult: float = 2.0,
    breakeven_trigger_r: float | None = None,
    partial_exit_r: float | None = None,
    partial_exit_fraction: float = 0.5,
    move_stop_to_be_after_partial: bool = False,
    rvol_exit_min: float | None = None,
    spread_bps: float = 0.5,
    slippage_bps: float = 0.0,
    entry_slippage_bps: float = 0.0,
    entry_lag_bars: int = 0,
    entry_fill_mode: str = "level",
    reanchor_stop_to_fill: bool = False,
    partial_check: str = "intrabar",
) -> pd.DataFrame:
    """Shared exit loop for every entry_type. Stop is checked intrabar
    (high/low, filled at the stop level - see research_orb_intrabar_stop.py's
    finding that a close-only check lets losses overshoot); target/time/RVOL
    exits are checked on the close, like the rest of this repo's engines.

    stop_mode="atr": stop = entry -/+ stop_atr_mult * atr.
    stop_mode="structural": opposite ORB boundary if that's actually beyond
    entry in the risk-reducing direction, else falls back to the ATR stop
    (covers the two range-fade entry types, where "opposite boundary" isn't
    always further from entry than a sane minimum stop).
    breakeven_trigger_r: once a bar's CLOSE shows favour >= this many R
    (initial entry-to-stop distance), the stop ratchets to entry_price
    (once, never loosens) - same convention/field name as
    strategy/backtest.py::BacktestConfig. None = disabled (default).

    partial_exit_r: once price reaches this many R in favour (checked
    intrabar, like the stop/target), `partial_exit_fraction` of the
    position banks its profit there; the rest keeps running against the
    ORIGINAL stop/target unless `move_stop_to_be_after_partial=True` moves
    the remainder's stop to entry_price at that moment (a targeted,
    partial-position breakeven - deliberately distinct from
    `breakeven_trigger_r`, which moves the WHOLE position and was found to
    hurt this strategy's expectancy, see knowledge/). None = disabled
    (default, unchanged prior behaviour). Reported `exit_reason` is always
    the reason the REMAINING fraction finally closed for - `r_multiple`/
    `return_pct` are fraction-weighted across both legs.
    """
    if entries.empty:
        return pd.DataFrame()

    half_cost = spread_bps / 10_000 / 2
    exit_slip = slippage_bps / 10_000
    entry_slip = entry_slippage_bps / 10_000
    trades = []
    for _, e in entries.iterrows():
        if pd.isna(e["atr"]) or e["atr"] <= 0:
            continue  # ATR(14) warm-up period at the start of the series - not enough history to size a stop yet
        direction = e["direction"]

        # Signalpreis = das Ausbruchslevel. Der Stop haengt IMMER hieran, auch
        # bei verzoegerter Ausfuehrung -- genau so macht es die Live-Bridge:
        # Funded-Portfolio-Bridge/run_once.py::_sl_price() rekonstruiert den SL
        # als entry_price - direction * initial_risk aus dem SIGNAL, nicht aus
        # dem tatsaechlichen Fuellpreis.
        signal_price = e["entry_price"] * (1 + half_cost * direction)

        # entry_lag_bars > 0: fuellen zum SCHLUSSKURS `lag` Baren spaeter statt
        # am Ausbruchslevel. Der Backtest unterstellte bisher eine Fuellung
        # exakt am Level -- der Live-Bot schickt aber eine MARKTorder beim
        # naechsten Scan (place_market_entry(), target=None). Bei einer
        # Ausbruchsstrategie ist diese Verzoegerung per Konstruktion
        # nachteilig, weil der Kurs im Ausbruch weiterlaeuft.
        # 0 = bisheriges Verhalten, bit-identisch.
        # Drei unterscheidbare Ausfuehrungsmechanismen:
        #   entry_fill_mode="level"     -> ruhende Stop-Order: Fuellung AM Level,
        #                                  intrabar, kein Versatz. Das ist der
        #                                  Mechanismus, den diese Strategie
        #                                  validiert hat (siehe Modul-Docstring).
        #   entry_fill_mode="bar_close" -> Marktorder, sobald der Bot die Bar
        #                                  sieht. entry_lag_bars=0 heisst
        #                                  "Schlusskurs der SIGNALbar" (EK sendet
        #                                  real 3-14 s danach), 1 heisst eine Bar
        #                                  spaeter (Funded-Pipeline ~3:15 Min).
        if entry_fill_mode not in ("level", "bar_close"):
            raise ValueError(f"entry_fill_mode must be 'level' or 'bar_close', got {entry_fill_mode!r}")
        if entry_fill_mode == "bar_close":
            try:
                fill_i = df.index.get_loc(e["entry_time"]) + entry_lag_bars
            except KeyError:
                continue
            if fill_i >= len(df) or df.index[fill_i] > df.loc[e["entry_time"], "session_close"]:
                continue  # Ausfuehrung faellt aus der Session -- live kaeme der Trade nicht zustande
            raw_fill = float(df["close"].iloc[fill_i])
            path_start = df.index[fill_i]
        elif entry_lag_bars > 0:
            try:
                fill_i = df.index.get_loc(e["entry_time"]) + entry_lag_bars
            except KeyError:
                continue
            if fill_i >= len(df) or df.index[fill_i] > df.loc[e["entry_time"], "session_close"]:
                continue
            raw_fill = float(df["close"].iloc[fill_i])
            path_start = df.index[fill_i]
        else:
            raw_fill = e["entry_price"]
            path_start = e["entry_time"]

        # Kosten am Entry: halber Spread PLUS Einstiegs-Slippage, beide gegen uns.
        entry_price = raw_fill * (1 + (half_cost + entry_slip) * direction)

        # reanchor_stop_to_fill: Stop am tatsaechlichen Fuellpreis aufhaengen
        # statt am Signal. Der Risiko-Abstand ist dann IMMER exakt
        # stop_atr_mult x ATR, unabhaengig vom Versatz.
        #
        # Warum das hier anders zu bewerten ist als bei cls_practical: dort
        # kostete dasselbe Vorgehen Ergebnis, weil der CLS-Stop auf einem
        # STRUKTURELLEN Invalidierungs-Niveau sitzt und dieses Niveau den Edge
        # traegt (siehe knowledge/projects/cls-practical-kostenvalidierung.md).
        # Der ORB-Stop im stop_mode="atr" ist dagegen eine reine
        # Volatilitaets-DISTANZ ohne eigene Bedeutung -- ihn mitwandern zu
        # lassen wirft also kein strukturelles Niveau weg.
        # (Fuer stop_mode="structural" gilt das NICHT: dort ist orb_low/orb_high
        # ein echtes Niveau und bleibt deshalb unangetastet.)
        stop_anchor = entry_price if reanchor_stop_to_fill else signal_price
        atr_stop = stop_anchor - direction * stop_atr_mult * e["atr"]
        if stop_mode == "structural":
            structural = e["orb_low"] if direction == 1 else e["orb_high"]
            beyond = (structural < entry_price) if direction == 1 else (structural > entry_price)
            stop_price = structural if beyond else atr_stop
        else:
            stop_price = atr_stop
        # Fill bereits JENSEITS des Stops (nur bei entry_lag_bars > 0 moeglich):
        # Der Trade kaeme live gar nicht zustande -- das Restlaufzeit-Gate der
        # Bridges ("SL schon beruehrt") blockt ihn. Rechnerisch ist er ausserdem
        # giftig: abs() unten macht aus dem negativen Abstand ein positives
        # Risiko, der Stop-Exit liefert dann ein POSITIVES r_multiple und ein
        # toter Trade erscheint als Gewinn. Genau das hat am 2026-09-14 die
        # Lag-Auswertung verfaelscht (Marktorder mit 10 Min Versatz sah besser
        # aus als mit 5 Min -- oekonomisch unmoeglich).
        # Bei entry_lag_bars=0 kann der Fall nicht eintreten (Fill == Signal,
        # Stop liegt stop_atr_mult x ATR entfernt), der Default-Pfad bleibt
        # dadurch unveraendert.
        if (entry_price - stop_price) * direction <= 0:
            continue
        initial_risk = abs(entry_price - stop_price)
        if initial_risk <= 0:
            continue

        if target_mode == "r_multiple":
            target_price = entry_price + direction * target_r_mult * initial_risk
        elif target_mode == "range_multiple":
            target_price = entry_price + direction * target_range_mult * e["orb_width"]
        else:
            target_price = None

        partial_level = None
        if partial_exit_r is not None:
            partial_level = entry_price + direction * partial_exit_r * initial_risk

        session_close = df.loc[e["entry_time"], "session_close"]
        # ab dem tatsaechlichen Fuellzeitpunkt, nicht ab der Signalbar
        path = df.loc[(df.index > path_start) & (df.index <= session_close)]

        exit_i, exit_reason, exit_price = None, None, None
        be_moved = False
        partial_done = False
        partial_ret_contribution = 0.0
        partial_r_contribution = 0.0
        remaining_fraction = 1.0
        for j, bar in path.iterrows():
            if breakeven_trigger_r is not None and not be_moved:
                favor = direction * (bar["close"] - entry_price)
                if favor >= breakeven_trigger_r * initial_risk:
                    stop_price = entry_price
                    be_moved = True
            hit_stop = (bar["low"] <= stop_price) if direction == 1 else (bar["high"] >= stop_price)
            if hit_stop:
                exit_i, exit_reason, exit_price = j, ("breakeven" if be_moved else "stop"), stop_price
                break
            if partial_level is not None and not partial_done:
                # partial_check="close" bildet einen GEPOLLTEN Teilausstieg nach:
                # die Live-Bridge prueft das Level nur alle 5 Minuten gegen den
                # aktuellen Kurs, nicht intrabar -- eine Spitze, die das Level
                # beruehrt und in derselben Bar zurueckfaellt, sieht sie nicht.
                # "intrabar" (Default) = bisheriges Verhalten, bit-identisch.
                if partial_check == "close":
                    hit_partial = (bar["close"] >= partial_level) if direction == 1 else (bar["close"] <= partial_level)
                else:
                    hit_partial = (bar["high"] >= partial_level) if direction == 1 else (bar["low"] <= partial_level)
                if hit_partial:
                    # Teilausstieg ist eine Marktorder der Bridge -- halber Spread UND Slippage
                    partial_fill = partial_level * (1 - (half_cost + exit_slip) * direction)
                    partial_ret_contribution = partial_exit_fraction * direction * (partial_fill - entry_price) / entry_price
                    partial_r_contribution = partial_exit_fraction * direction * (partial_fill - entry_price) / initial_risk
                    remaining_fraction = 1.0 - partial_exit_fraction
                    partial_done = True
                    if move_stop_to_be_after_partial:
                        stop_price = entry_price
                    continue  # remaining fraction keeps running - re-check stop/target on later bars
            if target_price is not None:
                hit_target = (bar["high"] >= target_price) if direction == 1 else (bar["low"] <= target_price)
                if hit_target:
                    exit_i, exit_reason, exit_price = j, "target", target_price
                    break
            if rvol_exit_min is not None and bar.get("rvol_at_time", np.nan) < rvol_exit_min:
                exit_i, exit_reason, exit_price = j, "rvol_fade", bar["close"]
                break
        if exit_i is None:
            if path.empty:
                continue
            exit_i, exit_reason, exit_price = path.index[-1], "session_end", path["close"].iloc[-1]

        # Alle Ausstiege dieses Beins sind in der Praxis Marktorders: der Broker-SL
        # slippt beim Ausloesen, und ein Ziel-/Session-Ende-Ausstieg laeuft ueber eine
        # Marktorder der Bridge (place_market_entry() setzt target=None). Deshalb
        # traegt JEDER Ausstieg halben Spread plus Slippage, nicht nur der Stop.
        exit_price = exit_price * (1 - (half_cost + exit_slip) * direction)
        final_leg_ret = direction * (exit_price - entry_price) / entry_price
        final_leg_r = direction * (exit_price - entry_price) / initial_risk
        ret = partial_ret_contribution + remaining_fraction * final_leg_ret
        r_multiple = partial_r_contribution + remaining_fraction * final_leg_r
        trades.append({
            "entry_time": e["entry_time"], "exit_time": exit_i, "direction": direction,
            "entry_price": entry_price, "exit_price": exit_price, "return_pct": ret,
            "exit_reason": exit_reason, "hold_bars": path.index.get_loc(exit_i) + 1 if exit_i in path.index else np.nan,
            "initial_risk": initial_risk, "r_multiple": r_multiple, "had_partial_exit": partial_done,
            "adx_at_entry": df.loc[e["entry_time"], "adx"], "atr_at_entry": e["atr"],
        })

    return pd.DataFrame(trades)
