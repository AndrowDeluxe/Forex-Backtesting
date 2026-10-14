"""Kill-Switch: Pause + Schattenkonto + Hysterese.

Muster aus gold_smc_htf_ltf/ctnl_kill_switch.py: die Gesundheit der
STRATEGIE wird auf einem Schattenkonto gemessen, das jeden Trade mitzaehlt,
auch die pausierten. So kann der Schalter wieder aufgehen.

Zeitbezug: Fuer die Entscheidung "Trade j handeln?" zaehlen nur Trades mit
exit_time <= entry_time_j (Memory ctnl-serienstopp: sonst Lookahead).
Alarm, wenn badness >= thr; Freigabe erst, wenn badness <= rel (Hysterese).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def episodes_seq(b: np.ndarray, thr: float, rel: float) -> int:
    """Anzahl Alarm-Episoden in einer Folge (fuer die Kalibrierung, ohne Zeit)."""
    on, n = False, 0
    for v in b:
        if np.isnan(v):
            continue
        if not on and v >= thr:
            on, n = True, n + 1
        elif on and v <= rel:
            on = False
    return n


def run(entry: pd.Series, exit_: pd.Series, b: np.ndarray, thr: float, rel: float) -> tuple[np.ndarray, list]:
    """entry/exit: Zeitpunkte je Trade (nach entry sortiert). b: badness nach
    dem i-ten GESCHLOSSENEN Trade, also in Schlussreihenfolge berechnet
    (siehe close_order). Rueckgabe: Maske 'live gehandelt' und Episoden."""
    entry = pd.DatetimeIndex(entry)
    exit_ = pd.DatetimeIndex(exit_)
    order_close = np.argsort(exit_.values, kind="stable")
    live = np.ones(len(entry), dtype=bool)
    on, start, eps = False, None, []
    ci = 0
    for j in range(len(entry)):
        # alle bis zum Einstieg geschlossenen Trades verarbeiten, in Schlussreihenfolge
        while ci < len(order_close) and exit_[order_close[ci]] <= entry[j]:
            v = b[ci]
            t = exit_[order_close[ci]]
            if not np.isnan(v):
                if not on and v >= thr:
                    on, start = True, t
                elif on and v <= rel:
                    on = False
                    eps.append((start, t))
            ci += 1
        live[j] = not on
    if on:
        eps.append((start, None))
    return live, eps


def close_order(exit_: pd.Series) -> np.ndarray:
    """Indizes der Trades in Schlussreihenfolge (stabil)."""
    return np.argsort(pd.DatetimeIndex(exit_).values, kind="stable")


def state_seq(b: np.ndarray, thr: float, rel: float) -> np.ndarray:
    """Alarmzustand nach jedem geschlossenen Trade (b in Schlussreihenfolge)."""
    on, out = False, np.zeros(len(b), dtype=bool)
    for i, v in enumerate(b):
        if not np.isnan(v):
            if not on and v >= thr:
                on = True
            elif on and v <= rel:
                on = False
        out[i] = on
    return out


def mask_from_states(entry: pd.Series, exit_: pd.Series, states: np.ndarray) -> np.ndarray:
    """Live-Maske: Trade j wird gehandelt, wenn nach dem letzten bis entry_j
    geschlossenen Trade kein Alarm stand. states in Schlussreihenfolge."""
    ex_sorted = np.sort(pd.DatetimeIndex(exit_).values, kind="stable")
    k = np.searchsorted(ex_sorted, pd.DatetimeIndex(entry).values, side="right")   # Anzahl geschlossener Trades
    prev = np.r_[False, states]
    return ~prev[k]
