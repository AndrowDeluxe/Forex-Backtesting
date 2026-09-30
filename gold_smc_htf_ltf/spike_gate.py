"""Signalkerzen-Filter fuer ctnl_reversal: nur Signale mit echter Groesse.

EINE Stelle fuer alle drei Bridges -- dasselbe Argument wie bei
`ribbon_gate`/`ctnl_kill_switch` (Memory `three_bridges_not_same_state`).

WAS ES TUT
Die M15-Signalbar muss eine Range von mindestens SPIKE_MIN_ATR x ATR haben
(Spalte `atr` des Reversal-Frames). Kleinere Signalbars -- das langsame
"Hochschleichen" ohne echten Liquidity-Spike -- werden nicht gehandelt.

WARUM (Nutzerentscheid 2026-09-30, knowledge/projects/ctnl-kostenvalidierung.md
Befund 18/19, scripts/research_ctnl_confirm_wf.py)
Anlass war die Short-Serie 29./30.09.: 5 der 6 Verlierer hatten eine
Signalbar unter 0,75 ATR. Ribbon-konform, am realen Betriebspunkt, 2016-2026:
risikoadjustierter Anker-Walk-Forward waehlt 0,75 in 8 von 8 Jahren; OOS
SigmaR -9 % (+242,7 gegen +267,3), MaxDD -28,5R statt -33,9R; volle Historie
Sharpe 1,08 statt 0,95, P(MaxDD>6 %) 18,4 % statt 43,5 %, kleinerer DD in
10 von 11 Jahren. Shorts mit kleiner Signalbar: Ø -0,57 R.

BEREITS GETRACKTE SIGNALE BLEIBEN IMMER DRIN
Der Filter wirkt nur auf NEUE Entries. Eine Zeile, zu der schon eine echte
Position (oder ein "missed"-Eintrag) existiert, wird nie entfernt -- sonst
verwaist die Position im Re-Scan-Vergleich (genau dieser Fehler, Memory
`ctnl_sim_filter_is_not_live_gate`: 38 statt 3 offene Positionen).

FAIL-SAFE: fehlt der Groessenwert einer NEUEN Zeile, wird sie nicht
gehandelt und separat gemeldet (Datenfehler, kein Strategie-Urteil).
"""
from __future__ import annotations

from typing import Callable

import pandas as pd

SPIKE_MIN_ATR = 0.75
SPALTE = "signal_spike"
GATED_LEGS = {"ctnl_reversal"}


def annotate(trades: pd.DataFrame, signals: pd.DataFrame) -> pd.DataFrame:
    """Haengt die Signalbar-Groesse (Range/ATR) an eine Trade-Tabelle aus
    simulate_trades[_concurrent]. `signal_bar` ist der POSITIONS-Index in
    `signals`. Rein additiv -- keine Zeile wird entfernt."""
    if trades is None or trades.empty or "signal_bar" not in trades.columns:
        return trades
    row = signals.iloc[trades["signal_bar"].astype(int).to_numpy()]
    spike = ((row["high"] - row["low"]) / row["atr"]).to_numpy()
    return trades.assign(**{SPALTE: spike})


def spike_of_bar(bar: pd.Series) -> float:
    """Dasselbe Mass fuer eine einzelne Signalbar (EK arbeitet je Signal)."""
    atr = float(bar["atr"])
    return float(bar["high"] - bar["low"]) / atr if atr > 0 else float("nan")


def allows(spike: float | None) -> bool:
    return spike is not None and pd.notna(spike) and spike >= SPIKE_MIN_ATR


def filter_trades(trades: pd.DataFrame, is_tracked: Callable[[pd.Series], bool],
                  *, leg: str = "ctnl_reversal") -> tuple[pd.DataFrame, str]:
    """(gefilterte Tabelle, Log-Zeile). `is_tracked(row)` sagt, ob zu der
    Zeile schon ein State-Eintrag existiert -- solche Zeilen bleiben immer."""
    if trades is None or trades.empty:
        return trades, ""
    if SPALTE not in trades.columns:
        tracked = trades.apply(is_tracked, axis=1)
        return trades[tracked], (f"{leg}: Spalte '{SPALTE}' fehlt -- alle NEUEN Entries blockiert "
                                 "(fail-safe, Scan liefert keine Signalbar-Groesse)")
    tracked = trades.apply(is_tracked, axis=1)
    sp = trades[SPALTE]
    gross = sp >= SPIKE_MIN_ATR
    behalten = tracked | gross
    klein = int((~behalten & sp.notna()).sum())
    ohne = int((~behalten & sp.isna()).sum())
    teile = []
    if klein:
        teile.append(f"{klein} mit Signalbar < {SPIKE_MIN_ATR:g} ATR verworfen (Regel, kein Fehler)")
    if ohne:
        teile.append(f"{ohne} OHNE Groessenwert blockiert -- DATENFEHLER")
    hinweis = (f"{leg}: Spike-Filter behaelt {int(behalten.sum())} von {len(trades)}; "
               + "; ".join(teile)) if teile else ""
    return trades[behalten], hinweis
