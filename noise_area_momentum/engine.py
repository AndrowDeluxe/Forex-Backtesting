"""Intraday-Momentum mit "Noise Area" nach Zarattini/Aziz/Barbon (SFI N°24-97,
"Beat the Market", SSRN 4824172, Version 22.09.2025).

Regeln 1:1 aus dem Paper (Abschnitt 3):
- sigma(t, HH:MM) = Mittel der letzten `lookback` Tage von |Close(HH:MM)/Open(09:30) - 1|
- UB = max(Open_t, Close_{t-1}) * (1 + VM*sigma), LB = min(Open_t, Close_{t-1}) * (1 - VM*sigma)
- Entscheidungen nur zu HH:00/HH:30, erste um 10:00, letzte um 15:30; Exit spaetestens 16:00
- Stop "opp":  long bis Kurs < LB (dann short), short spiegelbildlich (Basismodell, Tab. 1)
- Stop "vwap": long nur solange Kurs > max(UB, VWAP), short solange Kurs < min(LB, VWAP)
              (Tab. 2; entspricht dem Concretum-Code: Signal je Halbstunde neu bewertet)
- Sizing "1x": 100 % Exposure; "dyn": min(4, 2 % / sigma_daily(14 Tage)) (Tab. 3)

Abweichungen, die unsere Daten erzwingen (im Befund ausweisen):
- Dukascopy-Index-CFD (SP500/NASDAQ) statt SPY-ETF; Volumen ist Tick-Volumen,
  der VWAP also ein Tick-gewichteter Naeherungswert.
- Kosten: gemessener CFD-Spread + Slippage je Rundturn (statt $0,0035/Aktie).

Preis zur Entscheidung HH:MM = Close der Bar HH:MM-1; Fuellung = Open der Bar
HH:MM (+ `lag_bars` fuer die Ausfuehrungs-Lag-Probe p6_6).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

N_BARS = 390                                   # 09:30 .. 15:59
DECISIONS = np.arange(30, 361, 30)             # Minuten nach 09:30: 10:00 .. 15:30
MIN_BARS_PER_DAY = 300                         # Feiertage/Halbtage raus


def build_grid(m1: pd.DataFrame, start: str = "09:30", n_bars: int = N_BARS,
               decisions: np.ndarray | None = None) -> dict:
    """M1 (NY-Zeit) -> Tage x n_bars Minuten-Arrays ab `start` (Standard 09:30, 390 Bars).
    Andere Uhr (z.B. Oel 09:00-14:30): start/n_bars/decisions setzen; die Entscheidungszeiten
    liegen dann in grid["decisions"] (Minuten nach `start`) und gelten nur fuer run_general()."""
    h0, m0 = (int(x) for x in start.split(":"))
    end = pd.Timestamp(2000, 1, 1, h0, m0) + pd.Timedelta(minutes=n_bars - 1)
    d = m1.between_time(start, end.strftime("%H:%M")).copy()
    d["date"] = d.index.tz_localize(None).normalize()
    d["k"] = (d.index.hour - h0) * 60 + d.index.minute - m0
    counts = d.groupby("date").size()
    keep = counts[counts >= MIN_BARS_PER_DAY * n_bars / N_BARS].index
    d = d[d["date"].isin(keep)]
    out = {"dates": pd.DatetimeIndex(keep)}
    if decisions is not None:
        out["decisions"] = np.asarray(decisions)
    for col in ("open", "high", "low", "close", "volume"):
        g = d.pivot(index="date", columns="k", values=col).reindex(columns=range(n_bars))
        if col == "volume":
            g = g.fillna(0.0)
        elif col == "open":
            g = g.fillna(d.pivot(index="date", columns="k", values="close").reindex(columns=range(n_bars)).ffill(axis=1).shift(1, axis=1))
            g = g.bfill(axis=1)
        else:
            g = g.ffill(axis=1).bfill(axis=1)
        out[col] = g.to_numpy(dtype=float)
    out["open"] = np.where(np.isnan(out["open"]), out["close"], out["open"])
    return out


def _sigma(grid: dict, lookback: int) -> np.ndarray:
    o0 = grid["open"][:, [0]]
    move = np.abs(grid["close"] / o0 - 1.0)            # move[:, m-1] = Bewegung bis HH:MM
    cs = np.vstack([np.zeros((1, move.shape[1])), np.cumsum(move, axis=0)])
    sig = np.full_like(move, np.nan)
    n = move.shape[0]
    idx = np.arange(lookback, n)
    sig[idx] = (cs[idx] - cs[idx - lookback]) / lookback   # nur Vortage
    return sig


def _vwap(grid: dict) -> np.ndarray:
    tp = (grid["high"] + grid["low"] + grid["close"]) / 3.0
    v = grid["volume"]
    cv = np.cumsum(v, axis=1)
    ctp = np.cumsum(tp * v, axis=1)
    eq = np.cumsum(tp, axis=1) / np.arange(1, tp.shape[1] + 1)
    return np.where(cv > 0, ctp / np.where(cv > 0, cv, 1.0), eq)


def daily_leverage(grid: dict, target: float = 0.02, cap: float = 4.0, window: int = 14) -> np.ndarray:
    close = pd.Series(grid["close"][:, -1], index=grid["dates"])
    vol = close.pct_change().rolling(window, min_periods=window).std(ddof=1).shift(1)
    return np.minimum(cap, target / vol).to_numpy()


def run(grid: dict, *, vm: float = 1.0, lookback: int = 14, stop: str = "vwap", sizing: str = "1x",
        cost_rt_bps: float = 0.0, lag_bars: int = 0, gate: np.ndarray | None = None) -> pd.DataFrame:
    """Tagesweise Ergebnisse. ret_* sind Tagesrenditen (Anteil vom Kapital)."""
    o, c = grid["open"], grid["close"]
    n = o.shape[0]
    sig = _sigma(grid, lookback)
    prev_close = np.r_[np.nan, c[:-1, -1]]
    o0 = o[:, 0]
    top, bot = np.fmax(o0, prev_close), np.fmin(o0, prev_close)
    vw = _vwap(grid)

    m = DECISIONS
    p = c[:, m - 1]
    ub = top[:, None] * (1 + vm * sig[:, m - 1])
    lb = bot[:, None] * (1 - vm * sig[:, m - 1])
    v = vw[:, m - 1]

    pos = np.zeros_like(p)
    if stop == "vwap":
        pos[(p > ub) & (p > v)] = 1.0
        pos[(p < lb) & (p < v)] = -1.0
    elif stop == "opp":
        cur = np.zeros(n)
        for j in range(len(m)):
            cur = np.where(p[:, j] > ub[:, j], 1.0, np.where(p[:, j] < lb[:, j], -1.0, cur))
            pos[:, j] = cur
    else:
        raise ValueError(stop)

    valid = ~np.isnan(ub).any(axis=1) & ~np.isnan(prev_close)
    pos[~valid] = 0.0
    if gate is not None:          # gesperrte Tage bleiben als 0-Rendite-Tage in der Reihe
        pos[~gate] = 0.0

    fill_idx = np.minimum(m + lag_bars, N_BARS - 1)
    x = np.column_stack([o[:, fill_idx], c[:, -1]])
    seg = x[:, 1:] / x[:, :-1] - 1.0
    gross = (pos * seg).sum(axis=1)
    padded = np.column_stack([np.zeros(n), pos, np.zeros(n)])
    turnover = np.abs(np.diff(padded, axis=1)).sum(axis=1)
    entries = ((pos != 0) & (pos != padded[:, :-2])).sum(axis=1)
    cost = turnover * cost_rt_bps / 2 * 1e-4

    lev = daily_leverage(grid) if sizing == "dyn" else np.ones(n)
    lev = np.where(np.isnan(lev), 0.0, lev)
    if sizing == "dyn":
        valid &= lev > 0
    return pd.DataFrame({
        "valid": valid, "lev": lev, "trades": entries,
        "gross_1x": gross, "cost_1x": cost,
        "ret_gross": lev * gross, "ret_net": lev * (gross - cost),
        "long_gross": (np.where(pos > 0, pos, 0) * seg).sum(axis=1),
        "short_gross": (np.where(pos < 0, pos, 0) * seg).sum(axis=1),
    }, index=grid["dates"])


def entry_stop_distance_bps(grid: dict, *, vm: float = 1.0, lookback: int = 14) -> np.ndarray:
    """Fuer p6_8: Abstand Einstiegskurs -> Trailing-Stop (max(UB,VWAP) bzw. min(LB,VWAP))
    in bps, je Einstieg (Variante "vwap")."""
    o, c = grid["open"], grid["close"]
    sig = _sigma(grid, lookback)
    prev_close = np.r_[np.nan, c[:-1, -1]]
    top, bot = np.fmax(o[:, 0], prev_close), np.fmin(o[:, 0], prev_close)
    vw = _vwap(grid)
    m = DECISIONS
    p, v = c[:, m - 1], vw[:, m - 1]
    ub = top[:, None] * (1 + vm * sig[:, m - 1])
    lb = bot[:, None] * (1 - vm * sig[:, m - 1])
    pos = np.where((p > ub) & (p > v), 1, np.where((p < lb) & (p < v), -1, 0))
    prev = np.column_stack([np.zeros(len(p)), pos[:, :-1]])
    new = (pos != 0) & (pos != prev) & ~np.isnan(ub)
    stop = np.where(pos > 0, np.fmax(ub, v), np.fmin(lb, v))
    return (np.abs(p - stop) / p * 1e4)[new]


def metrics(df: pd.DataFrame, col: str = "ret_net") -> dict:
    d = df[df["valid"]]
    r = d[col]
    if len(r) < 20:
        return {"tage": len(r)}
    eq = (1 + r).cumprod()
    yrs = len(r) / 252
    traded = d[d["trades"] > 0]
    sd = r.std(ddof=1)
    return {
        "tage": len(r), "cagr_%": (eq.iloc[-1] ** (1 / yrs) - 1) * 100, "vol_%": sd * np.sqrt(252) * 100,
        "sharpe": r.mean() / sd * np.sqrt(252) if sd > 0 else np.nan,
        "t": r.mean() / sd * np.sqrt(len(r)) if sd > 0 else np.nan,
        "mdd_%": ((eq / eq.cummax()) - 1).min() * -100,
        "bps_tag": r.mean() * 1e4, "hit_tag": (traded[col] > 0).mean(),
        "trades_tag": d["trades"].mean(),
        "brutto_bps_trade_1x": d["gross_1x"].sum() / max(d["trades"].sum(), 1) * 1e4,
    }


def yearly(df: pd.DataFrame, col: str = "ret_net") -> pd.Series:
    d = df[df["valid"]][col]
    return ((1 + d).groupby(d.index.year).prod() - 1) * 100


# --- Regime-2026-Raster (14.10.): allgemeine Positionslogik ---------------------------------
# direction "mom": Einstieg in Ausbruchsrichtung (Paper); "fade": dagegen.
# exit fuer "mom": vwap = Kurs faellt unter max(Band, VWAP) (Paper) | band = zurueck ins Band |
#                  opp = Gegenband (mit Flip) | none = bis 16:00
# exit fuer "fade" (Ziel-Logik, kein Stop): vwap = VWAP erreicht | band = zurueck im Band |
#                  opp = Gegenband erreicht | none = bis 16:00
# window: all = 10:00-15:30 | first = nur ein Einstieg je Tag | am = bis 12:00 | pm = ab 12:30
# sides: both | long | short
_PREP: dict = {}


def _prep(grid: dict, lookback: int):
    key = (id(grid), lookback)
    if key not in _PREP:
        o, c = grid["open"], grid["close"]
        sig = _sigma(grid, lookback)
        prev_close = np.r_[np.nan, c[:-1, -1]]
        top, bot = np.fmax(o[:, 0], prev_close), np.fmin(o[:, 0], prev_close)
        m = grid.get("decisions", DECISIONS)
        _PREP[key] = (c[:, m - 1], sig[:, m - 1], top, bot, _vwap(grid)[:, m - 1],
                      ~np.isnan(sig[:, m - 1]).any(axis=1) & ~np.isnan(prev_close))
    return _PREP[key]


def _exit_mask(direction: str, exit: str, p, u, l, v):
    if exit == "none":
        z = np.zeros_like(p, dtype=bool)
        return z, z
    if direction == "mom":
        if exit == "vwap":
            return ~(p > np.fmax(u, v)), ~(p < np.fmin(l, v))
        if exit == "band":
            return p <= u, p >= l
        if exit == "opp":
            return p < l, p > u
    else:
        if exit == "vwap":
            return p >= v, p <= v
        if exit == "band":
            return p >= l, p <= u
        if exit == "opp":
            return p >= u, p <= l
    raise ValueError((direction, exit))


def positions_general(grid: dict, *, vm: float = 1.0, lookback: int = 14, direction: str = "mom",
                      exit: str = "vwap", sides: str = "both", window: str = "all",
                      gate: np.ndarray | None = None, long_ok: np.ndarray | None = None,
                      short_ok: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """long_ok/short_ok: optionale Einstiegs-Masken (Tage x Entscheidungen), z.B. Oel-Filter."""
    p, sg, top, bot, vw, valid = _prep(grid, lookback)
    ub = top[:, None] * (1 + vm * sg)
    lb = bot[:, None] * (1 - vm * sg)
    n = len(p)
    ok_day = valid if gate is None else valid & gate
    cur, used = np.zeros(n), np.zeros(n, dtype=bool)
    pos = np.zeros_like(p)
    for j, mm in enumerate(grid.get("decisions", DECISIONS)):
        pj, u, l, v = p[:, j], ub[:, j], lb[:, j], vw[:, j]
        lx, sx = _exit_mask(direction, exit, pj, u, l, v)
        cur = np.where(((cur > 0) & lx) | ((cur < 0) & sx), 0.0, cur)
        win_ok = {"all": True, "first": True, "am": mm <= 150, "pm": mm >= 180}[window]
        allowed = ok_day & (cur == 0) & win_ok
        if window == "first":
            allowed &= ~used
        up, dn = pj > u, pj < l
        tl, ts = (up, dn) if direction == "mom" else (dn, up)
        if sides == "short":
            tl = np.zeros_like(tl)
        if sides == "long":
            ts = np.zeros_like(ts)
        if long_ok is not None:
            tl = tl & long_ok[:, j]
        if short_ok is not None:
            ts = ts & short_ok[:, j]
        new = np.where(allowed & tl, 1.0, np.where(allowed & ts, -1.0, 0.0))
        new = np.where(((new > 0) & lx) | ((new < 0) & sx), 0.0, new)   # Sofort-Exit (Paper: Einstieg nur ueber VWAP)
        used |= new != 0
        cur = np.where(new != 0, new, cur)
        pos[:, j] = cur
    return pos, valid


def run_general(grid: dict, *, cost_rt_bps: float = 0.0, lag_bars: int = 0, sizing: str = "1x",
                vol_target: float = 0.02, **kw) -> pd.DataFrame:
    """sizing "dyn": Hebel min(4, vol_target / Tagesvola 14 T.); vol_target 0,02 = Paper, 0,01 = "1 % Risiko"."""
    pos, valid = positions_general(grid, **kw)
    o, c = grid["open"], grid["close"]
    n = len(pos)
    fill_idx = np.minimum(grid.get("decisions", DECISIONS) + lag_bars, c.shape[1] - 1)
    x = np.column_stack([o[:, fill_idx], c[:, -1]])
    seg = x[:, 1:] / x[:, :-1] - 1.0
    gross = (pos * seg).sum(axis=1)
    padded = np.column_stack([np.zeros(n), pos, np.zeros(n)])
    turnover = np.abs(np.diff(padded, axis=1)).sum(axis=1)
    entries = ((pos != 0) & (pos != padded[:, :-2])).sum(axis=1)
    cost = turnover * cost_rt_bps / 2 * 1e-4
    lev = daily_leverage(grid, target=vol_target) if sizing == "dyn" else np.ones(n)
    lev = np.where(np.isnan(lev), 0.0, lev)
    if sizing == "dyn":
        valid = valid & (lev > 0)
    return pd.DataFrame({
        "valid": valid, "lev": lev, "trades": entries, "gross_1x": gross, "cost_1x": cost,
        "ret_gross": lev * gross, "ret_net": lev * (gross - cost),
        "long_gross": (np.where(pos > 0, pos, 0) * seg).sum(axis=1),
        "short_gross": (np.where(pos < 0, pos, 0) * seg).sum(axis=1),
    }, index=grid["dates"])


def slice_grid(grid: dict, start: str) -> dict:
    """Tage ab `start` (fuer schnelle Raster auf kurzen Fenstern; Vorlauf fuer Lookback mitnehmen)."""
    keep = grid["dates"] >= pd.Timestamp(start)
    out = {k: (v if k == "decisions" else v[keep]) for k, v in grid.items()}
    return out
