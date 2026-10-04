"""Monatssignale -- Spezifikation Nutzer 2026-10-04 (identisch zu
scripts/research_faber_sp500tr.py): Monatsschluss = letzter Handelstag des
Monats; laufender Monat zaehlt nicht; SMA inkl. aktuellem Monat; > long,
< Cash (bzw. short, falls erlaubt), == alter Zustand; vor erstem gueltigem
Signal Cash."""
import numpy as np
import pandas as pd


def complete_month_ends(close, data_end=None):
    """Letzter Handelstag je Monat. Der Monat des letzten Datenpunkts zaehlt
    nur, wenn dieser Datenpunkt der letzte Werktag des Kalendermonats ist
    (BTC handelt auch am Wochenende: dann Kalender-Monatsende)."""
    me = close.groupby(close.index.to_period("M")).tail(1)
    last = close.index[-1] if data_end is None else data_end
    month_end_ok = last == (last + pd.offsets.BMonthEnd(0)) or last == (last + pd.offsets.MonthEnd(0))
    if me.index[-1].to_period("M") == last.to_period("M") and not month_end_ok:
        me = me.iloc[:-1]
    return me


def sma_signal(me, n, allow_short=False):
    sma = me.rolling(n).mean()
    out, state = [], 0
    for c, a in zip(me.values, sma.values):
        if not np.isnan(a):
            if c > a:
                state = 1
            elif c < a:
                state = -1 if allow_short else 0
        out.append(state)
    return pd.Series(out, index=me.index), sma


def tsmom_signal(me, n=12, allow_short=False):
    r = me.pct_change(n)
    out, state = [], 0
    for x in r.values:
        if not np.isnan(x):
            if x > 0:
                state = 1
            elif x < 0:
                state = -1 if allow_short else 0
        out.append(state)
    return pd.Series(out, index=me.index)


def by_month(sig):
    """Index auf Kalendermonat (Period) umstellen, damit Instrumente mit
    unterschiedlichen Handelstagen vergleichbar sind."""
    s = sig.copy()
    s.index = s.index.to_period("M")
    return s
