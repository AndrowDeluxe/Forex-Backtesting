"""Rechenbausteine: IC mit Newey-West-t, Regime-Regel (Drittel), Kontrollen, Kennzahlen."""

from __future__ import annotations

import numpy as np
import pandas as pd

from fusion_lab.metals_htf.spec import LOWER, N_RANDOM, UPPER

WEEKS = 52


def nw_tstat(x: pd.Series, lags: int) -> float:
    """t-Wert des Mittelwerts mit Newey-West-Standardfehler (Bartlett, `lags` Verzoegerungen)."""
    x = pd.Series(x).dropna().values.astype(float)
    n = len(x)
    if n < 10:
        return float("nan")
    e = x - x.mean()
    v = e @ e / n
    for k in range(1, min(lags, n - 1) + 1):
        v += 2 * (1 - k / (lags + 1)) * (e[k:] @ e[:-k]) / n
    return float(x.mean() / np.sqrt(v / n)) if v > 0 else float("nan")


def ic(signal: pd.Series, fwd: pd.Series, h: int) -> dict:
    """Spearman-IC = Mittel von Rang-z(Signal) x Rang-z(Rendite); t mit Newey-West, h-1 Lags (ueberlappend)."""
    d = pd.concat([signal, fwd], axis=1, keys=["s", "r"]).dropna()
    if len(d) < 30:
        return {"n": len(d), "ic": np.nan, "t": np.nan}
    z = d.rank().apply(lambda c: (c - c.mean()) / c.std(ddof=0))
    p = z["s"] * z["r"]
    return {"n": len(d), "ic": float(p.mean()), "t": nw_tstat(p, max(h - 1, 0))}


def positions(sig: pd.Series, upper: float = UPPER, lower: float = LOWER) -> pd.Series:
    """Oberes Drittel long (+1), unteres short (-1), sonst/fehlend flat (0)."""
    return pd.Series(np.where(sig > upper, 1.0, np.where(sig < lower, -1.0, 0.0)), index=sig.index)


def pnl(pos: pd.Series, r1: pd.Series, cost_bps: float, swap_pa: float = 0.0) -> pd.Series:
    """Wochenrendite: Position am Freitag t -> Rendite t..t+1, Kosten je Seite und Einheit Positionswechsel.
    Wochen ohne Rendite (Datenluecke) zaehlen nicht und erzeugen keine Kosten."""
    d = pd.concat([pos, r1], axis=1, keys=["p", "r"]).dropna(subset=["r"])
    p = d["p"].fillna(0.0)
    trade = p.diff().abs().fillna(p.abs())
    return p * d["r"] - trade * cost_bps / 1e4 - p.abs() * swap_pa / WEEKS


def stats(r: pd.Series, pos: pd.Series | None = None) -> dict:
    r = r.dropna()
    if len(r) < 10:
        return {"n_w": len(r)}
    eq = r.cumsum()
    sd = r.std(ddof=1)
    out = {"n_w": len(r), "ret_pa_%": round(r.mean() * WEEKS * 100, 2),
           "sharpe": round(float(r.mean() / sd * np.sqrt(WEEKS)), 3) if sd > 0 else np.nan,
           "t": round(float(r.mean() / sd * np.sqrt(len(r))), 2) if sd > 0 else np.nan,
           "maxDD_%": round(float((eq - eq.cummax()).min() * 100), 1)}
    if pos is not None:
        p = pos.reindex(r.index).fillna(0)
        out.update({"long_%": round((p > 0).mean() * 100, 1), "short_%": round((p < 0).mean() * 100, 1),
                    "wechsel": int((p.diff().abs() > 0).sum())})
    return out


def sharpe(r: pd.Series) -> float:
    r = r.dropna()
    sd = r.std(ddof=1)
    return float(r.mean() / sd * np.sqrt(WEEKS)) if len(r) > 10 and sd > 0 else np.nan


def random_timing(pos: pd.Series, r1: pd.Series, cost_bps: float, n: int = N_RANDOM, seed: int = 7) -> np.ndarray:
    """Sharpe von n zufaellig permutierten Positionsreihen (gleiche Exposure-Verteilung, gleiche Kosten-Regel)."""
    d = pd.concat([pos, r1], axis=1, keys=["p", "r"]).dropna(subset=["r"])
    p0 = d["p"].fillna(0.0).values
    rng = np.random.default_rng(seed)
    out = np.empty(n)
    for i in range(n):
        p = pd.Series(rng.permutation(p0), index=d.index)
        out[i] = sharpe(pnl(p, d["r"], cost_bps))
    return out


def faber_positions(faber_raw: pd.Series) -> pd.Series:
    """Kontrolle Faber: long ueber der 10-Monats-SMA, sonst flat."""
    return pd.Series(np.where(faber_raw > 0, 1.0, 0.0), index=faber_raw.index).where(faber_raw.notna(), 0.0)


def block_bootstrap(r: pd.Series, fn, block: int = 13, n: int = 2000, seed: int = 11) -> np.ndarray:
    """Kennzahl `fn` auf n Block-Bootstrap-Stichproben (zusammenhaengende Bloecke, Autokorrelation bleibt)."""
    x = r.dropna().values
    m = len(x)
    if m < block * 2:
        return np.array([np.nan])
    rng = np.random.default_rng(seed)
    k = int(np.ceil(m / block))
    out = np.empty(n)
    for i in range(n):
        starts = rng.integers(0, m - block + 1, k)
        s = np.concatenate([x[j:j + block] for j in starts])[:m]
        out[i] = fn(pd.Series(s))
    return out


def max_dd(r: pd.Series) -> float:
    eq = r.cumsum()
    return float((eq - eq.cummax()).min())
