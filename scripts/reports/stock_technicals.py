"""Technische Kennzahlen einer Aktie aus Yahoo-Tageskursen (fuer geplante Einzelanalysen per claude -p).

    python scripts/reports/stock_technicals.py NVDA

Gibt JSON aus: Kurs, SMA20/50/200, RSI14, MACD, ATR14, Bollinger, 52-Wochen-Spanne, Renditen,
Swing-Hochs/-Tiefs und Volumenprofil. Gerechnet, nicht von Webseiten abgeschrieben.
"""

from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
import yfinance as yf


def technicals(ticker: str) -> dict:
    d = yf.download(ticker, period="2y", progress=False, auto_adjust=True)
    d.columns = [c[0] if isinstance(c, tuple) else c for c in d.columns]
    c, h, l, v = d["Close"], d["High"], d["Low"], d["Volume"]
    dl = c.diff()
    up = dl.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    dn = (-dl.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rsi = 100 - 100 / (1 + up / dn)
    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    sig = macd.ewm(span=9, adjust=False).mean()
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    s20 = c.rolling(20).mean()
    sd20 = c.rolling(20).std()
    y = d[d.index >= d.index[-1] - pd.Timedelta(days=365)]
    w = 5
    lo, hi = l.iloc[-260:], h.iloc[-260:]
    swing_lo = [(str(lo.index[k].date()), round(float(lo.iloc[k]), 2)) for k in range(w, len(lo) - w)
                if lo.iloc[k] == lo.iloc[k - w:k + w + 1].min()]
    swing_hi = [(str(hi.index[k].date()), round(float(hi.iloc[k]), 2)) for k in range(w, len(hi) - w)
                if hi.iloc[k] == hi.iloc[k - w:k + w + 1].max()]
    step = max(1.0, round(float(c.iloc[-1]) * 0.03))
    bins = np.arange(np.floor(float(c.iloc[-260:].min()) / step) * step,
                     float(c.iloc[-260:].max()) + step, step)
    vp = pd.Series(v.iloc[-260:].values, index=pd.cut(c.iloc[-260:], bins)).groupby(level=0, observed=False).sum()
    last = lambda s: round(float(s.iloc[-1]), 2)  # noqa: E731
    return {
        "ticker": ticker, "datum": str(c.index[-1].date()), "close": last(c),
        "letzte_5_tage": [{"datum": str(i.date()), "open": round(float(r.Open), 2), "high": round(float(r.High), 2),
                           "low": round(float(r.Low), 2), "close": round(float(r.Close), 2), "volumen": int(r.Volume)}
                          for i, r in d.tail(5).iterrows()],
        "sma20": last(s20), "sma50": last(c.rolling(50).mean()), "sma200": last(c.rolling(200).mean()),
        "rsi14": round(float(rsi.iloc[-1]), 1), "macd": last(macd), "macd_signal": last(sig),
        "atr14": last(atr), "atr_pct": round(float(atr.iloc[-1] / c.iloc[-1] * 100), 2),
        "bollinger_unten": last(s20 - 2 * sd20), "bollinger_oben": last(s20 + 2 * sd20),
        "hoch_52w": round(float(y["High"].max()), 2), "tief_52w": round(float(y["Low"].min()), 2),
        "volumen_5t_vs_50t": round(float(v.iloc[-5:].mean() / v.iloc[-55:-5].mean()), 2),
        "rendite_pct": {f"{n}d": round(float((c.iloc[-1] / c.iloc[-1 - n] - 1) * 100), 1) for n in (1, 5, 21, 63, 252)},
        "swing_tiefs": swing_lo[-8:], "swing_hochs": swing_hi[-8:],
        "volumenprofil_pct": {str(k): round(float(x), 1) for k, x in (vp / vp.sum() * 100).items() if x > 0},
    }


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(technicals(sys.argv[1] if len(sys.argv) > 1 else "NVDA"), ensure_ascii=False, indent=1))
