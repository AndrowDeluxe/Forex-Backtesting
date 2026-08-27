"""Gemeinsame 10-Jahre In-Sample/Out-of-Sample-Fensterdefinition fuer
Intraday-FX-Strategien (CLS practical, London-Range-Setups, etc.), auf
Wunsch des Users (2026-08-12): "die vollen 10 Jahre, 5 IS und 5 OOS" statt
der bisherigen Ad-hoc-Kurzfenster (6 Monate). Chronologischer Split (aeltere
Haelfte = In-Sample zum Entwickeln/Tunen, juengere Haelfte = Out-of-Sample,
EINMAL am Ende gegengeprueft) -- dieselbe Konvention wie
ou_paper_backtest/config.py's IN_SAMPLE_START/OUT_SAMPLE_START.

Nicht strategie-spezifisch -- lebt bewusst NICHT in cls_practical/, damit
andere Intraday-FX-Strategien (z.B. scripts/research_london_range_bos_retest.py)
denselben Zeitraum reproduzierbar mitnutzen koennen, ohne cls_practical zu
importieren."""

import pandas as pd

TODAY = pd.Timestamp.now(tz="Europe/Berlin").normalize()

OUT_SAMPLE_END = TODAY
OUT_SAMPLE_START = TODAY - pd.DateOffset(years=5)
IN_SAMPLE_END = OUT_SAMPLE_START
IN_SAMPLE_START = IN_SAMPLE_END - pd.DateOffset(years=5)

FULL_START = IN_SAMPLE_START
FULL_END = OUT_SAMPLE_END
