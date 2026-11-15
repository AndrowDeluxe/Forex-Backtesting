"""Forward-Ledger: Wahrheitsbuch aller Screener-Aussagen (Regeln: ledger/FORWARD.md).

Zeilenarten
  szenario  berechnetes Szenario A (Limit in der Zone) oder B (Stop ueber Widerstand) eines Tiefen-Kandidaten;
            Spalte `gewaehlt` = vom LLM gewaehltes Szenario.
  referenz  von Hand vorgegebene Szenarien (z. B. NVDA-Analyse 15.11.2026), gleiche Auswertung.
  gruppe    Titel-Gruppen eines Tages (KAUFEN / VERKAUFEN / TOP10), Rendite nach 5/20/60 Kerzen gegen
            Benchmark und gleichgewichtetes Universum.

Auswertung ohne Vorgriff: nur Kerzen NACH dem Datenstand (`stand`). Fuellung A = erste Kerze mit Low <= Einstieg
(Fuellpreis min(Open, Einstieg)), B = High >= Trigger (max(Open, Trigger)). Danach Stopp vor Ziel; auf der
Fuellkerze nur der Stopp; Luecken ueber Stopp/Ziel zum Open; Zeitausstieg nach HOLD_MAX Kerzen zum Schluss.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from fusion_lab.screener import config as C

LEDGER = C.LEDGER_DIR / "ledger.csv"
COLUMNS = ["erstellt", "stand", "screener", "version", "status", "art", "objekt", "szenario", "gewaehlt", "score",
           "signal", "sentiment", "einstieg", "zone_lo", "zone_hi", "stopp", "ziel", "rr", "horizont", "titel",
           "fill_datum", "fill_preis", "exit_datum", "exit_preis", "exit_grund", "ergebnis_r", "ergebnis_pct",
           "bench_pct", "univ_pct", "ausgewertet"]
TEXT_COLUMNS = ["erstellt", "stand", "screener", "version", "status", "art", "objekt", "szenario", "gewaehlt",
                "signal", "titel", "fill_datum", "exit_datum", "exit_grund", "ausgewertet"]


def status(run_day: str) -> str:
    """run_day = Datum des Laufs (nicht Datenstand)."""
    return "forward" if C.FORWARD_START and run_day >= C.FORWARD_START else "probe"


def read(path: Path = LEDGER) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=COLUMNS)
    df = pd.read_csv(path, dtype={"titel": str, "objekt": str})
    for c in COLUMNS:
        if c not in df:
            df[c] = np.nan
    # Leere Spalten liest pandas als float; spaeter eingetragene Daten/Texte wuerden dann scheitern.
    return df[COLUMNS].astype({c: object for c in TEXT_COLUMNS})


def write(df: pd.DataFrame, path: Path = LEDGER) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    df[COLUMNS].to_csv(tmp, index=False)
    tmp.replace(path)


def _open(df: pd.DataFrame, screener: str, objekt: str, szenario: str, art: str, status_: str) -> bool:
    """Offene Zeile mit gleichem Titel/Szenario/Art UND gleichem Status (Probe-Zeilen blockieren Forward nicht)."""
    m = (df["screener"] == screener) & (df["objekt"] == objekt) & (df["szenario"] == szenario) & \
        (df["art"] == art) & (df["status"] == status_) & (df["ausgewertet"].astype(str) != "True")
    return bool(m.any())


def append(rows: list[dict], path: Path = LEDGER) -> int:
    """Haengt neue Zeilen an. Szenario-Zeilen nur, wenn fuer Titel+Szenario keine offene Zeile existiert
    (sonst wuerde ein wochenlang gleiches Setup die Stichprobe aufblaehen)."""
    df = read(path)
    new = []
    for r in rows:
        if r["art"] in ("szenario", "referenz") and _open(df, r["screener"], r["objekt"], r["szenario"], r["art"], r["status"]):
            continue
        if r["art"] == "gruppe" and ((df["art"] == "gruppe") & (df["screener"] == r["screener"]) &
                                     (df["stand"] == r["stand"]) & (df["objekt"] == r["objekt"]) & (df["status"] == r["status"]) &
                                     (df["horizont"] == r["horizont"])).any():
            continue
        new.append({c: r.get(c, np.nan) for c in COLUMNS} | {"ausgewertet": False})
    if new:
        df = pd.concat([df, pd.DataFrame(new)], ignore_index=True) if len(df) else pd.DataFrame(new)
        write(df, path)
    return len(new)


# ------------------------------------------------------------------ Auswertung

def simulate(bars: pd.DataFrame, typ: str, einstieg: float, stopp: float, ziel: float,
             fill_window: int = C.FILL_WINDOW, hold_max: int = C.HOLD_MAX) -> dict | None:
    """bars: Kerzen NACH dem Stand. None = noch nicht entscheidbar."""
    o, h, l, c = (bars[k].to_numpy() for k in ("Open", "High", "Low", "Close"))
    idx = bars.index
    fill_i = fill_px = None
    for i in range(min(fill_window, len(bars))):
        if typ == "A" and l[i] <= einstieg:
            fill_i, fill_px = i, min(o[i], einstieg)
            break
        if typ == "B" and h[i] >= einstieg:
            fill_i, fill_px = i, max(o[i], einstieg)
            break
    if fill_i is None:
        if len(bars) >= fill_window:
            return {"exit_grund": "nicht_gefuellt"}
        return None
    res = {"fill_datum": str(idx[fill_i].date()), "fill_preis": float(fill_px)}
    if l[fill_i] <= stopp:                                   # Fuellkerze: nur Stopp
        return res | {"exit_datum": str(idx[fill_i].date()), "exit_preis": float(min(stopp, fill_px)),
                      "exit_grund": "stopp"}
    for i in range(fill_i + 1, len(bars)):
        if o[i] <= stopp:
            return res | {"exit_datum": str(idx[i].date()), "exit_preis": float(o[i]), "exit_grund": "stopp_luecke"}
        if l[i] <= stopp:
            return res | {"exit_datum": str(idx[i].date()), "exit_preis": float(stopp), "exit_grund": "stopp"}
        if o[i] >= ziel:
            return res | {"exit_datum": str(idx[i].date()), "exit_preis": float(o[i]), "exit_grund": "ziel_luecke"}
        if h[i] >= ziel:
            return res | {"exit_datum": str(idx[i].date()), "exit_preis": float(ziel), "exit_grund": "ziel"}
        if i - fill_i >= hold_max:
            return res | {"exit_datum": str(idx[i].date()), "exit_preis": float(c[i]), "exit_grund": "zeit"}
    return None


def _after(d: pd.DataFrame, stand: str) -> pd.DataFrame:
    return d[d.index > pd.Timestamp(stand)]


def _fwd_return(d: pd.DataFrame | None, stand: str, h: int) -> float | None:
    if d is None:
        return None
    base = d[d.index <= pd.Timestamp(stand)]
    nxt = _after(d, stand)
    if not len(base) or len(nxt) < h:
        return None
    return float(nxt["Close"].iloc[h - 1] / base["Close"].iloc[-1] - 1)


def evaluate(panel: dict[str, pd.DataFrame], screener: str, bench: str, path: Path = LEDGER) -> int:
    """Traegt faellige Ergebnisse fuer diesen Screener nach. panel: Objekt -> Tageskerzen (inkl. Benchmark)."""
    df = read(path)
    if not len(df):
        return 0
    cost = C.COST_BPS[screener] / 1e4
    n = 0
    for k, r in df[(df["screener"] == screener) & (df["ausgewertet"].astype(str) != "True")].iterrows():  # noqa: E712
        if r["art"] in ("szenario", "referenz"):
            d = panel.get(r["objekt"])
            if d is None:
                continue
            res = simulate(_after(d, r["stand"]), r["szenario"], float(r["einstieg"]), float(r["stopp"]),
                           float(r["ziel"]))
            if res is None:
                continue
            for key, v in res.items():
                df.at[k, key] = v
            if "exit_preis" in res:
                fill, ex, st = res["fill_preis"], res["exit_preis"], float(r["stopp"])
                risk = fill - st
                df.at[k, "ergebnis_pct"] = round((ex / fill - 1 - cost) * 100, 3)
                df.at[k, "ergebnis_r"] = round((ex - fill) / risk - cost * fill / risk, 3) if risk > 0 else np.nan
            df.at[k, "ausgewertet"] = True
            n += 1
        elif r["art"] == "gruppe":
            h = int(r["horizont"])
            titles = [t for t in str(r["titel"]).split(";") if t and t != "nan"]
            rets = [x for t in titles if (x := _fwd_return(panel.get(t), r["stand"], h)) is not None]
            b = _fwd_return(panel.get(bench), r["stand"], h)
            if b is None:
                continue                                         # Horizont noch nicht erreicht
            univ = [x for t, d in panel.items() if t != bench and (x := _fwd_return(d, r["stand"], h)) is not None]
            df.at[k, "ergebnis_pct"] = round(float(np.mean(rets)) * 100, 3) if rets else np.nan
            df.at[k, "bench_pct"] = round(b * 100, 3)
            df.at[k, "univ_pct"] = round(float(np.mean(univ)) * 100, 3) if univ else np.nan
            df.at[k, "ausgewertet"] = True
            n += 1
    write(df, path)
    return n


def summary(path: Path = LEDGER) -> dict:
    """Bilanz je Screener und Status fuer Bericht/Dashboard."""
    df = read(path)
    out = {}
    for (scr, st), g in df.groupby(["screener", "status"]):
        sz = g[g["art"].isin(["szenario", "referenz"])]
        done = sz[sz["ausgewertet"].astype(str) == "True"]
        filled = done[done["exit_grund"].notna() & (done["exit_grund"] != "nicht_gefuellt")]
        r = pd.to_numeric(filled["ergebnis_r"], errors="coerce").dropna()
        chosen = filled[filled["gewaehlt"].astype(str) == "True"]
        rc = pd.to_numeric(chosen["ergebnis_r"], errors="coerce").dropna()
        grp = g[(g["art"] == "gruppe") & (g["ausgewertet"].astype(str) == "True")]
        groups = {}
        for (obj, hz), gg in grp.groupby(["objekt", "horizont"]):
            e = pd.to_numeric(gg["ergebnis_pct"], errors="coerce")
            groups[f"{obj}_{int(hz)}"] = {"n": int(e.notna().sum()), "rendite": _r(e.mean()),
                                          "minus_univ": _r((e - pd.to_numeric(gg["univ_pct"], errors="coerce")).mean()),
                                          "minus_bench": _r((e - pd.to_numeric(gg["bench_pct"], errors="coerce")).mean())}
        out[f"{scr}_{st}"] = {
            "szenarien_offen": int((sz["ausgewertet"].astype(str) != "True").sum()),
            "nicht_gefuellt": int((done["exit_grund"] == "nicht_gefuellt").sum()),
            "gefuellt": int(len(r)), "avg_r": _r(r.mean()), "trefferquote": _r((r > 0).mean() * 100),
            "summe_r": _r(r.sum()), "gewaehlt_n": int(len(rc)), "gewaehlt_avg_r": _r(rc.mean()),
            "gruppen": groups,
        }
    return out


def _r(x) -> float | None:
    return None if x is None or pd.isna(x) else round(float(x), 3)
