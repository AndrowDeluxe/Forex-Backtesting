"""Dennis' Volumen-Bausteine als FILTER auf den H4-Manipulations-Edge (A6) -- Test 25.11.2026 (Nutzerauftrag 24.11.).

    python -m scripts.research_volumen_kontext_h4

Grundlage: alle H4-Manipulationssignale aus htf_daily_trade/h4_v4_signale.parquet (Sweep >= 2 Kerzen, Koerper zurueck,
Einstieg Folgekerze, Stop am Docht; Ergebnisse g_/r_ = brutto/netto R je Ausstieg). Hier NICHTS neu simuliert, nur
jedem Signal der Volumenkontext zum Schluss der Signalkerze angehaengt (Kerzen mit Start < Einstieg, kein Vorgriff).
Profile: fusion_lab/patterns/volume_profile.py (CME-Tag, VA 70 %, Dukascopy-Tick-Volumen M15).

Merkmale (fuer Short beschrieben; Long gespiegelt), alle aus Dennis' Calls [[smh-dennis-volumen-ltf-inducement-day]]:
  V1 trend_mit    Value laeuft in Trade-Richtung: POC(T-1) < POC(T-2) und VA-Mitte(T-1) < VA-Mitte(T-2)
  V2 inducement   laufender POC des Tages > POC(T-1) (Value wurde gegen den Trade „hochgelockt“)
  V3 poi_va2      Sweep-Extrem (Stop) reicht bis in/ueber VAL(T-2)
  V4 premium      Einstiegskurs ueber VAH(T-1) (Verkauf ausserhalb der gestrigen Value, auf der teuren Seite)
  V5 delta_kipp   Delta-Naeherung der Signalkerze < 0 (Verkaeufer auf der Ablehnungskerze)
  V6 vol_schwach  Tick-Volumen der Signalkerze < Ø der 6 H4-Kerzen davor (Sweep ohne Volumen = Divergenz)
  K  dennis       V1 & V2 & V3 (Kontext des Daily Inducement Day)
Ausstiege: R3 (Ziel 3 R) und Z48 (Zeitausstieg nach 12 H4-Kerzen). 7 x 2 = 14 Varianten, einmal auf allen Signalen,
einmal nur mit Makro-Punkten <= 2 gegen (einziger stabiler H4-Baustein) = 28 gezaehlte Varianten.
Vergleich: Ø R mit vs. ohne Merkmal, zusaetzlich innerhalb gleicher Zellen Markt x Stopweiten-Quartil (CRT-Lehre).
Sperre `volumen_kontext_h4`: IS 2016-2021, OOS bis 2026-05-11, Tresor bis 2026-11-11 (wie h4_manip; zu).
NZDUSD ohne M15-Historie ab 2016 -> ausgelassen.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from fusion_lab.patterns.volume_profile import VA_PCT, Histogram, cme_day, day_profiles
from research_lock import Lock

LOCK = Lock("volumen_kontext_h4")
CACHE = Path("data_cache/smh/volumen_kontext_h4.parquet")
OUT = "scripts/research_volumen_kontext_h4"
SRC = {  # Markt: (Datei, Preisraster)
    "EURUSD": ("EURUSD_M15_2016-01-01_2026-07-29", 0.0001),
    "GBPUSD": ("GBPUSD_M15_2016-01-01_2026-11-01", 0.0001),
    "AUDUSD": ("AUDUSD_M15_2016-01-01_2026-11-01", 0.0001),
    "USDCAD": ("USDCAD_M15_2016-01-01_2026-11-01", 0.0001),
    "USDCHF": ("USDCHF_M15_2016-01-01_2026-11-01", 0.0001),
    "USDJPY": ("USDJPY_M15_2016-01-01_2026-11-01", 0.01),
    "XAUUSD": ("GOLD_M15_2009-06-01_2026-11-01", 0.50),
    "XAGUSD": ("SILVER_M15_2016-01-01_2026-05-28", 0.01),
}
FEATS = ["trend_mit", "inducement", "poi_va2", "premium", "delta_kipp", "vol_schwach", "dennis"]
EXITS = ["R3", "Z48"]


def annotate(m: str, sig: pd.DataFrame) -> pd.DataFrame:
    f, step = SRC[m]
    bars = pd.read_parquet(f"data_cache/combined/{f}.parquet")[["Open", "High", "Low", "Close", "Volume"]]
    bars = bars[~bars.index.duplicated(keep="last")].sort_index()
    prof = day_profiles(bars, step)
    prof["vam"] = (prof["val"] + prof["vah"]) / 2
    pdays = prof.index.to_numpy()
    days = cme_day(bars.index)
    t = bars.index
    o, h, l, c, v = (bars[k].to_numpy() for k in ("Open", "High", "Low", "Close", "Volume"))
    delta = np.sign(c - o) * v
    out = []
    for _, s in sig.iterrows():
        cut = int(t.searchsorted(s["einstieg"].tz_convert("UTC")))      # erste Kerze ab Einstieg (ausgeschlossen)
        k0 = int(t.searchsorted(s["signal"].tz_convert("UTC")))         # erste Kerze der Signal-H4
        if cut <= k0 or cut >= len(t) or k0 < 24 * 4 * 6:
            out.append(None)
            continue
        d = days[cut - 1]
        pi = int(np.searchsorted(pdays, d))
        if pi < 2 or pi >= len(pdays) or pdays[pi] != d:
            out.append(None)
            continue
        p1, p2 = prof.iloc[pi - 1], prof.iloc[pi - 2]
        a = int(np.searchsorted(days, d))                               # Tagesbeginn
        hist = Histogram(l[a:cut].min(), h[a:cut].max(), step)
        for i in range(a, cut):
            hist.add(l[i], h[i], v[i])
        _, poc, _ = hist.poc_va(VA_PCT)
        vol_k = v[k0:cut].sum()
        prev = [v[max(0, k0 - 16 * (j + 1)):k0 - 16 * j].sum() for j in range(6)]
        dl = delta[k0:cut].sum()
        short = s["seite"] == "short"
        sg = 1 if short else -1
        out.append({
            "trend_mit": sg * (p2["poc"] - p1["poc"]) > 0 and sg * (p2["vam"] - p1["vam"]) > 0,
            "inducement": sg * (poc - p1["poc"]) > 0,
            "poi_va2": (s["stop"] >= p2["val"]) if short else (s["stop"] <= p2["vah"]),
            "premium": (s["kurs"] > p1["vah"]) if short else (s["kurs"] < p1["val"]),
            "delta_kipp": sg * dl < 0,
            "vol_schwach": vol_k < np.mean(prev),
        })
    ann = pd.DataFrame([x if x is not None else {} for x in out], index=sig.index)
    ok = pd.Series([x is not None for x in out], index=sig.index)
    res = pd.concat([sig, ann], axis=1)[ok.values]
    res["dennis"] = res["trend_mit"].astype(bool) & res["inducement"].astype(bool) & res["poi_va2"].astype(bool)
    return res


def build() -> pd.DataFrame:
    if CACHE.exists():
        return pd.read_parquet(CACHE)
    sig = pd.read_parquet("htf_daily_trade/h4_v4_signale.parquet")
    keep = ["markt", "seite", "signal", "einstieg", "kurs", "stop", "spanne_atr", "makro_gegen", "periode"] + \
           [f"{p}_{e}" for e in EXITS for p in ("g", "r")]
    parts = []
    for m in SRC:
        res = annotate(m, sig.loc[sig["markt"] == m, keep])
        print(f"{m}: {len(res)} Signale mit Kontext")
        parts.append(res)
    out = pd.concat(parts)
    for col in FEATS:
        out[col] = out[col].astype(bool)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(CACHE)
    return out


def tstat(r: pd.Series) -> float:
    return r.mean() / r.std(ddof=1) * np.sqrt(len(r)) if len(r) > 2 else np.nan


def compare(x: pd.DataFrame) -> pd.DataFrame:
    x = x.copy()
    x["sq"] = x.groupby("markt")["spanne_atr"].transform(lambda s: pd.qcut(s, 4, labels=False, duplicates="drop"))
    rows = {}
    for e in EXITS:
        g, r = f"g_{e}", f"r_{e}"
        for f in FEATS:
            a, b = x[x[f]], x[~x[f]]
            cell = x.groupby(["markt", "sq", f])[g].agg(["mean", "size"]).unstack(f).dropna()
            w = cell[("size", True)]
            matched = np.average(cell[("mean", True)] - cell[("mean", False)], weights=w) if len(w) else np.nan
            per_m = (a.groupby("markt")[g].mean() - b.groupby("markt")[g].mean())
            rows[(e, f)] = {"n_mit": len(a), "anteil%": 100 * len(a) / len(x),
                            "R_brutto_mit": a[g].mean(), "R_brutto_ohne": b[g].mean(),
                            "R_netto_mit": a[r].mean(), "t_netto_mit": tstat(a[r]),
                            "diff_gleiche_zelle": matched,
                            "maerkte_besser": f"{int((per_m > 0).sum())}/{per_m.notna().sum()}"}
    return pd.DataFrame(rows).T


def main() -> None:
    LOCK.register_split("2016-01-01", "2021-12-31", "2026-05-11", "2026-11-11")
    res = build()
    res = res.set_index(res["einstieg"].dt.tz_convert("UTC")).sort_index()
    n = LOCK.log_trials(2 * len(FEATS) * len(EXITS),
                        "7 Volumen-Merkmale x Ausstieg R3/Z48 als Filter auf H4-Signale, alle + nur Makro <= 2 gegen")
    pd.set_option("display.width", 250, "display.max_columns", 30)
    is_, oos = LOCK.is_only(res), LOCK.oos_only(res)
    for name, x in (("IS", is_), ("OOS", oos)):
        tab = compare(x)
        print(f"\n===== {name} (n {len(x)}, Versuche {n}) =====\n{tab.round(3).to_string()}")
        tab.to_csv(f"{OUT}_{name.lower()}.csv")
    # Zusammenspiel mit dem einzigen stabilen H4-Baustein (Makro-Veto, Memory h4-edge-nicht-mechanisch)
    for name, x in (("IS", is_), ("OOS", oos)):
        y = x[x["makro_gegen"] <= 2]
        tab = compare(y)
        print(f"\n===== {name} nur Makro <= 2 gegen (n {len(y)}) =====\n{tab.round(3).to_string()}")


if __name__ == "__main__":
    main()
