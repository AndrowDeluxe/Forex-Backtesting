"""Edge Card „Dayli Trade“ -- Regel-Entwurf Feld 02, Typ R (Reversal), als Signal-Scanner.

    python -m htf_daily_trade.rules EURUSD 2025-01-01

Entwurf vom 02.11.2026 ([[htf-daily-trade-edge-card]]); mit (V) markierte Teile sind
Claude-Lesarten, noch nicht vom Nutzer bestaetigt. Ohne Makro-Gate.

Indikatoren wie im Nutzer-Chart:
- Fractals: 5 Kerzen (2 links, 2 rechts), bekannt 2 Tage nach dem Extrem.
- MA Cross: SMA 12 / SMA 20 (TradingView-„MA Cross“, Kerzenschluss).
- RSI Multi Length [LuxAlgo]: hier angenaehert als Mittel von RSI(10..20) (V); Schwellen 30/70 (V).
- MACD 12/26/9: Cross nach dem RSI-Extrem = hoehere Risikostufe (nicht Pflicht).
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from htf_daily_trade.ipda_cycles import load_daily

RSI_LOOKBACK = 20   # (V) Handelstage: RSI-Extrem vor dem Fractal (Nutzer-Beispiel 09/2026: ~3 Wochen)
CROSS_WINDOW = 5    # (V) Handelstage: MA-Cross nach dem Fractal
MAX_WAIT = 10       # (V) spaetester Einstieg nach dem Fractal
RSI_LOW, RSI_HIGH = 30, 70   # (V) Baender wie im LuxAlgo-Chart (~70/~28); Nutzer nannte 25/75


def rsi(close: pd.Series, n: int) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


def indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    c = out["Close"]
    out["ma_fast"] = c.rolling(12).mean()
    out["ma_slow"] = c.rolling(20).mean()
    out["rsi_ml"] = pd.concat([rsi(c, n) for n in range(10, 21)], axis=1).mean(axis=1)
    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    out["macd"], out["macd_sig"] = macd, macd.ewm(span=9, adjust=False).mean()
    h, l = out["High"], out["Low"]
    out["frac_hi"] = (h > h.shift(1)) & (h > h.shift(2)) & (h > h.shift(-1)) & (h > h.shift(-2))
    out["frac_lo"] = (l < l.shift(1)) & (l < l.shift(2)) & (l < l.shift(-1)) & (l < l.shift(-2))
    return out


def reversal_signals(df: pd.DataFrame) -> pd.DataFrame:
    x = indicators(df)
    idx = x.index
    diff = x["ma_fast"] - x["ma_slow"]
    cross_dn = (diff < 0) & (diff.shift(1) >= 0)
    cross_up = (diff > 0) & (diff.shift(1) <= 0)
    mdiff = x["macd"] - x["macd_sig"]
    macd_dn = (mdiff < 0) & (mdiff.shift(1) >= 0)
    macd_up = (mdiff > 0) & (mdiff.shift(1) <= 0)
    rows = []
    for i in range(len(x)):
        for side in ("short", "long"):
            if side == "short" and not x["frac_hi"].iat[i]:
                continue
            if side == "long" and not x["frac_lo"].iat[i]:
                continue
            r = x["rsi_ml"].iloc[max(0, i - RSI_LOOKBACK):i + 1]
            if side == "short" and not (r >= RSI_HIGH).any():
                continue
            if side == "long" and not (r <= RSI_LOW).any():
                continue
            cross = (cross_dn if side == "short" else cross_up).iloc[i:i + CROSS_WINDOW + 1]
            if not cross.any():
                continue
            j = i + int(np.argmax(cross.to_numpy()))
            level = x["Low"].iat[i] if side == "short" else x["High"].iat[i]
            stop = x["High"].iat[i] if side == "short" else x["Low"].iat[i]
            for e in range(max(i + 2, j), min(len(x), i + MAX_WAIT + 1)):
                c = x["Close"].iat[e]
                if (side == "short" and c < level) or (side == "long" and c > level):
                    macd_ok = (macd_dn if side == "short" else macd_up).iloc[i:e + 1].any()
                    rows.append({"fractal": idx[i].date(), "seite": side, "einstieg": idx[e].date(),
                                 "kurs": round(c, 5), "stop": round(stop, 5),
                                 "risiko_pips": round(abs(stop - c) * (100 if c > 20 else 10000), 1),
                                 "macd_cross": bool(macd_ok),
                                 "rsi_extrem": round(float(r.max() if side == "short" else r.min()), 1)})
                    break
    return pd.DataFrame(rows)


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "EURUSD"
    start = sys.argv[2] if len(sys.argv) > 2 else "2025-01-01"
    df = load_daily(name)
    sig = reversal_signals(df)
    print(sig[sig["einstieg"] >= pd.Timestamp(start).date()].to_string(index=False))


def continuation_signals(df: pd.DataFrame, sweep_window: int = 7) -> pd.DataFrame:
    """Typ C nach Nutzer-Definition (02.11.): (1) Manipulation -- eine Daily-Kerze bricht ueber
    (unter) die Hochs (Tiefs) der 3 vorherigen Kerzen; (2) Einstieg auf dem Daily-Close, sobald
    eine Kerze unter (ueber) den Dochten der 3 vorherigen Kerzen schliesst, d. h. unter deren
    Tiefs (ueber deren Hochs). (V) Einstieg spaetestens `sweep_window` Handelstage nach der Manipulation.
    Trend (V): MA 12 unter (ueber) MA 20. Stop (V): Extrem seit der Manipulation."""
    x = indicators(df)
    h, l, o, c = x["High"], x["Low"], x["Open"], x["Close"]
    prev3 = lambda s, f: pd.concat([s.shift(k) for k in (1, 2, 3)], axis=1).agg(f, axis=1)
    sweep_up = h > prev3(h, "max")
    sweep_dn = l < prev3(l, "min")
    close_dn = c < prev3(l, "min")   # Nutzer 02.11.: Schluss unter den Dochten (Tiefs)
    close_up = c > prev3(h, "max")   # der 3 vorherigen Kerzen
    down = x["ma_fast"] < x["ma_slow"]
    rows, last = [], {"short": -10, "long": -10}
    for t in range(3, len(x)):
        for side in ("short", "long"):
            trend_ok = down.iat[t] if side == "short" else not down.iat[t]
            trig = close_dn.iat[t] if side == "short" else close_up.iat[t]
            if not (trend_ok and trig) or t - last[side] <= sweep_window:
                continue
            sw = (sweep_up if side == "short" else sweep_dn).iloc[max(0, t - sweep_window):t + 1]
            if not sw.any():
                continue
            s0 = max(0, t - sweep_window) + int(np.argmax(sw.to_numpy()))
            stop = h.iloc[s0:t + 1].max() if side == "short" else l.iloc[s0:t + 1].min()
            cc = c.iat[t]
            rows.append({"manipulation": x.index[s0].date(), "einstieg": x.index[t].date(), "seite": side,
                         "kurs": round(cc, 5), "stop": round(stop, 5),
                         "risiko_pips": round(abs(stop - cc) * (100 if cc > 20 else 10000), 1)})
            last[side] = t
    return pd.DataFrame(rows)
