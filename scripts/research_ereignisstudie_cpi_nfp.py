"""CPI/NFP-Ereignisstudie: Regeln aus der OneNote-Makro-Education pruefen (Plan 26.11.2026).

    python -m scripts.research_ereignisstudie_cpi_nfp

H1  CPI bewegt USD/Zinsen je Ueberraschungseinheit staerker als NFP (Blueprint 2024).
H2  Core-CPI erklaert die Reaktion besser als Headline (Blueprint, Macro Report 2024).
H3  Inflationsueberraschung staerkt die Waehrung nur ohne Wachstumsschwaeche (Top Down 12.05.2024),
    Drift 1/3/5 Tage nach dem Termin, G8, Einstieg 1 h nach Termin wie Remy A3.
H4  "Neutral bis Freitag" (Macro Report 20.10.2024): verlieren unsere Beine ueber US-CPI/NFP-Termine?

Overfitting-Sperre: Lock `ereignis_cpi_nfp_v1` (H1-H3, IS 2007-2018, OOS bis 25.05.2026, Tresor zu) und
`ereignis_sperre_beine_v1` (H4, IS 2016-2021, OOS bis 25.05.2026). Kriterium "traegt": IS t >= 2 und OOS
gleiches Vorzeichen mit t >= 1. Ergebnis-CSV: fusion_lab/data/research/ereignisstudie/.
"""

from __future__ import annotations

import itertools
from pathlib import Path

import numpy as np
import pandas as pd

from research_lock import Lock, deflated_sharpe
from scripts.remy_common import HALF_SPREAD
from scripts.research_remy_a3_surprise import INVERT, MIN_IS_EVENTS, PAIR, load_h1, parse_value, trades

ROOT = Path(__file__).resolve().parents[1]
FF = ROOT / "data_cache/remy/ff_calendar.parquet"
COMB = ROOT / "data_cache/combined"
LEGS = ROOT / "portfolio_construction/results/live_2016"
OUT = ROOT / "fusion_lab/data/research/ereignisstudie"

LOCK = Lock("ereignis_cpi_nfp_v1")
LOCK_LEGS = Lock("ereignis_sperre_beine_v1")
SPLIT = ("2007-01-01", "2018-12-31", "2026-05-25", "2026-11-25")
SPLIT_LEGS = ("2016-01-01", "2021-12-31", "2026-05-25", "2026-11-25")

US_CPI, US_CORE, US_NFP = "CPI m/m", "Core CPI m/m", "Non-Farm Employment Change"
REACT_MIN = 60
ASSETS = {  # Asset -> (feine Datei-Muster, grobe Datei-Muster)
    "EURUSD": (["EURUSD_M5_2016-01-01_2026-10-28"], ["EURUSD_H1_2007-01-01_2026-11-10"]),
    "USDJPY": (["USDJPY_M5_2016-01-01_2026-10-28"], ["USDJPY_H1_2007-01-01_2026-11-10"]),
    "GOLD": (["GOLD_M1_20*"], ["GOLD_H1_2009-06-01_2026-11-01"]),
    "NASDAQ": (["NASDAQ_M1_*"], []),
}
H3_VARIANTS = list(itertools.product((0.5, 1.0), (24, 72, 120)))  # |z| x Haltedauer in H1-Kerzen (1/3/5 Tage)
H4_WINDOWS = ("offen_ueber_termin", "einstieg_termintag_vorher", "einstieg_termintag_nachher")
H4_LEGS = {"ttp": None, "fk": ["gold_silver"]}  # je Bein genau ein Konto
# Datenpruefung nach Lauf 1 (26.11.): Corona-NFP-Ueberraschungen ergeben |z| > 20 und machen das Beta wertlos
# -> Kappung wie im Fact Sheet (panels.SURPRISE_CLIP); Welch-t erst ab 10 markierten Trades.
Z_CLIP = 3.0
MIN_MARK = 10


