"""Termin-Gewichte CPI gegen NFP nach Regime (Nutzerauftrag 26.11.2026, aus der CPI/NFP-Ereignisstudie).

Befund (knowledge/resources/ereignisstudie-cpi-nfp.md): Welcher US-Termin die Zinsen bewegt, haengt am Regime
(bis 2018 NFP 3-5x staerker, 2021-23 CPI 3-4x, seit 2024 gleich). Statt eines festen Gewichts misst das Blatt
die Reaktion der US-2J-Rendite (Tagesaenderung in bp) je 1 SD Ueberraschung ueber die letzten 24 Monate.
Ueberraschung je Indikator auf die robuste Streuung (MAD) der FRUEHEREN Ueberraschungen normiert, bei +-3 gekappt (kein Vorgriff).
Anteil CPI = b_CPI / (b_CPI + b_NFP), negative Betas zaehlen als 0. Kontext, kein Signal.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from fusion_lab.macro_data import calendar, calendar_values

WINDOW_MONTHS = 24
MIN_EVENTS = 12
MIN_PRIOR = 20      # fruehere Termine fuer die Streuung
Z_CLIP = 3.0
DOMINANT = 0.6      # Anteil ab dem ein Termin "dominiert"
GROUPS = {"CPI": ["CPI m/m", "Core CPI m/m"], "NFP": ["Non-Farm Employment Change"]}
UPCOMING = {"CPI": ("CPI",), "NFP": ("Non-Farm", "Average Hourly Earnings", "Unemployment Rate")}


def robust_scale(x: pd.Series) -> pd.Series:
    """Streuung je Termin aus den FRUEHEREN Ueberraschungen: 1,4826 x MAD (robust). Die einfache Standardabweichung
    bleibt nach den Corona-NFP-Ausreissern 2020 (Millionen Stellen) dauerhaft aufgeblaeht -> z faellt gegen null."""
    v = x.to_numpy(float)
    out = np.full(len(v), np.nan)
    for i in range(MIN_PRIOR, len(v)):
        prior = v[:i]
        mad = np.median(np.abs(prior - np.median(prior)))
        out[i] = 1.4826 * mad if mad > 0 else np.nan
    return pd.Series(out, index=x.index)


def us_surprises(ff: pd.DataFrame, as_of: pd.Timestamp) -> pd.DataFrame:
    """Je US-CPI/NFP-Termin bis as_of: Datum, Gruppe, z (Mittel ueber die Gruppen-Indikatoren)."""
    names = {n: g for g, ns in GROUPS.items() for n in ns}
    ev = ff[(ff["currency"] == "USD") & ff["name"].isin(names)].copy()
    ev["t"] = pd.to_datetime(ev["time"], utc=True).dt.tz_localize(None)
    ev = ev[ev["t"] < as_of + pd.Timedelta(days=1)]
    a, f = ev["actual"].map(calendar.parse_number), ev["forecast"].map(calendar.parse_number)
    ev = ev.assign(av=a.str[0], fv=f.str[0], same=a.str[1] == f.str[1])
    ev = ev[ev["av"].notna() & ev["fv"].notna() & ev["same"]]
    ev = ev.assign(s=ev["av"].astype(float) - ev["fv"].astype(float)).sort_values("t")
    sd = ev.groupby("name")["s"].transform(robust_scale)
    ev["z"] = (ev["s"] / sd).clip(-Z_CLIP, Z_CLIP)
    ev = ev[np.isfinite(ev["z"])]
    ev["gruppe"] = ev["name"].map(names)
    ev["datum"] = ev["t"].dt.normalize()
    return ev.groupby(["datum", "gruppe"], as_index=False)["z"].mean()


def _beta(y: np.ndarray, x: np.ndarray) -> tuple[float, float]:
    ok = np.isfinite(y) & np.isfinite(x)
    y, x = y[ok], x[ok]
    if len(y) < MIN_EVENTS:
        return np.nan, np.nan
    X = np.c_[np.ones(len(x)), x]
    xtx = np.linalg.inv(X.T @ X)
    b = xtx @ X.T @ y
    e = y - X @ b
    cov = xtx @ (X.T * e**2) @ X @ xtx * len(y) / (len(y) - 2)
    return float(b[1]), float(b[1] / np.sqrt(cov[1, 1]))


def weights(macro_w: pd.DataFrame, as_of: pd.Timestamp, ff: pd.DataFrame | None = None) -> dict:
    if ff is None:
        if not calendar_values.FF_HISTORY.exists():
            return {"fehler": "ForexFactory-Historie fehlt"}
        ff = pd.read_parquet(calendar_values.FF_HISTORY)
    if "US.2y" not in macro_w:
        return {"fehler": "US.2y fehlt"}
    y2 = macro_w["US.2y"].dropna()
    y2 = y2[y2.index <= as_of]
    dy = (y2.diff() * 100).rename("dy")  # bp, Tagesaenderung bis Schluss des Termintags
    sur = us_surprises(ff, as_of)
    start = as_of - pd.DateOffset(months=WINDOW_MONTHS)
    sur = sur[sur["datum"] > start].join(dy, on="datum")
    out = {"fenster_monate": WINDOW_MONTHS, "termine": {}}
    for g in GROUPS:
        x = sur[sur["gruppe"] == g]
        b, t = _beta(x["dy"].to_numpy(float), x["z"].to_numpy(float))
        out["termine"][g] = {"bp_je_sd": None if not np.isfinite(b) else round(b, 2),
                             "t": None if not np.isfinite(t) else round(t, 2), "n": int(x["dy"].notna().sum()),
                             "letzter": None if x.empty else x["datum"].max().date().isoformat()}
    bc, bn = (out["termine"][g]["bp_je_sd"] for g in ("CPI", "NFP"))
    if bc is None or bn is None:
        out.update({"anteil_cpi": None, "regime": "zu wenig Termine"})
        return out
    pc, pn = max(bc, 0.0), max(bn, 0.0)
    share = pc / (pc + pn) if pc + pn > 0 else 0.5
    out["anteil_cpi"] = round(share, 2)
    out["regime"] = ("Inflation dominiert (CPI wichtiger)" if share >= DOMINANT else
                     "Arbeitsmarkt dominiert (NFP wichtiger)" if share <= 1 - DOMINANT else "ausgeglichen")
    return out


def tag(title: str, currency: str, w: dict) -> str | None:
    """Gewicht fuer einen anstehenden US-Termin, z. B. 'CPI 64 %'."""
    if currency != "USD" or not w or w.get("anteil_cpi") is None:
        return None
    for g, keys in UPCOMING.items():
        if any(k in title for k in keys) and not title.startswith("ADP"):
            share = w["anteil_cpi"] if g == "CPI" else 1 - w["anteil_cpi"]
            return f"{g}-Gewicht {share * 100:.0f} %"
    return None
