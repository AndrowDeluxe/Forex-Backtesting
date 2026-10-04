"""Faber 10-Monats-SMA auf ^SP500TR (Tagesdaten) -- Spezifikation Nutzer 2026-10-04.

Daten: Yahoo ^SP500TR ab 1988-01-01, einmal geladen und als CSV mit Datum im
Namen eingefroren (scripts/frozen_data/). Alle Laeufe lesen nur diese Datei.

Signal: Monatsschluss = letzter Handelstag des Monats in den Daten; laufender
Monat zaehlt nicht. SMA = Mittel der letzten 10 Monatsschluesse inkl. aktuellem.
Schluss > SMA long, < SMA Cash, == alter Zustand; vor erstem gueltigen Signal Cash.
Neue Position gilt ab dem Schlusskurs des ersten Handelstags nach dem
Monatsschluss (die Rendite dieses Tages laeuft noch mit der alten Position).

Renditen taeglich: Position (Vortagsschluss) x Tagesrendite, Cash 0 %.
Kosten: Spread 0,05 % je Ein- und Ausstieg; Swap je Kalendertag investiert
(mittel 2,5 %/J, hoch 5 %/J). Keine Steuern. MaxDD vor Kosten.
"""
import glob
import json
import os
import sys
from datetime import date

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FROZEN_DIR = os.path.join(ROOT, "scripts", "frozen_data")
OUT = os.path.join(ROOT, "Claude outputs", "faber_sp500tr.json")
SPLIT = pd.Timestamp("2006-06-01")
SPREAD = 0.0005
COSTS = {"ohne": (0.0, 0.0), "mittel": (SPREAD, 0.025), "hoch": (SPREAD, 0.05)}


def load_frozen():
    files = sorted(glob.glob(os.path.join(FROZEN_DIR, "sp500tr_daily_*.csv")))
    if not files:
        import yfinance as yf
        os.makedirs(FROZEN_DIR, exist_ok=True)
        d = yf.download("^SP500TR", start="1988-01-01", auto_adjust=False, progress=False)
        close = d["Close"].squeeze().dropna().rename("close")
        path = os.path.join(FROZEN_DIR, f"sp500tr_daily_{date.today():%Y%m%d}.csv")
        close.to_csv(path, index_label="date")
        files = [path]
        print("eingefroren:", path)
    path = files[-1]
    s = pd.read_csv(path, index_col="date", parse_dates=True)["close"]
    return s.sort_index(), os.path.basename(path)


def complete_month_ends(close):
    """Letzter Handelstag je Monat; der Monat des letzten Datenpunkts zaehlt nur,
    wenn dieser Datenpunkt der letzte Werktag des Kalendermonats ist."""
    me = close.groupby(close.index.to_period("M")).tail(1)
    last = close.index[-1]
    if last != (last + pd.offsets.BMonthEnd(0)):
        me = me.iloc[:-1]
    return me


def monthly_signal(me, n):
    sma = me.rolling(n).mean()
    sig, state = [], 0
    for c, a in zip(me.values, sma.values):
        if not np.isnan(a):
            if c > a:
                state = 1
            elif c < a:
                state = 0
        sig.append(state)
    return pd.Series(sig, index=me.index), sma


def daily_position(close, me_sig):
    """Position am Tagesschluss. Signal vom Monatsschluss t0 gilt ab Schluss t1."""
    idx = close.index
    pos = pd.Series(np.nan, index=idx)
    pos.iloc[0] = 0.0
    for t0, s in me_sig.items():
        i = idx.get_loc(t0)
        if i + 1 < len(idx):
            pos.iloc[i + 1] = s
    return pos.ffill()


def curve(close, pos, start, end, spread=0.0, swap=0.0, entry_cost_at_start=True):
    """Equity ab Schluss `start` (=1) bis `end`. Rendite Tag d = pos[d-1]*r[d]."""
    c = close.loc[:end]
    p = pos.loc[:end]
    r = c.pct_change()
    held = p.shift(1)
    days = c.index.to_series().diff().dt.days
    net = held * r - held * swap * days / 365.0
    trades = p.diff().abs()
    net = (1 + net) * (1 - spread * trades) - 1
    net = net.loc[start:].copy()
    net.iloc[0] = 0.0
    eq = (1 + net).cumprod()
    if entry_cost_at_start and p.loc[start] == 1 and spread:
        eq *= (1 - spread)
    return eq


def stats(eq):
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = eq.iloc[-1] / eq.iloc[0]
    cagr = cagr ** (1 / yrs) - 1
    dd = (eq / eq.cummax() - 1).min()
    return {"von": str(eq.index[0].date()), "bis": str(eq.index[-1].date()),
            "jahre": round(yrs, 2), "cagr_pct": round(cagr * 100, 2),
            "maxdd_pct": round(dd * 100, 2), "endwert": round(float(eq.iloc[-1]), 3)}


