"""London-CLS-Fenster-Breakout - EUR/USD-Variante, User-Idee (2026-08-07),
konzeptionell verwandt mit `cls_squeeze.py` und `cls_advanced.py` (gleiche
CLS-Settlement-Fenster-Herkunft), aber ein eigener, dritter Ansatz: statt
Reversion/Momentum auf das VWAP-Signal oder einer Cross-Pair-Bestätigung zu
handeln, wird hier die Range aus dem KOMBINIERTEN Pre-Settle+Settle+Test-
Fenster (06:00-09:30 Berlin-Zeit, deckungsgleich mit den drei Teilfenstern
aus cls_advanced.py) direkt als Ausbruchs-Range gehandelt - dieselbe
Grundkonstruktion wie `asian_range_breakout/cls_settle.py`, hier auf
EUR/USD statt Gold und mit einer strengeren Ausbruchs-Bestätigung.

Ausbruchs-Bestätigung (explizite User-Vorgabe, bewusst strenger als ein
einfacher Stop-Order-Fill auf der ersten Berührung): eine Kerze muss
außerhalb der Range SCHLIESSEN (Kandidat), UND die darauffolgende Kerze muss
ebenfalls noch außerhalb schließen - erst dann gilt der Ausbruch als
bestätigt, Entry zum Schlusskurs dieser zweiten Kerze. Eine Kandidaten-Kerze,
die von der Folgekerze wieder eingeholt wird, verwirft den Kandidaten
(Fehlausbruch); die Folgekerze wird dabei selbst sofort wieder als neuer
Kandidat geprüft, statt eine Bar zu verlieren. Kein literales Resting-Stop-
Order-Fill-Modell (inkompatibel mit einer Zwei-Kerzen-Bestätigung, die erst
nach Schluss der zweiten Kerze feststeht) - bewusste Vereinfachung für einen
schnellen, händischen Erstcheck, wie in diesem Projekt üblich.

Entry nur bis `entry_cutoff` gültig (User: 13:00 Berlin) - kein Ausbruch
mehr nach diesem Zeitpunkt, auch wenn die Range selbst nur bis 09:30 offen
war. SL = atr_mult x ATR(atr_period) auf M15 direkt (kein Resampling, User:
"M15 ATR Band"), kausal geshiftet (Wert des zuletzt VOLLSTÄNDIG
geschlossenen Bars). TP = fix 1:2 R (User-Vorgabe "für den Anfang, ganz
simpel"). BE-Move bei 1R (User-Vorgabe, gleiche Konvention wie
`asian_range_breakout/engine.py`'s be_trigger_r - pro Bar wird BE zuerst
geprüft, dann Stop, ein Bar der BE erreicht und im selben Bar hart
zurückdreht scratcht bei Breakeven statt den weiteren Original-Stop zu
bankieren)."""

import numpy as np
import pandas as pd

from strategy.indicators import compute_atr
from strategy.real_data import fetch_pair_history


