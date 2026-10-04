"""ORB NASDAQ: Was kostet es, dass die Bridge die Storno-am-SL-Regel nur
gepollt (Funded/FK alle 5 Min, EK alle 2 Min) statt sofort umsetzen kann?

Faellt SL-Touch und Fuellung in DASSELBE Poll-Intervall, ist die Order schon
gefuellt, wenn die Bridge sie stornieren will -- sie schliesst die Position dann
beim naechsten Lauf (Schlusskurs der letzten Minute vor dem Poll). Der Backtest
kennt diesen Trade nicht. Hier: Haeufigkeit und R dieser "Blitz-Trades", M1.
Nutzerentscheid 2026-10-04 (NASDAQ Storno am SL + ohne Teilziel).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from research_orb_cancel_at_sl_and_hold import ENTRY_SLIPPAGE_BPS, EXIT_SLIPPAGE_BPS, SPREAD_BPS  # noqa: E402
from research_orb_cancel_at_sl_montecarlo import load_m1  # noqa: E402

STOP = 0.6
inst = "NASDAQ"
frame, allowed = load_m1(inst)
half = SPREAD_BPS[inst] / 10_000 / 2
es, xs = ENTRY_SLIPPAGE_BPS / 10_000, EXIT_SLIPPAGE_BPS / 10_000
tw = frame[frame.index >= frame["range_end"]]
for poll in (5, 2):
    flash = []
    n_sessions = 0
    for session, day in tw.groupby("session"):
        dirs = allowed.get(pd.Timestamp(session), [])
        if not dirs or pd.isna(day["orb_high"].iloc[0]):
            continue
        day = day[day.index < day["session_close"].iloc[0]]
        n_sessions += 1
        lvl = {1: day["orb_high"].iloc[0], -1: day["orb_low"].iloc[0]}
        atr = day["atr"].iloc[0]
        sl = {d: lvl[d] * (1 + half * d) - d * STOP * atr for d in dirs}
        hi, lo, cl = day["high"].to_numpy(), day["low"].to_numpy(), day["close"].to_numpy()
        state = {d: "pending" for d in dirs}
        touched = {d: None for d in dirs}      # Minute des ersten SL-Touchs (solange pending)
        for k in range(len(day)):
            # Bridge-Poll zu Beginn von Minute k (sieht Minuten < k)
            if k > 0 and k % poll == 0:
                for d in dirs:
                    if state[d] == "pending" and touched[d] is not None:
                        state[d] = "cancelled"
            pend = [d for d in dirs if state[d] == "pending"]
            fill = {d: (hi[k] >= lvl[d]) if d == 1 else (lo[k] <= lvl[d]) for d in pend}
            hit = {d: (lo[k] <= sl[d]) if d == 1 else (hi[k] >= sl[d]) for d in pend}
            filled = [d for d in pend if fill[d]]
            if len(filled) == 2:
                continue
            if filled:
                d = filled[0]
                if touched[d] is not None:          # SL lag VOR der Fuellung -> Blitz-Trade
                    nxt = (k // poll + 1) * poll    # naechster Poll
                    j = min(nxt - 1, len(day) - 1)
                    entry = lvl[d] * (1 + (half + es) * d)
                    risk = abs(entry - sl[d])
                    # bis zum Poll ausgestoppt? (SL liegt beim Broker)
                    seg_lo, seg_hi = lo[k + 1:j + 1], hi[k + 1:j + 1]
                    stopped = (seg_lo <= sl[d]).any() if d == 1 else (seg_hi >= sl[d]).any()
                    px = sl[d] if stopped else cl[j]
                    r = d * (px * (1 - (half + xs) * d) - entry) / risk
                    flash.append({"session": session, "r": r, "stopped": stopped, "min_after_touch": k - touched[d]})
                    state[d] = "closed"            # Gegenseite bleibt (wie Backtest)
                    continue
                break                               # regulaerer Trade -- Rest wie Backtest
            for d in pend:
                if hit[d] and touched[d] is None:
                    touched[d] = k
    f = pd.DataFrame(flash)
    print(f"Poll {poll} Min: {len(f)} Blitz-Trades in {n_sessions} Sessions "
          f"({len(f) / n_sessions:.1%}), Ø R {f['r'].mean():+.3f}, Σ R {f['r'].sum():+.1f}, "
          f"davon ausgestoppt {f['stopped'].mean():.0%}")
