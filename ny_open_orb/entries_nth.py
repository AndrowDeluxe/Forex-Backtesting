"""ORB-Einstiege jenseits des ersten Ausbruchs (Nutzerauftrag 2026-10-06).

Modi (alle auf M1/M5-Ausfuehrungsbars nach `range_end`, ein Trade je Tag):
  first       erster Ausbruch (identisch mit find_live_entries(rule="none"))
  nth_same    N-ter Bruch derselben Seite; zwischen zwei Bruechen muss ein
              Schlusskurs zurueck in [orb_low, orb_high] liegen
  after_fail  Bruch einer Seite, nachdem die GEGENseite gebrochen und per
              Schlusskurs in die Range zurueckgekehrt ist
  fade        gegen den ersten Ausbruch (Opening-Range-Reversal, Ladia 2026):
              Einstieg am Level in Gegenrichtung
  retest      nach dem ersten Bruch einer Seite der Ruecklauf zum Level
              (Limit am Level, Richtung des Ausbruchs); faellt aus, wenn vorher
              die Gegenseite der Range gebrochen wird

`allowed[session]` enthaelt die erlaubten TRADE-Richtungen (+1/-1). `cutoff`
("HH:MM", NY) ist der spaeteste Einstieg. Beruehren beide Seiten dieselbe Bar
(Reihenfolge unbekannt), wird der Tag uebersprungen -- dieselbe Konvention
wie find_live_entries.

Ausgabe: gleiche Spalten wie scripts/research_orb_cancel_at_sl_and_hold.py::
find_live_entries, damit research_orb_exit_grid_m1.prepare()/sim() direkt
weiterrechnen (entry_price = Level; direction = Trade-Richtung).
"""
from __future__ import annotations

import pandas as pd

MODES = ("first", "nth_same", "after_fail", "fade", "retest")
COLS = ["entry_time", "session", "direction", "entry_price", "orb_high", "orb_low", "orb_width", "atr"]


def _day_entry(highs, lows, closes, times_min, hi, lo, dirs, mode, n, cutoff_min):
    """Index k und Richtung des Einstiegs, oder None."""
    breaks = {1: 0, -1: 0}          # Anzahl Brueche je Seite
    armed = {1: True, -1: True}     # Seite darf (wieder) brechen
    failed = {1: False, -1: False}  # Seite brach und kehrte per Schluss in die Range zurueck
    first_side = None               # Seite des ersten Bruchs (fade/retest)
    for k in range(len(highs)):
        if times_min[k] >= cutoff_min:
            return None
        h, l, c = highs[k], lows[k], closes[k]
        up, dn = h >= hi, l <= lo

        if mode == "first":   # exakt find_live_entries(rule="none"): nur erlaubte Seiten, Doppel-Bar wird uebersprungen
            touched = [s for s in dirs if (s == 1 and up) or (s == -1 and dn)]
            if len(touched) == 1:
                return k, touched[0]
            continue

        if mode == "retest" and first_side is not None:
            s = first_side
            if (s == 1 and dn) or (s == -1 and up):
                return None                       # Gegenseite zuerst -> verworfen
            if (s == 1 and l <= hi) or (s == -1 and h >= lo):
                return (k, s) if s in dirs else None
            continue

        if up and dn:
            return None                           # beide Seiten in einer Bar
        side = 1 if (up and armed[1]) else (-1 if (dn and armed[-1]) else None)
        if side is not None:
            breaks[side] += 1
            armed[side] = False
            if mode == "nth_same":
                if breaks[side] == n and side in dirs:
                    return k, side
            elif mode == "after_fail":
                if failed[-side] and side in dirs:
                    return k, side
            elif mode == "fade":
                return (k, -side) if -side in dirs else None
            elif mode == "retest" and first_side is None:
                first_side = side
                continue
        # zurueck in die Range per Schlusskurs -> Seite wieder scharf
        if lo <= c <= hi:
            for s_ in (1, -1):
                if not armed[s_]:
                    armed[s_] = True
                    failed[s_] = True
    return None


def find_entries_nth(frame: pd.DataFrame, allowed: dict, mode: str, n: int = 2, cutoff: str = "16:00") -> pd.DataFrame:
    if mode not in MODES:
        raise ValueError(f"unbekannter Modus {mode!r}, erwartet {MODES}")
    hh, mm = (int(x) for x in cutoff.split(":"))
    cutoff_min = hh * 60 + mm
    rows = []
    tw = frame[frame.index >= frame["range_end"]]
    for session, day in tw.groupby("session"):
        dirs = allowed.get(pd.Timestamp(session), [])
        if not dirs or day.empty or pd.isna(day["orb_high"].iloc[0]):
            continue
        day = day[day.index < day["session_close"].iloc[0]]
        if day.empty:
            continue
        hi, lo, atr = day["orb_high"].iloc[0], day["orb_low"].iloc[0], day["atr"].iloc[0]
        if pd.isna(atr) or atr <= 0:
            continue
        idx = day.index
        times_min = (idx.hour * 60 + idx.minute).to_numpy()
        res = _day_entry(day["high"].to_numpy(), day["low"].to_numpy(), day["close"].to_numpy(), times_min,
                         hi, lo, list(dirs), mode, n, cutoff_min)
        if res is None:
            continue
        k, d = res
        if mode == "fade":
            level = lo if d == 1 else hi          # Fade: long am Range-Tief, short am Range-Hoch
        else:
            level = hi if d == 1 else lo
        rows.append({"entry_time": idx[k], "session": session, "direction": d, "entry_price": level,
                     "orb_high": hi, "orb_low": lo, "orb_width": day["orb_width"].iloc[0], "atr": atr})
    out = pd.DataFrame(rows, columns=COLS)
    out["entry_type"] = mode if mode != "nth_same" else f"nth_same_{n}"
    return out
