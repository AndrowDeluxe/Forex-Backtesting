"""Gemeinsames Indikator-Modul (Nachbau der TradingView-Indikatoren des Nutzers).

Einstellungen laut knowledge/resources/indikator-steckbriefe.md (bestaetigt 26.11.2026).
Alle Funktionen nutzen nur Werte bis zur jeweiligen Kerze (kein Vorgriff, kein Repaint).
Gegen TradingView-Exporte geprueft mit htf_daily_trade/tv_abgleich.py.
"""
import numpy as np
import pandas as pd


def rma(x: pd.Series, n: int) -> pd.Series:
    """Wilder-Glaettung wie Pine ta.rma (Start mit SMA der ersten n Werte)."""
    x = x.astype(float)
    out = np.full(len(x), np.nan)
    v = x.to_numpy()
    valid = np.where(~np.isnan(v))[0]
    if len(valid) < n:
        return pd.Series(out, index=x.index)
    s = valid[0]
    out[s + n - 1] = np.nanmean(v[s:s + n])
    a = 1.0 / n
    for i in range(s + n, len(v)):
        out[i] = a * v[i] + (1 - a) * out[i - 1]
    return pd.Series(out, index=x.index)


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    up = rma(d.clip(lower=0), n)
    dn = rma((-d).clip(lower=0), n)
    return 100 - 100 / (1 + up / dn)


def rsi_mit_ma(close: pd.Series, n: int = 14, ma_n: int = 14) -> pd.DataFrame:
    """RSI(14) + SMA(14) des RSI; cross_up/cross_dn = RSI kreuzt seine MA."""
    r = rsi(close, n)
    m = r.rolling(ma_n).mean()
    return pd.DataFrame({
        "rsi": r, "rsi_ma": m,
        "rsi_cross_up": (r > m) & (r.shift() <= m.shift()),
        "rsi_cross_dn": (r < m) & (r.shift() >= m.shift()),
    })


def rsi_multi_length(close: pd.Series, min_len: int = 10, max_len: int = 20,
                     ob: float = 70, os_: float = 30) -> pd.DataFrame:
    """RSI Multi Length [LuxAlgo]: Mittel-RSI, bewegliche Kanaele, Flaechen.

    ob_area = Anteil der Laengen ueber ob (0-100). os_area = Anteil unter os (0-100).
    TradingView plottet die Oversold-Flaeche als 100 - os_area.
    """
    v = close.to_numpy(float)
    n_len = max_len - min_len + 1
    num = np.zeros(n_len)
    den = np.zeros(n_len)
    avg_out = np.full(len(v), np.nan)
    upper = np.full(len(v), np.nan)
    lower = np.full(len(v), np.nan)
    ob_a = np.zeros(len(v))
    os_a = np.zeros(len(v))
    up_prev = np.nan
    lo_prev = np.nan
    lens = np.arange(min_len, max_len + 1)
    alpha = 1.0 / lens
    for t in range(len(v)):
        diff = 0.0 if t == 0 or np.isnan(v[t - 1]) else v[t] - v[t - 1]
        num = alpha * diff + (1 - alpha) * num
        den = alpha * abs(diff) + (1 - alpha) * den
        with np.errstate(invalid="ignore", divide="ignore"):
            r = 50 * num / den + 50
        r = np.where(np.isnan(r), 50.0, r)
        avg = r.mean()
        nb = (r > ob).sum() / n_len
        ns = (r < os_).sum() / n_len
        up_prev = avg if np.isnan(up_prev) else up_prev + nb * (avg - up_prev)
        lo_prev = avg if np.isnan(lo_prev) else lo_prev + ns * (avg - lo_prev)
        avg_out[t], upper[t], lower[t] = avg, up_prev, lo_prev
        ob_a[t], os_a[t] = nb * 100, ns * 100
    return pd.DataFrame({"rsi_ml": avg_out, "rsi_ml_upper": upper, "rsi_ml_lower": lower,
                         "rsi_ml_ob_area": ob_a, "rsi_ml_os_area": os_a}, index=close.index)