# --- Daten ---------------------------------------------------------------------------------------
def load_bars(patterns: list[str]) -> pd.DataFrame | None:
    files = sorted({p for pat in patterns for p in COMB.glob(f"{pat}.parquet")})
    if not files:
        return None
    d = pd.concat([pd.read_parquet(f, columns=["Open", "Close"]) for f in files]).sort_index()
    return d[~d.index.duplicated(keep="last")]


def zscores(ff: pd.DataFrame, is_end: str, names: set[str] | None = None, ccy: set[str] | None = None,
            high_only: bool = True) -> pd.DataFrame:
    """Ueberraschung je Termin, auf die IS-Streuung des Indikators normiert (wie A3, aber nicht gruppiert)."""
    ev = ff
    if high_only:
        ev = ev[ev["impact"] == "high"]
    if names:
        ev = ev[ev["name"].isin(names)]
    if ccy:
        ev = ev[ev["currency"].isin(ccy)]
    a, f = ev["actual"].map(parse_value), ev["forecast"].map(parse_value)
    ok = a.notna() & f.notna()
    ev, a, f = ev[ok].copy(), a[ok], f[ok]
    same = np.array([x[1] == y[1] for x, y in zip(a, f)], dtype=bool)
    ev = ev[same].assign(raw=[x[0] - y[0] for x, y in zip(a[same], f[same])])
    ev["key"] = ev["currency"] + "|" + ev["name"]
    is_ev = ev[ev["time"] <= pd.Timestamp(is_end, tz="UTC") + pd.Timedelta(days=1)]
    sc = is_ev.groupby("key")["raw"].agg(["std", "size"])
    sc = sc[(sc["size"] >= MIN_IS_EVENTS) & (sc["std"] > 0)]["std"]
    ev = ev[ev["key"].isin(sc.index)]
    ev["z"] = (np.where(ev["name"].str.contains(INVERT), -1.0, 1.0) * ev["raw"] / ev["key"].map(sc)).clip(-Z_CLIP, Z_CLIP)
    return ev


def price_change(bars: pd.DataFrame, t: pd.Timestamp, minutes: int = REACT_MIN) -> float:
    """Log-Rendite vom letzten Kurs vor t bis t+minutes. Liegt t mitten in einer Kerze (H1), zaehlt deren
    Open als Vorher-Kurs; Nachher = Schluss der letzten Kerze, die vor t+minutes beginnt."""
    idx = bars.index
    i = idx.searchsorted(t, side="right") - 1
    if i < 1:
        return np.nan
    pre = bars["Close"].iloc[i - 1] if idx[i] == t else bars["Open"].iloc[i]
    if t - idx[i] > pd.Timedelta(hours=1):  # Luecke vor dem Termin
        return np.nan
    j = idx.searchsorted(t + pd.Timedelta(minutes=minutes), side="left") - 1
    if j <= i - (idx[i] == t) or idx[j] - t > pd.Timedelta(minutes=minutes):
        return np.nan
    return float(np.log(bars["Close"].iloc[j] / pre))


def reactions(times: pd.Series, bars: dict) -> pd.DataFrame:
    rows = []
    for t in times:
        r = {"time": t}
        for a, (fine, coarse) in bars.items():
            v = np.nan
            for b in (fine, coarse):
                if b is not None and len(b) and b.index[0] <= t <= b.index[-1]:
                    v = price_change(b, t)
                    if np.isfinite(v):
                        r[f"{a}_quelle"] = "fein" if b is fine else "H1"
                        break
            r[a] = v * 1e4
        rows.append(r)
    return pd.DataFrame(rows).set_index("time")


def us2y_change() -> pd.Series:
    from fusion_lab.macro_data import store
    m = store.read_all("macro")
    s = m[m["key"] == "US.2y"].sort_values("fetched_at").drop_duplicates("date", keep="last")
    s = s.set_index(pd.to_datetime(s["date"]))["value"].astype(float).sort_index()
    return s.diff() * 100  # bp


