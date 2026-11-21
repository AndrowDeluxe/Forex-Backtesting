"""Auswertung des Quellen-Ledgers: Traegt eine Quelle oder nicht?

Je Quelle x Klasse x Horizont:
- treffer:        Anteil, bei dem das Vorzeichen des Werts zur Folgerendite passt (nur Werte != 0)
- kontrolle:      bester Wert aus "immer long" bzw. "immer short" auf denselben Zeilen (Long-Beta-Falle!)
- vorsprung:      treffer - kontrolle (> 0 heisst: die Quelle weiss mehr als die Marktrichtung)
- spread:         Oe Rendite bei positivem Wert minus Oe Rendite bei negativem Wert (in %)
- ic:             Rang-Korrelation Wert <-> Folgerendite
- aussagekraeftig: n >= MIN_OBS
Startkurs = erster Schlusskurs mit Datum NACH dem Aufzeichnungstag (kein Vorgriff). Teilen sich mehrere
Aufzeichnungen denselben Startkurs (Sa/So bei Aktien/FX), zaehlt nur die letzte (Sonntag = Stand vor Wochenstart).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from fusion_lab.news_sources import config as C
from fusion_lab.news_sources import ledger


def load_prices(tickers: list[str], start: str) -> pd.DataFrame:
    import yfinance as yf
    df = yf.download(tickers, start=start, progress=False, auto_adjust=True, group_by="column")["Close"]
    if isinstance(df, pd.Series):
        df = df.to_frame(tickers[0])
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    return df


def forward_returns(led: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    """Haengt ret_<h> (Folgerendite in %) an; NaN, solange der Horizont nicht erreicht ist."""
    out = led.copy()
    out["start"] = pd.NaT
    for h in C.HORIZONS:
        out[f"ret_{h}"] = np.nan
    for i, r in out.iterrows():
        tick = C.UNIVERSE[r["symbol"]]["kurs"]
        if tick not in prices:
            continue
        s = prices[tick].dropna()
        after = s.index[s.index > pd.Timestamp(r["datum"])]
        if not len(after):
            continue
        k = s.index.get_loc(after[0])
        out.at[i, "start"] = after[0]
        for h in C.HORIZONS:
            if k + h < len(s):
                out.at[i, f"ret_{h}"] = (s.iloc[k + h] / s.iloc[k] - 1) * 100
    return out


def evaluate(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    d = df[df["status"] == "ok"].copy()
    d["wert"] = pd.to_numeric(d["wert"], errors="coerce")
    if {"start", "symbol", "datum"} <= set(d.columns):
        # Wochenende/Feiertag: mehrere Aufzeichnungen messen dieselbe Folgerendite (gleicher Startkurs).
        # Nur die letzte vor dem Start zaehlt, sonst blaeht die doppelte Zaehlung die Trefferquote auf.
        has = d["start"].notna()
        d = pd.concat([d[~has], d[has].sort_values("datum").drop_duplicates(["quelle", "symbol", "start"], keep="last")])
    for (q, kl), g in d.groupby(["quelle", "klasse"]):
        for h in C.HORIZONS:
            x = g.dropna(subset=["wert", f"ret_{h}"])
            x = x[x["wert"] != 0]
            if x.empty:
                continue
            ret, w = x[f"ret_{h}"], x["wert"]
            hit = float((np.sign(w) == np.sign(ret)).mean())
            up = float((ret > 0).mean())
            ctrl = max(up, 1 - up)
            pos, neg = ret[w > 0], ret[w < 0]
            rows.append({"quelle": q, "klasse": kl, "horizont": h, "n": len(x),
                         "treffer": round(hit, 3), "kontrolle": round(ctrl, 3), "vorsprung": round(hit - ctrl, 3),
                         "spread_pct": round(pos.mean() - neg.mean(), 3) if len(pos) and len(neg) else np.nan,
                         "ic": round(float(w.rank().corr(ret.rank())), 3) if len(x) > 2 else np.nan,
                         "aussagekraeftig": len(x) >= C.MIN_OBS})
    return pd.DataFrame(rows)


def availability() -> pd.DataFrame:
    if not ledger.RUNS.exists():
        return pd.DataFrame()
    r = pd.read_csv(ledger.RUNS)
    return r.groupby("quelle").agg(laeufe=("status", "size"), ok=("status", lambda s: int((s == "ok").sum())),
                                   letzter_status=("status", "last"), letzter_grund=("grund", "last"))


def report() -> tuple[pd.DataFrame, pd.DataFrame]:
    led = ledger.read()
    if led.empty:
        return pd.DataFrame(), availability()
    ticks = sorted({C.UNIVERSE[s]["kurs"] for s in led["symbol"].unique()})
    start = (pd.Timestamp(led["datum"].min()) - pd.Timedelta(days=3)).date().isoformat()
    return evaluate(forward_returns(led, load_prices(ticks, start))), availability()