def fetch_eurusd_m15_berlin(start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    df = fetch_pair_history("EURUSD", start, end, force_refresh=force_refresh)
    df.index = df.index.tz_convert("Europe/Berlin")
    return df


def _minutes(index: pd.DatetimeIndex) -> np.ndarray:
    return (index.hour * 60 + index.minute).to_numpy()


def _minutes_of(hhmm: str) -> int:
    t = pd.Timestamp(hhmm)
    return t.hour * 60 + t.minute


def simulate_london_cls_breakout(
    df: pd.DataFrame,
    range_start: str = "06:00",
    range_end: str = "09:30",
    entry_cutoff: str = "13:00",
    atr_mult: float = 1.0,
    atr_period: int = 14,
    tp_r_mult: float = 2.0,
    be_trigger_r: float | None = 1.0,
    spread_bps: float = 0.3,
    confirm_bars: int = 2,
) -> pd.DataFrame:
    """confirm_bars: Anzahl aufeinanderfolgender Kerzen, die außerhalb der
    Range SCHLIESSEN müssen, bevor der Ausbruch als bestätigt gilt (Entry
    zum Schlusskurs der letzten davon). confirm_bars=1 = keine Bestätigung,
    Entry direkt auf der ersten Ausbruchskerze (naives Stop-Order-Verhalten
    auf Basis von Kerzenschlüssen, nicht Intrabar-Touch). confirm_bars=2 ist
    die ursprüngliche User-Vorgabe (2026-08-07)."""
    required = {"open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"simulate_london_cls_breakout: missing columns {missing}")

    start_min = _minutes_of(range_start)
    end_min = _minutes_of(range_end)
    cutoff_min = _minutes_of(entry_cutoff)
    minutes = _minutes(df.index)
    in_window = (minutes >= start_min) & (minutes < end_min)

    atr = compute_atr(df, n=atr_period).shift(1).to_numpy()

    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    times = df.index
    n = len(df)
    half_cost_frac = spread_bps / 10_000 / 2

    trades = []
    i = 0
    while i < n:
        while i < n and not in_window[i]:
            i += 1
        if i >= n:
            break
        window_start = i
        while i < n and in_window[i]:
            i += 1
        window_end = i  # exklusiv - erster Bar NICHT mehr im Fenster (Range gerade geschlossen)
        if window_end >= n:
            break

        r_hi = high[window_start:window_end].max()
        r_lo = low[window_start:window_end].min()
        if r_hi - r_lo <= 0:
            continue

        # --- Ausbruchs-Suche mit N-Kerzen-Bestätigung (confirm_bars), bis entry_cutoff (selber Kalendertag) ---
        window_day = times[window_end].normalize()
        entry_i, direction = None, 0
        pending_dir, streak = 0, 0
        j = window_end
        while j < n and times[j].normalize() == window_day and minutes[j] < cutoff_min:
            c = close[j]
            beyond_hi = c > r_hi
            beyond_lo = c < r_lo
            if pending_dir == 1 and not beyond_hi:
                pending_dir, streak = 0, 0
            elif pending_dir == -1 and not beyond_lo:
                pending_dir, streak = 0, 0

            if pending_dir == 0:
                if beyond_hi:
                    pending_dir, streak = 1, 1
                elif beyond_lo:
                    pending_dir, streak = -1, 1
            else:
                streak += 1

            if pending_dir != 0 and streak >= confirm_bars:
                entry_i, direction = j, pending_dir
                break
            j += 1

        if entry_i is None:
            i = j
            continue

        this_atr = atr[entry_i]
        if np.isnan(this_atr) or this_atr <= 0:
            i = entry_i + 1
            continue

        raw_entry = close[entry_i]
        sl_dist = atr_mult * this_atr
        entry_price = raw_entry * (1 + half_cost_frac) if direction == 1 else raw_entry * (1 - half_cost_frac)
        sl = raw_entry - sl_dist if direction == 1 else raw_entry + sl_dist
        tp = raw_entry + tp_r_mult * sl_dist if direction == 1 else raw_entry - tp_r_mult * sl_dist
        be_trigger_price = None
        if be_trigger_r is not None:
            be_trigger_price = (
                raw_entry + be_trigger_r * sl_dist if direction == 1 else raw_entry - be_trigger_r * sl_dist
            )

        # --- Position von entry_i+1 an verwalten: BE-Check zuerst, dann Stop, dann TP, dann Datenende ---
        current_sl = sl
        be_moved = False
        exit_i, exit_price, exit_reason = None, None, None
        k = entry_i + 1
        while k < n:
            if not be_moved and be_trigger_price is not None:
                reached_be = (high[k] >= be_trigger_price) if direction == 1 else (low[k] <= be_trigger_price)
                if reached_be:
                    current_sl = raw_entry
                    be_moved = True

            hit_stop = (low[k] <= current_sl) if direction == 1 else (high[k] >= current_sl)
            hit_tp = (high[k] >= tp) if direction == 1 else (low[k] <= tp)
            if hit_stop:
                exit_price = current_sl * (1 - half_cost_frac) if direction == 1 else current_sl * (1 + half_cost_frac)
                exit_i, exit_reason = k, ("breakeven" if be_moved else "stop")
                break
            if hit_tp:
                exit_price = tp * (1 - half_cost_frac) if direction == 1 else tp * (1 + half_cost_frac)
                exit_i, exit_reason = k, "take_profit"
                break
            k += 1

        if exit_i is None:
            exit_price = close[n - 1] * (1 - half_cost_frac) if direction == 1 else close[n - 1] * (1 + half_cost_frac)
            exit_i, exit_reason = n - 1, "data_end"

        return_pct = (
            (exit_price - entry_price) / entry_price
            if direction == 1
            else (entry_price - exit_price) / entry_price
        )
        trades.append(
            {
                "window_start": times[window_start],
                "window_end": times[window_end],
                "entry_time": times[entry_i],
                "exit_time": times[exit_i],
                "direction": "long" if direction == 1 else "short",
                "entry_price": entry_price,
                "exit_price": exit_price,
                "sl": sl,
                "tp": tp,
                "range_high": r_hi,
                "range_low": r_lo,
                "range_width": r_hi - r_lo,
                "atr_at_entry": this_atr,
                "return_pct": return_pct,
                "hold_bars": exit_i - entry_i,
                "exit_reason": exit_reason,
            }
        )
        i = exit_i + 1

    return pd.DataFrame(trades)