def segment(close, pos, start, end):
    p = pos.loc[start:end]
    entries = int(((p.diff() == 1)).sum() + (p.iloc[0] == 1))
    exits = int((p.diff() == -1).sum())
    res = {"zeit_im_markt_pct": round(float(pos.shift(1).loc[start:end].iloc[1:].mean()) * 100, 1),
           "einstiege": entries, "ausstiege": exits}
    for k, (sp, sw) in COSTS.items():
        res[f"strategie_{k}"] = stats(curve(close, pos, start, end, sp, sw))
    res["maxdd_vor_kosten_pct"] = res["strategie_ohne"]["maxdd_pct"]
    bh = close.loc[start:end] / close.loc[start]
    res["buy_and_hold"] = stats(bh)
    return res


def run_variant(close, me, n, end):
    sig, sma = monthly_signal(me, n)
    pos = daily_position(close, sig)
    first_trade = pos[pos == 1].index[0]
    split_day = close.index[close.index >= SPLIT][0]
    pre_end = close.index[close.index < SPLIT][-1]
    out = {"erster_trade_tag": str(first_trade.date()),
           "gesamt": segment(close, pos, first_trade, end),
           "vor_2006_06": segment(close, pos, first_trade, pre_end),
           "ab_2006_06": segment(close, pos, split_day, end)}
    return out, sig, sma, pos, first_trade


def random_test(close, me, sig, pos, first_trade, end, runs=2000, seed=42):
    """Monats-Positionen der Strategie zufaellig mischen (gleiche Zeit im Markt)."""
    real_dd = stats(curve(close, pos, first_trade, end))["maxdd_pct"]
    # Monate, deren Signal im Bewertungsfenster wirkt: Monatsschluss vor first_trade bis Ende
    idx = close.index
    t1 = pd.Series([idx[idx.get_loc(t) + 1] if idx.get_loc(t) + 1 < len(idx) else pd.NaT
                    for t in sig.index], index=sig.index)
    use = sig[(t1 >= first_trade) & (sig.index <= end)]
    rng = np.random.default_rng(seed)
    dds = []
    for _ in range(runs):
        sh = pd.Series(rng.permutation(use.values), index=use.index)
        full = sig.copy()
        full.loc[use.index] = sh.values
        p = daily_position(close, full)
        eq = curve(close, p, first_trade, end, entry_cost_at_start=False)
        dds.append((eq / eq.cummax() - 1).min() * 100)
    dds = np.array(dds)
    return {"maxdd_strategie_pct": real_dd, "monate_gemischt": int(len(use)),
            "anteil_long_monate_pct": round(float(use.mean()) * 100, 1),
            "anteil_zufall_dd_gleich_oder_kleiner": round(float(np.mean(dds >= real_dd - 1e-9)), 4),
            "zufall_maxdd_median_pct": round(float(np.median(dds)), 2),
            "zufall_maxdd_p05_p95_pct": [round(float(np.percentile(dds, 5)), 2),
                                         round(float(np.percentile(dds, 95)), 2)]}


def main():
    close, fname = load_frozen()
    r = close.pct_change()
    extreme = r[r.abs() > 0.10]
    me = complete_month_ends(close)
    end = me.index[-1]  # Bewertung endet am letzten abgeschlossenen Monatsschluss
    res = {"datei": fname, "daten_von": str(close.index[0].date()), "daten_bis": str(close.index[-1].date()),
           "bewertung_bis": str(end.date()),
           "tagesrenditen_ueber_10pct": {str(k.date()): round(v * 100, 2) for k, v in extreme.items()},
           "varianten": {}}
    for n in (10, 8, 9, 11, 12):
        out, sig, sma, pos, ft = run_variant(close, me, n, end)
        if n == 10:
            out["zufall"] = random_test(close, me, sig, pos, ft, end)
            last = me.index[-1]
            res["gegencheck_letzter_monat"] = {
                "monat": str(last.to_period("M")), "monatsschluss_tag": str(last.date()),
                "schluss": round(float(me.iloc[-1]), 2), "durchschnitt_10m": round(float(sma.iloc[-1]), 2),
                "signal": "long" if sig.iloc[-1] == 1 else "cash",
                "gilt_ab_schluss": str(close.index[close.index.get_loc(last) + 1].date())
                if close.index.get_loc(last) + 1 < len(close) else "naechster Handelstag (noch keine Daten)"}
        res["varianten"][f"sma{n}"] = out
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    json.dump(res, sys.stdout, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
