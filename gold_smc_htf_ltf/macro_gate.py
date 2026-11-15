"""Makro-Sperre fuer ctnl_reversal: kein Trade gegen den Gold-MACRO-Block.

EINE Stelle fuer alle drei Bridges -- dasselbe Argument wie bei `spike_gate`/`ribbon_gate`/
`ctnl_kill_switch` (Memory `three_bridges_not_same_state`).

WAS ES TUT
MACRO-Block (Realzins 10J, USD, Breakeven 10J, EPU; je 3-Jahres-Perzentil 0..100, hoch = bullisch
fuer Gold) vom letzten Handelstag VOR dem Entry-Tag (UTC):
  MACRO <= 35 -> kein Long,  MACRO >= 65 -> kein Short,  dazwischen alles erlaubt.

WARUM (Nutzerentscheid 2026-11-15, knowledge/projects/gold-confirmation-score.md)
Gesperrte Trades IS -0,69 R (n 109), OOS -0,75 R (n 69), Tresor -1,16 R (n 5); Long- und Short-
Seite einzeln negativ. Gegengeprueft auf dem Live-Set (Ribbon + Spike), siehe Projekt-Notiz.

BEREITS GETRACKTE SIGNALE BLEIBEN IMMER DRIN (wie spike_gate): nur NEUE Entries werden gefiltert.

FAIL-SAFE: DURCHLASSEN, NICHT BLOCKIEREN (wie ctnl_kill_switch). Ist der MACRO-Wert aelter als
MAX_STALE_DAYS Kalendertage oder fehlt die Datei, wird durchgelassen und gemeldet. Begruendung: die
Sperre trifft nur ~1 von 8 Trades; ein Datenausfall soll das Bein nicht still abschalten.
Daten: taeglicher Task `python -m fusion_lab.gold_confirm.refresh`.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

import pandas as pd

LONG_MIN, SHORT_MAX = 65.0, 35.0
GATED_LEGS = {"ctnl_reversal"}
MAX_STALE_DAYS = 5
FRAME = Path(__file__).resolve().parents[1] / "fusion_lab" / "data" / "gold_confirm" / "score_frame.parquet"
_TTL_S = 600.0
_cache: dict[str, tuple[float, pd.Series]] = {}


def _series() -> pd.Series:
    hit = _cache.get("macro")
    if hit and time.time() - hit[0] < _TTL_S:
        return hit[1]
    s = pd.read_parquet(FRAME, columns=["MACRO"])["MACRO"].dropna() * 100
    _cache["macro"] = (time.time(), s)
    return s


def _day(t) -> pd.Timestamp:
    t = pd.Timestamp(t)
    if t.tzinfo is not None:
        t = t.tz_convert("UTC").tz_localize(None)
    return t.normalize()


def value(entry_time) -> tuple[float | None, pd.Timestamp | None]:
    """(MACRO 0..100, Datum des Werts) vom letzten Handelstag vor dem Entry-Tag; (None, None) ohne Daten."""
    try:
        s = _series()
    except Exception:  # noqa: BLE001
        return None, None
    prior = s.loc[: _day(entry_time) - pd.Timedelta(days=1)]
    if prior.empty:
        return None, None
    return float(prior.iloc[-1]), prior.index[-1]


def decide(direction: int, entry_time) -> tuple[bool, str]:
    """(erlaubt?, Grund). direction +1 long / -1 short."""
    v, stand = value(entry_time)
    if v is None or (_day(entry_time) - stand).days > MAX_STALE_DAYS:
        return True, f"MACRO-Daten fehlen/veraltet (Stand {stand.date() if stand is not None else '-'}) -- durchgelassen"
    if direction > 0 and v <= SHORT_MAX:
        return False, f"Long gegen MACRO {v:.0f} (<= {SHORT_MAX:g})"
    if direction < 0 and v >= LONG_MIN:
        return False, f"Short gegen MACRO {v:.0f} (>= {LONG_MIN:g})"
    return True, ""


def filter_trades(trades: pd.DataFrame, is_tracked: Callable[[pd.Series], bool],
                  *, leg: str = "ctnl_reversal") -> tuple[pd.DataFrame, str]:
    """(gefilterte Tabelle, Log-Zeile). Getrackte Zeilen bleiben immer."""
    if trades is None or trades.empty:
        return trades, ""
    keep, gesperrt, stale = [], 0, 0
    for _, r in trades.iterrows():
        if is_tracked(r):
            keep.append(True)
            continue
        d = r.get("direction", 1)
        ok, grund = decide(int(d) if pd.notna(d) else 1, r["entry_time"])
        keep.append(ok)
        gesperrt += not ok
        stale += ok and "veraltet" in grund
    teile = []
    if gesperrt:
        teile.append(f"{gesperrt} gegen MACRO gesperrt (Regel, kein Fehler)")
    if stale:
        teile.append(f"{stale} ohne aktuellen MACRO-Wert DURCHGELASSEN -- Refresh-Task pruefen")
    hinweis = f"{leg}: Makro-Sperre behaelt {sum(keep)} von {len(trades)}; " + "; ".join(teile) if teile else ""
    return trades[pd.Series(keep, index=trades.index)], hinweis
