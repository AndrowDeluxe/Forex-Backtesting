"""Tageskurse der Fact-Sheet-Maerkte aus Dukascopy (tagesaktuell, wie der G8-Nachbau).

Dukascopy-D1 beginnt um 00:00 UTC; der kurze Sonntagsbar faellt weg. AUDNZD gibt es dort nicht:
nur der Schluss aus AUDUSD/NZDUSD, ohne ATR (Hochs/Tiefs zweier Paare fallen nicht gleichzeitig).
"""

from __future__ import annotations

import pandas as pd

USD_PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD"]
CROSSES = ["EURGBP", "EURJPY", "EURCHF", "AUDNZD", "GBPJPY", "AUDJPY", "CADJPY"]
MARKETS = USD_PAIRS + ["XAUUSD"] + CROSSES
DUKA_KEY = {"XAUUSD": "GOLD"}
LOOKBACK_DAYS = 120


def _fetch(key: str, as_of: pd.Timestamp) -> pd.DataFrame:
    from combined_strategy.data import fetch_timeframe
    start = (as_of - pd.Timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    end = (as_of + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    df = fetch_timeframe(key, "D1", start, end)[["Open", "High", "Low", "Close"]].copy()
    df.index = df.index.tz_convert(None).normalize()
    return df[(df.index.dayofweek < 5) & (df.index <= as_of)]


def load(as_of: pd.Timestamp) -> dict[str, pd.DataFrame]:
    out = {m: _fetch(DUKA_KEY.get(m, m), as_of) for m in MARKETS if m != "AUDNZD"}
    out["AUDNZD"] = (out["AUDUSD"]["Close"] / out["NZDUSD"]["Close"]).dropna().to_frame("Close")
    return out


def atr(df: pd.DataFrame, n: int = 14) -> float | None:
    if not {"High", "Low"} <= set(df.columns) or len(df) <= n:
        return None
    prev = df["Close"].shift()
    tr = pd.concat([df["High"] - df["Low"], (df["High"] - prev).abs(), (df["Low"] - prev).abs()], axis=1).max(axis=1)
    return float(tr.iloc[-n:].mean())


def stats(df: pd.DataFrame) -> dict | None:
    c = df["Close"].dropna()
    if len(c) < 50:
        return None
    pct = lambda n: float((c.iloc[-1] / c.iloc[-1 - n] - 1) * 100)
    sma20, sma50 = c.iloc[-20:].mean(), c.iloc[-50:].mean()
    a = atr(df)
    digits = 5 if c.iloc[-1] < 20 else 3
    return {"close": round(float(c.iloc[-1]), digits), "date": c.index[-1].date().isoformat(),
            "ret_5d_pct": round(pct(5), 2), "ret_20d_pct": round(pct(20), 2),
            "sma20": round(float(sma20), digits), "sma50": round(float(sma50), digits),
            "dist_sma20_pct": round(float((c.iloc[-1] / sma20 - 1) * 100), 2),
            "atr14": None if a is None else round(a, digits)}