# --- Statistik ------------------------------------------------------------------------------------
def ols(y: np.ndarray, X: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """OLS mit HC1-Standardfehlern; gibt (beta, t, R2)."""
    ok = np.isfinite(y) & np.isfinite(X).all(axis=1)
    y, X = y[ok], X[ok]
    n, k = X.shape
    if n <= k + 2:
        return np.full(k, np.nan), np.full(k, np.nan), np.nan
    xtx = np.linalg.inv(X.T @ X)
    b = xtx @ X.T @ y
    e = y - X @ b
    cov = xtx @ (X.T * e**2) @ X @ xtx * n / (n - k)
    r2 = 1 - (e @ e) / ((y - y.mean()) @ (y - y.mean()))
    return b, b / np.sqrt(np.diag(cov)), r2


def welch_t(a: pd.Series, b: pd.Series) -> float:
    if len(a) < MIN_MARK or len(b) < MIN_MARK:
        return np.nan
    return (a.mean() - b.mean()) / np.sqrt(a.var() / len(a) + b.var() / len(b))


def periods(df: pd.DataFrame, lock: Lock) -> dict[str, pd.DataFrame]:
    return {"IS": lock.is_only(df), "OOS": lock.oos_only(df)}


# --- H1/H2 ----------------------------------------------------------------------------------------
def h1_h2(ff: pd.DataFrame, bars: dict, y2: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ev = zscores(ff, SPLIT[1], {US_CPI, US_CORE, US_NFP}, {"USD"}, high_only=False)
    piv = ev.pivot_table(index="time", columns="name", values="z", aggfunc="mean")
    react = reactions(pd.Series(piv.index), bars)
    react["US2Y"] = [y2.get(t.tz_localize(None).normalize(), np.nan) for t in react.index]
    data = piv.join(react)
    data.to_csv(OUT / "h1_h2_termine.csv")
    assets = list(bars) + ["US2Y"]
    rows1, rows2 = [], []
    for per, d in periods(data, LOCK).items():
        for a in assets:
            res = {}
            for lab, col in (("CPI", US_CPI), ("NFP", US_NFP)):
                sub = d[d[col].notna()]
                b, t, r2 = ols(sub[a].to_numpy(float), np.c_[np.ones(len(sub)), sub[col].to_numpy(float)])
                res[lab] = (b[1], t[1], r2, int(sub[a].notna().sum()))
            # Interaktion: gemeinsame Regression, Differenz |b| ueber Vorzeichen des CPI-Effekts gepolt
            sub = d[d[US_CPI].notna() | d[US_NFP].notna()]
            z = sub[US_CPI].fillna(sub[US_NFP]).to_numpy(float)
            cpi = sub[US_CPI].notna().to_numpy(float)
            b, t, _ = ols(sub[a].to_numpy(float), np.c_[np.ones(len(sub)), cpi, z, z * cpi])
            # Ausrichtung an der gemeinsamen Richtung beider Termine (NFP und CPI koennen gegenlaeufig wirken)
            pooled = ols(sub[a].to_numpy(float), np.c_[np.ones(len(sub)), z])[0][1]
            sign = np.sign(pooled) if np.isfinite(pooled) and pooled != 0 else 1.0
            rows1.append({"periode": per, "asset": a,
                          "b_CPI": res["CPI"][0], "t_CPI": res["CPI"][1], "R2_CPI": res["CPI"][2], "n_CPI": res["CPI"][3],
                          "b_NFP": res["NFP"][0], "t_NFP": res["NFP"][1], "R2_NFP": res["NFP"][2], "n_NFP": res["NFP"][3],
                          "diff_b": b[3] * sign, "t_diff": t[3] * sign})
            sub = d[d[US_CPI].notna() & d[US_CORE].notna()]
            b, t, r2 = ols(sub[a].to_numpy(float), np.c_[np.ones(len(sub)), sub[US_CORE], sub[US_CPI]])
            rc = ols(sub[a].to_numpy(float), np.c_[np.ones(len(sub)), sub[US_CORE]])[2]
            rh = ols(sub[a].to_numpy(float), np.c_[np.ones(len(sub)), sub[US_CPI]])[2]
            rows2.append({"periode": per, "asset": a, "b_core": b[1], "t_core": t[1], "b_head": b[2], "t_head": t[2],
                          "R2_beide": r2, "R2_core": rc, "R2_head": rh, "n": int(sub[a].notna().sum())})
    return data, pd.DataFrame(rows1), pd.DataFrame(rows2)


# --- H3 -------------------------------------------------------------------------------------------
def growth_weak(ff: pd.DataFrame) -> pd.DataFrame:
    """Je Waehrung die zuletzt veroeffentlichten PMI-/GDP-Ist-Werte als Zeitreihe (Zeit = Veroeffentlichung)."""
    g = ff[ff["name"].str.contains(r"Manufacturing PMI|GDP q/q", regex=True)
           & ~ff["name"].str.contains("Flash|Chicago|Richmond|Empire|Philly", regex=True)].copy()
    v = g["actual"].map(parse_value)
    g = g[v.notna()].assign(v=[x[0] for x in v[v.notna()]])
    g["art"] = np.where(g["name"].str.contains("PMI"), "pmi", "gdp")
    return g[["time", "currency", "art", "v"]].sort_values("time")


def weak_at(g: pd.DataFrame, ccy: str, t: pd.Timestamp) -> bool | None:
    """Wachstumsschwaeche = letzter PMI < 50 ODER letztes GDP q/q <= 0, nur vor t veroeffentlichte Werte."""
    x = g[(g["currency"] == ccy) & (g["time"] < t)]
    if x.empty:
        return None
    pmi = x[x["art"] == "pmi"]["v"]
    gdp = x[x["art"] == "gdp"]["v"]
    flags = []
    if len(pmi):
        flags.append(pmi.iloc[-1] < 50)
    if len(gdp):
        flags.append(gdp.iloc[-1] <= 0)
    return any(flags) if flags else None


def stats(r: pd.Series) -> dict:
    sr = r.mean() / r.std() if len(r) > 1 and r.std() > 0 else np.nan
    return {"n": len(r), "avg_bp": r.mean() * 1e4, "t": sr * np.sqrt(len(r)) if np.isfinite(sr) else np.nan,
            "sr": sr, "skew": r.skew(), "kurt": r.kurt() + 3}


def h3(ff: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    ev = zscores(ff, SPLIT[1])
    ev = ev[ev["name"].str.contains("CPI")]
    sig = ev.groupby(["time", "currency"], as_index=False).agg(z=("z", "mean"), names=("name", " + ".join))
    g = growth_weak(ff)
    sig["schwach"] = [weak_at(g, c, t) for c, t in zip(sig["currency"], sig["time"])]
    sig = sig[sig["schwach"].notna()]
    h1 = load_h1()
    rows, best = [], {}
    for per, s in periods(sig.set_index("time"), LOCK).items():
        s = s.reset_index()
        for zmin, hold in H3_VARIANTS:
            for weak in (False, True):
                tr = trades(s[s["schwach"] == weak], h1, zmin, hold)
                st = stats(tr["ret"]) if len(tr) else {"n": 0}
                key = f"|z|>={zmin} {hold // 24}T"
                rows.append({"periode": per, "variante": key, "schwaeche": weak, **st,
                             "erste_stunde_bp": tr["react"].mean() * 1e4 if len(tr) else np.nan})
                if per == "IS" and not weak:
                    best[key] = st
    LOCK.log_trials(len(H3_VARIANTS), "H3 IS: |z| x Haltedauer, Gruppe ohne Wachstumsschwaeche")
    return pd.DataFrame(rows), best


# --- H4 -------------------------------------------------------------------------------------------
def leg_trades() -> pd.DataFrame:
    parts = []
    for acc, only in H4_LEGS.items():
        t = pd.read_parquet(LEGS / f"{acc}_trades.parquet")
        parts.append(t[t["leg"].isin(only)] if only else t)
    return pd.concat(parts, ignore_index=True)


def flag_trades(tr: pd.DataFrame, ev_times: pd.DatetimeIndex) -> pd.DataFrame:
    """Markierung je Trade; Zeiten naive UTC."""
    ev = np.sort(ev_times.to_numpy())
    et, xt = tr["entry_time"].to_numpy(), tr["exit_time"].to_numpy()
    nxt = np.searchsorted(ev, et, side="right")  # erster Termin nach dem Einstieg
    nxt_t = np.where(nxt < len(ev), ev[np.minimum(nxt, len(ev) - 1)], np.datetime64("NaT", "ns"))
    prv = np.searchsorted(ev, et, side="right") - 1  # letzter Termin <= Einstieg
    prv_t = np.where(prv >= 0, ev[np.maximum(prv, 0)], np.datetime64("NaT", "ns"))
    day = tr["entry_time"].dt.normalize().to_numpy()
    out = tr.copy()
    out["offen_ueber_termin"] = (nxt < len(ev)) & (nxt_t < xt)
    out["einstieg_termintag_vorher"] = (nxt < len(ev)) & (pd.DatetimeIndex(nxt_t).normalize().to_numpy() == day)
    out["einstieg_termintag_nachher"] = (prv >= 0) & (pd.DatetimeIndex(prv_t).normalize().to_numpy() == day)
    return out


def h4(ff: pd.DataFrame) -> pd.DataFrame:
    us = ff[(ff["currency"] == "USD") & ff["name"].isin({US_CPI, US_NFP})]
    ev_times = pd.DatetimeIndex(us["time"].dt.tz_convert(None).unique())
    tr = flag_trades(leg_trades(), ev_times).set_index("entry_time").sort_index()
    rows = []
    for per, d in periods(tr, LOCK_LEGS).items():
        for leg, x in d.groupby("leg"):
            for w in H4_WINDOWS:
                m, u = x[x[w]]["r"], x[~x[w]]["r"]
                rows.append({"periode": per, "bein": leg, "fenster": w, "n_mark": len(m), "R_mark": m.mean(),
                             "n_rest": len(u), "R_rest": u.mean(), "t": welch_t(m, u),
                             "sumR_mark": m.sum(), "sumR_gesamt": x["r"].sum()})
    LOCK_LEGS.log_trials(len(H4_WINDOWS) * tr["leg"].nunique(), "H4 IS: Fenster x Bein")
    return pd.DataFrame(rows)


def verdict(is_t: float, oos_t: float, sign: float = 0.0) -> str:
    """sign = erwartete Richtung (+1/-1), 0 = beide Richtungen zaehlen."""
    if not (np.isfinite(is_t) and np.isfinite(oos_t)):
        return "zu wenig Daten"
    if abs(is_t) >= 2 and np.sign(oos_t) == np.sign(is_t) and abs(oos_t) >= 1:
        if sign and np.sign(is_t) != sign:
            return "Gegenteil traegt"
        return "traegt"
    return "traegt nicht"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    LOCK.register_split(*SPLIT)
    LOCK_LEGS.register_split(*SPLIT_LEGS)
    ff = pd.read_parquet(FF)
    pd.set_option("display.width", 220)

    bars = {a: (load_bars(f), load_bars(c) if c else None) for a, (f, c) in ASSETS.items()}
    data, t1, t2 = h1_h2(ff, bars, us2y_change())
    t1.to_csv(OUT / "h1_cpi_vs_nfp.csv", index=False)
    t2.to_csv(OUT / "h2_core_vs_headline.csv", index=False)
    print("Quellen der Reaktion:", {a: data[f"{a}_quelle"].value_counts().to_dict() for a in ASSETS
                                    if f"{a}_quelle" in data})
    print("\nH1  CPI gegen NFP (bp je 1 SD Ueberraschung, Reaktion +60 Min.; 2J = Tagesaenderung)")
    print(t1.round(3).to_string(index=False))
    print("\nH2  Core gegen Headline an CPI-Terminen")
    print(t2.round(3).to_string(index=False))

    t3, best = h3(ff)
    t3.to_csv(OUT / "h3_bedingte_drift.csv", index=False)
    print("\nH3  Drift nach CPI-Ueberraschung, getrennt nach Wachstumsschwaeche (netto nach Kosten)")
    print(t3.round(3).to_string(index=False))
    if best:
        bk = max(best, key=lambda k: best[k].get("t", -np.inf) if np.isfinite(best[k].get("t", np.nan)) else -np.inf)
        b = best[bk]
        srs = pd.Series([v["sr"] for v in best.values()], dtype=float)
        dsr = deflated_sharpe(b["sr"], int(b["n"]), LOCK.trials, b["skew"], b["kurt"], sr_var_trials=float(srs.var()))
        print(f"H3 beste IS-Variante ohne Schwaeche: {bk}  t {b['t']:.2f}  DSR {dsr:.2f} (Versuche {LOCK.trials})")

    t4 = h4(ff)
    t4.to_csv(OUT / "h4_termin_sperre_beine.csv", index=False)
    print("\nH4  Beine ueber US-CPI/NFP-Termine (R je Trade, markiert gegen Rest)")
    print(t4.round(3).to_string(index=False))

    print("\nUrteile (IS t >= 2 und OOS gleiches Vorzeichen mit t >= 1):")
    for a in ("EURUSD", "USDJPY", "US2Y", "GOLD", "NASDAQ"):
        x = t1.set_index(["periode", "asset"])
        print(f"  H1 {a}: CPI staerker als NFP -> {verdict(x.loc[('IS', a), 't_diff'], x.loc[('OOS', a), 't_diff'], 1)}"
              f" (t_diff IS {x.loc[('IS', a), 't_diff']:.2f}, OOS {x.loc[('OOS', a), 't_diff']:.2f})")
        y = t2.set_index(["periode", "asset"])
        core_ok = all(abs(y.loc[(p, a), "b_core"]) > abs(y.loc[(p, a), "b_head"]) for p in ("IS", "OOS"))
        v = verdict(y.loc[("IS", a), "t_core"], y.loc[("OOS", a), "t_core"])
        print(f"  H2 {a}: Core -> {v if core_ok else 'traegt nicht (Headline mind. gleich stark)'}")
    x = t3[~t3["schwaeche"]].set_index(["variante", "periode"])
    for k in dict.fromkeys(t3["variante"]):
        print(f"  H3 {k} ohne Schwaeche -> {verdict(x.loc[(k, 'IS'), 't'], x.loc[(k, 'OOS'), 't'])}")
    x = t4.set_index(["bein", "fenster", "periode"])
    for (leg, w) in dict.fromkeys(zip(t4["bein"], t4["fenster"])):
        ti, to = x.loc[(leg, w, "IS"), "t"], x.loc[(leg, w, "OOS"), "t"]
        v = verdict(ti, to)
        if v == "traegt" and ti < 0:
            print(f"  H4 SPERR-KANDIDAT {leg} / {w}: IS t {ti:.2f}, OOS t {to:.2f}")
        elif v == "traegt":
            print(f"  H4 {leg} / {w}: Termin-Trades BESSER (IS t {ti:.2f}, OOS t {to:.2f})")
    print("  H4 alle uebrigen Bein/Fenster: kein belastbarer Unterschied")


if __name__ == "__main__":
    main()
