"""Wochen-Frame (Freitagsschluss) mit Merkmalen aus spec.FEATURES, ohne Vorgriff.

Verfuegbarkeit je Quelle (Wert gilt erst ab hier):
  Kurse Yahoo (Metalle, HG, DBC, DXY)   Tagesschluss, am Freitag bekannt
  FRED (DFII10, T10YIE, DGS2/10, GVZ)   Wert vom Tag d erst ab d+1 Handelstag  -> Freitag kennt Donnerstag
  CFTC                                  Bericht (Di) + 3 Tage = Freitag (15:30 ET, vor Schluss)
  GLD-Bestand                           +1 Handelstag
  IMF-Goldreserven                      Monatsende + 2 Monate
Wochenwert = letzter gueltiger Tageswert bis Freitag, aber nur wenn hoechstens MAX_AGE Tage alt (keine Luecke
ueber Wochen fortschreiben). Datenqualitaet: Yahoo PL=F hat 2006-09 monatelange Luecken -> Platin erst ab 2010.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from fusion_lab.metals_htf import data as D
from fusion_lab.metals_htf.spec import (COT_MIN, COT_WINDOW, FEATURES, LOOKBACKS, METALS, PCT_MIN, PCT_WINDOW,
                                        name)

KEY = {"GOLD": "gc", "SILVER": "si", "PLATINUM": "pl"}
DATA_START = {"GOLD": "2003-01-01", "SILVER": "2003-01-01", "PLATINUM": "2010-01-01"}
MAX_AGE = 6          # Kalendertage: Freitag darf hoechstens Wert vom Samstag davor nutzen
COT_MAX_AGE = 10


# ------------------------------------------------------------------ Grundbausteine

def week_grid(end: pd.Timestamp, start: str = "2003-01-03") -> pd.DatetimeIndex:
    return pd.date_range(start, end, freq="W-FRI")


def weekly(s: pd.Series, grid: pd.DatetimeIndex, max_age: int = MAX_AGE) -> pd.Series:
    """Letzter gueltiger Wert <= Freitag, NaN wenn aelter als max_age Tage."""
    s = s.dropna().sort_index()
    s = s[~s.index.duplicated(keep="last")]
    if s.empty:
        return pd.Series(np.nan, index=grid)
    pos = s.index.searchsorted(grid, side="right") - 1
    ok = pos >= 0
    vals = np.full(len(grid), np.nan)
    dates = np.full(len(grid), np.datetime64("NaT", "ns"), dtype="datetime64[ns]")
    vals[ok], dates[ok] = s.values[pos[ok]], s.index.values[pos[ok]]
    age = (grid.values - dates).astype("timedelta64[D]").astype(float)
    return pd.Series(np.where(ok & (age <= max_age), vals, np.nan), index=grid)


def lag_bdays(s: pd.Series, n: int = 1) -> pd.Series:
    """Wert vom Tag d gilt erst ab d + n Werktage."""
    s = s.dropna()
    return pd.Series(s.values, index=s.index + pd.offsets.BDay(n))


def avail_on(values: pd.Series, avail: pd.Series) -> pd.Series:
    return pd.Series(values.values, index=pd.DatetimeIndex(avail.values)).sort_index()


def rolling_pct(x: pd.Series, window: int = PCT_WINDOW, min_obs: int = PCT_MIN) -> pd.Series:
    """Perzentil des aktuellen Werts in den letzten `window` gueltigen Werten (inkl. aktuellem), nur Vergangenheit."""
    def pct(w: np.ndarray) -> float:
        return (w[:-1] < w[-1]).mean() + 0.5 * (w[:-1] == w[-1]).mean()
    v = x.dropna()
    return v.rolling(window, min_periods=min_obs).apply(pct, raw=True).reindex(x.index)


def _hlc(y: pd.DataFrame, k: str, start: str) -> pd.DataFrame:
    d = y[[f"{k}_high", f"{k}_low", f"{k}_close"]].copy()
    d.columns = ["h", "l", "c"]
    d = d[d.index >= start].dropna(subset=["c"])
    d["h"] = d[["h", "c"]].max(axis=1)          # Yahoo-OHLC teils widerspruechlich -> Spanne um den Schluss
    d["l"] = d[["l", "c"]].min(axis=1)
    return d


def cot_index(net: pd.Series, window: int = COT_WINDOW, min_obs: int = COT_MIN) -> pd.Series:
    lo, hi = net.rolling(window, min_periods=min_obs).min(), net.rolling(window, min_periods=min_obs).max()
    return ((net - lo) / (hi - lo).replace(0, np.nan)).clip(0, 1)


# ------------------------------------------------------------------ Merkmale

def daily_metal(d: pd.DataFrame) -> pd.DataFrame:
    """Taegliche Screener-Rohwerte je Metall (wie levels.technicals/scoring, aber als Reihe)."""
    c = d["c"]
    s50, s200 = c.rolling(50).mean(), c.rolling(200).mean()
    tr = pd.concat([d["h"] - d["l"], (d["h"] - c.shift()).abs(), (d["l"] - c.shift()).abs()], axis=1).max(axis=1)
    atr_pct = tr.rolling(14).mean() / c * 100
    out = pd.DataFrame(index=d.index)
    out["close"], out["sma50"], out["sma200"] = c, s50, s200
    out["sma50_steigung"] = s50 - s50.shift(20)
    checks = pd.concat([c > s50, c > s200, s50 > s200, out["sma50_steigung"] > 0], axis=1)
    out["trend"] = (checks.sum(axis=1) * 25.0).where(s200.notna() & out["sma50_steigung"].notna())
    out["ret_21d"] = (c / c.shift(21) - 1) * 100
    out["ret_63d"] = (c / c.shift(63) - 1) * 100
    out["ret_126d"] = (c / c.shift(126) - 1) * 100
    out["atr_pct"] = atr_pct
    out["momentum"] = (out["ret_126d"] - out["ret_21d"]) / (atr_pct * np.sqrt(105))
    hi, lo = d["h"].rolling(252, min_periods=200).max(), d["l"].rolling(252, min_periods=200).min()
    out["hoch_52w"], out["tief_52w"] = hi, lo
    out["lage_52w"] = (c - lo) / (hi - lo)
    out["faber"] = c / c.rolling(210).mean() - 1
    return out


def imf_net12() -> pd.Series:
    """Zentralbanken netto 12 Monate (Mio. oz), gilt ab Monatsende + 2 Monate (Logik wie gold_confirm.p_cb)."""
    imf = D.load("imf")
    piv = imf.pivot_table(index="month", columns="country", values="moz").sort_index()
    piv = piv.drop(columns=[c for c in piv.columns if not re.fullmatch(r"[A-Z]{3}", str(c))], errors="ignore")
    net12 = piv.diff().clip(-5, 5).sum(axis=1, min_count=1).rolling(12, min_periods=9).sum()
    return avail_on(net12, pd.Series(net12.index + pd.offsets.MonthEnd(0) + pd.offsets.MonthEnd(2)))


def build() -> dict:
    """-> {'grid', 'px' (Wochenschluss je Metall), 'daily' (je Metall), 'raw' {(merkmal, L): DataFrame[METALS]}}"""
    y, fred, cftc = D.load("yf"), D.load("fred"), D.load("cftc")
    end = y.index.max()
    grid = week_grid(end - pd.Timedelta(days=(end.dayofweek - 4) % 7))
    daily = {m: daily_metal(_hlc(y, KEY[m], DATA_START[m])) for m in METALS}
    px = pd.DataFrame({m: weekly(daily[m]["close"], grid) for m in METALS})
    W = lambda s, **kw: weekly(s, grid, **kw)  # noqa: E731
    fw = {k: W(lag_bdays(fred[k])) for k in fred.columns}
    hg, dbc, dxy = W(y["hg_close"]), W(y["dbc_close"]), W(y["dxy_close"])
    gld = W(lag_bdays(D.load("gld")["tonnes"]))
    real_gap = W(lag_bdays(fred["real10"].dropna() - fred["real10"].dropna().rolling(252, min_periods=200).mean()))
    cb = W(imf_net12(), max_age=40)
    gsr = np.log(px["GOLD"] / px["SILVER"])
    gsr_z = (gsr - gsr.rolling(52, min_periods=40).mean()) / gsr.rolling(52, min_periods=40).std()

    cot = {}
    for m in METALS:
        c = cftc[cftc["market"] == m].sort_values("report").drop_duplicates("report")
        net = c["m_money_positions_long_all"] - c["m_money_positions_short_all"]
        idx = cot_index(pd.Series(net.values, index=c["report"].values))
        cot[m] = W(avail_on(idx, pd.Series(idx.index + pd.Timedelta(days=3))), max_age=COT_MAX_AGE)

    raw: dict[tuple[str, int | None], pd.DataFrame] = {}
    same = lambda s: pd.DataFrame({m: s for m in METALS})  # noqa: E731
    per_metal = lambda col: pd.DataFrame({m: W(daily[m][col]) for m in METALS})  # noqa: E731
    for f, sp in FEATURES.items():
        for L in (LOOKBACKS if sp["lb"] else (None,)):
            if f in ("trend", "momentum", "lage_52w", "faber"):
                v = per_metal(f)
            elif f in ("cot_mit", "cot_contra"):
                v = pd.DataFrame(cot)
            elif f == "rel_staerke":
                v = pd.DataFrame({m: np.log(px[m]).diff(L) - np.log(dbc).diff(L) for m in METALS})
            elif f == "real_delta":
                v = same(fw["real10"].diff(L))
            elif f == "real_gap":
                v = same(real_gap)
            elif f == "usd_delta":
                v = same(np.log(dxy).diff(L))
            elif f == "be_delta":
                v = same(fw["be10"].diff(L))
            elif f == "us2_delta":
                v = same(fw["us2y"].diff(L))
            elif f == "curve_delta":
                v = same((fw["us10y"] - fw["us2y"]).diff(L))
            elif f == "gld_flow":
                v = same(np.log(gld).diff(L))
            elif f == "cb_12m":
                v = same(cb)
            elif f == "gvz":
                v = same(fw["gvz"])
            elif f == "gsr_z":
                v = same(gsr_z)
            elif f == "cu_au":
                v = same(np.log(hg / px["GOLD"]).diff(L))
            else:
                raise KeyError(f)
            for m in METALS:
                if sp["vorz"].get(m) is None:
                    v[m] = np.nan
            # Kein Datenstart-Schnitt hier: Makro-Merkmale brauchen die volle Historie fuer das Perzentil;
            # Platin ist vor 2010 ueber px/Renditen (NaN) ohnehin nicht im Test.
            raw[(f, L)] = v
    return {"grid": grid, "px": px, "daily": daily, "raw": raw, "dbc": dbc}


def oriented(raw: dict) -> dict[str, pd.DataFrame]:
    """Gleitendes Perzentil 0..1, mit erwartetem Vorzeichen gedreht (hoch = bullisch erwartet)."""
    out = {}
    for (f, L), v in raw.items():
        o = pd.DataFrame(index=v.index)
        for m in METALS:
            sgn = FEATURES[f]["vorz"].get(m)
            p = rolling_pct(v[m]) if sgn is not None else pd.Series(np.nan, index=v.index)
            o[m] = p if sgn in (1, None) else 1 - p
        out[name(f, L)] = o
    return out


def returns(px: pd.DataFrame) -> dict[int, pd.DataFrame]:
    """Log-Renditen Woche t -> t+h (h=1 fuer die Regime-Rechnung)."""
    lp = np.log(px)
    return {h: lp.shift(-h) - lp for h in (1, 4, 13, 26)}