def stoch_rsi(close: pd.Series, k: int = 3, d: int = 3, rsi_len: int = 14,
              stoch_len: int = 14) -> pd.DataFrame:
    r = rsi(close, rsi_len)
    lo = r.rolling(stoch_len).min()
    hi = r.rolling(stoch_len).max()
    kk = (100 * (r - lo) / (hi - lo)).rolling(k).mean()
    dd = kk.rolling(d).mean()
    return pd.DataFrame({
        "stoch_k": kk, "stoch_d": dd,
        "stoch_cross_up": (kk > dd) & (kk.shift() <= dd.shift()),
        "stoch_cross_dn": (kk < dd) & (kk.shift() >= dd.shift()),
    })


def macd(close: pd.Series, fast: int = 8, slow: int = 20, signal: int = 14) -> pd.DataFrame:
    """MACD wie TradingView (EMA/EMA). Daily-Einstellung des Nutzers: 8/20/14."""
    def ema(x, n):
        out = x.ewm(span=n, adjust=False).mean()
        out.iloc[:n - 1] = np.nan  # Pine ta.ema startet erst nach n Werten (SMA-Seed)
        return out
    m = ema(close, fast) - ema(close, slow)
    s = m.ewm(span=signal, adjust=False).mean()
    return pd.DataFrame({
        "macd": m, "macd_signal": s, "macd_hist": m - s,
        "macd_cross_up": (m > s) & (m.shift() <= s.shift()),
        "macd_cross_dn": (m < s) & (m.shift() >= s.shift()),
    })


def bollinger(src: pd.Series, n: int = 20, mult: float = 2.0) -> pd.DataFrame:
    basis = src.rolling(n).mean()
    sd = src.rolling(n).std(ddof=0)
    return pd.DataFrame({"bb_basis": basis, "bb_upper": basis + mult * sd,
                         "bb_lower": basis - mult * sd})


def nw_envelope(close: pd.Series, h: float = 8.0, mult: float = 3.0,
                window: int = 500) -> pd.DataFrame:
    """Nadaraya-Watson Envelope [LuxAlgo], NICHT-repaintender Modus (Endpunkt-Schaetzung).

    Linie = gewichtetes Mittel der letzten `window` Schlusskurse mit Gauss-Gewichten,
    Huelle = Linie +/- mult * SMA(|close - Linie|, window - 1).
    """
    v = close.to_numpy(float)
    i = np.arange(window)
    w = np.exp(-(i ** 2) / (h * h * 2))
    line = np.full(len(v), np.nan)
    for t in range(len(v)):
        m = min(window, t + 1)
        seg = v[t - m + 1:t + 1][::-1]
        line[t] = (seg * w[:m]).sum() / w[:m].sum()
    line = pd.Series(line, index=close.index)
    mae = (close - line).abs().rolling(window - 1, min_periods=1).mean() * mult
    up, lo = line + mae, line - mae
    return pd.DataFrame({
        "nw_line": line, "nw_upper": up, "nw_lower": lo,
        "nw_cross_up": (close > up) & (close.shift() <= up.shift()),   # Ausbruch oben
        "nw_cross_dn": (close < lo) & (close.shift() >= lo.shift()),   # Ausbruch unten
    })


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    pc = df["close"].shift()
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(),
                    (df["low"] - pc).abs()], axis=1).max(axis=1)
    tr.iloc[0] = df["high"].iloc[0] - df["low"].iloc[0]
    return rma(tr, n)


def alle(df: pd.DataFrame) -> pd.DataFrame:
    """Alle sechs bestaetigten Indikatoren mit den Nutzer-Einstellungen."""
    c = df["close"]
    return pd.concat([rsi_mit_ma(c), rsi_multi_length(c), stoch_rsi(c), macd(c),
                      bollinger(c), nw_envelope(c), atr(df).rename("atr")], axis=1)
