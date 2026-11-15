"""Gold Confirmation Score -- Nachbau + Backtest (Nutzerauftrag 14.11.2026, Plan freigegeben).

    python scripts/research_gold_confirm.py --stage data      # Stufe 0: Abdeckung + Korrelation der Bausteine (IS)
    python scripts/research_gold_confirm.py --stage single    # Stufe 1: Einzelbausteine -> Gold-Forward-Rendite (IS)
    python scripts/research_gold_confirm.py --stage edge      # Stufe 2: Score als eigener Edge (IS + OOS-Vergleich)
    python scripts/research_gold_confirm.py --stage filter    # Stufe 3: Score/Bloecke als Veto auf ASB, C2, CTNL
    python scripts/research_gold_confirm.py --stage combo     # Stufe 4: Kombination mit Zins/Trend/COT/ASB-Filtern
    python scripts/research_gold_confirm.py --stage robust    # Stufe 5: MC/Bootstrap/Jahresreihe der Kandidaten

Lock `gold_confirm_v1`: IS 2010-2019, OOS bis 10.05.2026, Tresor bis 10.11.2026 (bleibt zu, nur nach Rueckfrage).
Ergebnisse: fusion_lab/data/gold_confirm/results/*.csv
"""

from __future__ import annotations

import argparse
import itertools
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fusion_lab.gold_confirm.components import CATALOG, _cftc, _on, normalize  # noqa: E402
from fusion_lab.gold_confirm.data import load  # noqa: E402
from fusion_lab.gold_confirm.score import WEIGHTS, build  # noqa: E402
from research_lock import Lock, deflated_sharpe  # noqa: E402

warnings.filterwarnings("ignore")
LOCK = Lock("gold_confirm_v1")
SPLIT = ("2010-01-01", "2019-12-31", "2026-05-10", "2026-11-10")
OUT = ROOT / "fusion_lab" / "data" / "gold_confirm" / "results"
COMPS = list(CATALOG)
BLOCKS = list(WEIGHTS)


def frame() -> pd.DataFrame:
    p = ROOT / "fusion_lab" / "data" / "gold_confirm" / "score_frame.parquet"
    if p.exists():
        return pd.read_parquet(p)
    f = build()
    f.to_parquet(p)
    return f


def tstat(x: pd.Series) -> float:
    x = x.dropna()
    return float(x.mean() / x.std(ddof=1) * np.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else float("nan")


# ------------------------------------------------------------------ Stufe 0

def stage_data() -> None:
    f = LOCK.is_only(frame())
    cov = pd.DataFrame({"ab": f[COMPS].apply(lambda s: s.first_valid_index()).dt.date,
                        "abdeckung_IS_%": (f[COMPS].notna().mean() * 100).round(0),
                        "block": [CATALOG[c][0] for c in COMPS], "pdf": [CATALOG[c][2] for c in COMPS]})
    print("Abdeckung je Baustein (IS):\n", cov.to_string())
    # Wochenwerte, damit die woechentlichen CFTC-Bausteine nicht durch ffill kuenstlich korrelieren
    wk = f[COMPS].resample("W-FRI").last()
    corr = wk.corr(method="spearman").round(2)
    print("\nSpearman-Korrelation (Wochenwerte, IS):\n", corr.to_string())
    hi = [(a, b, corr.loc[a, b]) for a, b in itertools.combinations(COMPS, 2) if abs(corr.loc[a, b]) >= 0.4]
    print("\n|rho| >= 0,4 (Doppelzaehlung):", hi or "keine")
    mom = np.log(load("spot")["Close"]).diff(20).rename("gold_mom20")
    rho_mom = f[COMPS].apply(lambda s: s.corr(mom.reindex(s.index), method="spearman")).round(2)
    print("\nKorrelation mit Gold-Momentum 20 T (selbes Fenster):\n", rho_mom.to_string())
    OUT.mkdir(parents=True, exist_ok=True)
    cov.join(rho_mom.rename("rho_gold_mom20")).to_csv(OUT / "stage0_coverage.csv")
    corr.to_csv(OUT / "stage0_corr.csv")


# ------------------------------------------------------------------ Stufe 1

HORIZONS = (1, 5, 20)


def fwd_returns(close: pd.Series) -> pd.DataFrame:
    """Rendite vom Schluss t+1 ... nein: Einstieg Open t+1 ~ Schluss t (Gold handelt fast durch); Rendite
    Schluss t -> Schluss t+h. Score vom Schluss t ist bekannt, also kein Vorgriff."""
    lc = np.log(close)
    return pd.DataFrame({h: lc.shift(-h) - lc for h in HORIZONS})


def ic_table(comp: pd.DataFrame, close: pd.Series, cols: list[str]) -> pd.DataFrame:
    fr = fwd_returns(close)
    rows = []
    for c in cols:
        for h in HORIZONS:
            d = pd.concat([comp[c], fr[h]], axis=1, keys=["x", "y"]).dropna()
            if len(d) < 200:
                continue
            ic = d["x"].corr(d["y"], method="spearman")
            n_eff = len(d) / h  # ueberlappende Renditen
            t_ic = ic * np.sqrt(max(n_eff - 2, 1)) / np.sqrt(max(1 - ic ** 2, 1e-9))
            q = pd.cut(d["x"], [-0.01, 1 / 3, 2 / 3, 1.01], labels=["tief", "mitte", "hoch"])
            g = d.groupby(q, observed=True)["y"].mean() * 1e4 / h  # bp je Tag
            rows.append({"baustein": c, "h": h, "n": len(d), "IC": round(ic, 3), "t_IC": round(t_ic, 2),
                         "bp/T tief": round(g.get("tief", np.nan), 1), "bp/T mitte": round(g.get("mitte", np.nan), 1),
                         "bp/T hoch": round(g.get("hoch", np.nan), 1)})
    return pd.DataFrame(rows)


def silver_cftc() -> tuple[pd.DataFrame, pd.Series]:
    """Uebertragbarkeit: CFTC-Bausteine fuer Silber, gegen Silber-Forward-Rendite (SI=F)."""
    yf = load("yf")
    si = yf["si_close"].dropna()
    days = si.index[si.index >= "2009-01-01"]
    c = _cftc(days, "SILVER")
    out = pd.DataFrame(index=days)
    out["f_mm"] = normalize(_on(c["mm"].diff(4) / c["oi"], days))
    out["f_other"] = normalize(_on(c["other"].diff(4) / c["oi"], days))
    slv = yf["slv_close"]  # SLV-Bestand nicht frei -> Silber-ETF-Fluss entfaellt
    gld_like = None  # noqa: F841
    return out, si.reindex(days)


def stage_single() -> None:
    f = frame()
    close = load("spot")["Close"]
    n_trials = len(COMPS + BLOCKS + ["score"]) * len(HORIZONS)
    LOCK.log_trials(n_trials, "Stufe 1: Bausteine/Bloecke/Score x 3 Horizonte, IC auf IS")
    tab = ic_table(LOCK.is_only(f), close, COMPS + BLOCKS + ["score"])
    tab["block"] = tab["baustein"].map(lambda c: CATALOG[c][0] if c in CATALOG else "-")
    print("Stufe 1, IS 2010-2019: IC Baustein -> Gold-Forward-Rendite\n", tab.to_string(index=False))
    OUT.mkdir(parents=True, exist_ok=True)
    tab.to_csv(OUT / "stage1_ic_is.csv", index=False)
    # OOS zum Vergleich (frei seit 10.11.)
    tab_o = ic_table(LOCK.oos_only(f), close, COMPS + BLOCKS + ["score"])
    tab_o.to_csv(OUT / "stage1_ic_oos.csv", index=False)
    m = tab.merge(tab_o, on=["baustein", "h"], suffixes=("_IS", "_OOS"))
    print("\nIS gegen OOS (nur IC/t):\n", m[["baustein", "h", "IC_IS", "t_IC_IS", "IC_OOS", "t_IC_OOS"]].to_string(index=False))
    # Silber-Uebertrag
    sc, si = silver_cftc()
    LOCK.log_trials(2 * len(HORIZONS), "Stufe 1: Silber-Uebertrag f_mm/f_other")
    ts = ic_table(LOCK.is_only(sc), si, ["f_mm", "f_other"])
    print("\nSilber (CFTC-Bausteine -> SI=F), IS:\n", ts.to_string(index=False))
    ts.to_csv(OUT / "stage1_silver_is.csv", index=False)


# ------------------------------------------------------------------ Stufe 2: Score als eigener Edge

COST_PRICE = 0.30        # Round-Trip Spread+Slippage in USD/oz (wie htf_daily_trade, XAUUSD)
SWAP_PA = 0.03           # Haltekosten je Seite, pauschal 3 % p. a. auf den Nominalwert (Annahme, dokumentiert)
SL_ATR, TP_R, MAX_DAYS = 1.5, 2.0, 20
EXIT_NEUTRAL = 50
M15_FILES = ["GOLD_M15_2009-01-01_2016-01-01.parquet", "GOLD_M15_2016-01-01_2026-11-01.parquet"]


def daily() -> pd.DataFrame:
    d = load("spot")[["Open", "High", "Low", "Close"]].copy()
    tr = pd.concat([d.High - d.Low, (d.High - d.Close.shift()).abs(), (d.Low - d.Close.shift()).abs()], axis=1).max(axis=1)
    d["atr"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    return d


_H1: dict[str, pd.DataFrame] = {}


def h1() -> pd.DataFrame:
    if not _H1:
        m = pd.concat([pd.read_parquet(ROOT / "data_cache" / "combined" / f) for f in M15_FILES])
        m.index = pd.to_datetime(m.index).tz_convert("UTC").tz_localize(None)
        m = m[~m.index.duplicated(keep="last")].sort_index()
        _H1["x"] = m.resample("1h").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()
    return _H1["x"]


def ltf_trigger(day: pd.Timestamp, side: int) -> tuple[pd.Timestamp, float] | None:
    """E3: Asia-Range 00-07 UTC des Tages; erster H1-Schluss jenseits der Range in `side`-Richtung zwischen
    07 und 20 UTC -> Einstieg zum Open der naechsten H1-Kerze."""
    x = h1().loc[day: day + pd.Timedelta(hours=23)]
    asia, rest = x[x.index.hour < 7], x[(x.index.hour >= 7) & (x.index.hour < 20)]
    if len(asia) < 4 or len(rest) < 2:
        return None
    hi, lo = asia.High.max(), asia.Low.min()
    hit = rest[(rest.Close > hi)] if side > 0 else rest[(rest.Close < lo)]
    if hit.empty:
        return None
    nxt = x.index[x.index > hit.index[0]]
    return (nxt[0], float(x.loc[nxt[0], "Open"])) if len(nxt) else None


def signals(s: pd.Series, thr: int, cadence: str, mode: str) -> pd.Series:
    """Richtung je Tag t (Stand Schluss t). state = Zustand, cross = nur am Tag des Schwellen-Kreuzens."""
    hi, lo = thr, 100 - thr
    d = pd.Series(np.where(s >= hi, 1, np.where(s <= lo, -1, 0)), index=s.index).where(s.notna(), 0)
    if mode == "cross":
        d = d.where(d != d.shift(1).fillna(0), 0)
    if cadence == "weekly":
        d = d.where(d.index.dayofweek == 4, 0)
    return d.astype(int)


def simulate(sig: pd.Series, s: pd.Series, entry: str, exit_mode: str, d: pd.DataFrame | None = None) -> pd.DataFrame:
    d = daily() if d is None else d
    days = d.index
    sig = sig.reindex(days).fillna(0).astype(int)
    s = s.reindex(days)
    trades, i, n = [], 0, len(days)
    while i < n - 1:
        side = sig.iloc[i]
        if side == 0:
            i += 1
            continue
        sig_day, atr, c0 = days[i], d.atr.iloc[i], d.Close.iloc[i]
        fill = None
        if entry in ("E1", "E4"):
            fill = (i + 1, d.Open.iloc[i + 1], days[i + 1])
        elif entry == "E2":
            lim = c0 - side * 0.5 * atr
            for k in range(i + 1, min(i + 4, n)):
                if (side > 0 and d.Low.iloc[k] <= lim) or (side < 0 and d.High.iloc[k] >= lim):
                    px = min(d.Open.iloc[k], lim) if side > 0 else max(d.Open.iloc[k], lim)
                    fill = (k, px, days[k])
                    break
        elif entry == "E3":
            for k in range(i + 1, min(i + 4, n)):
                t = ltf_trigger(days[k], side)
                if t:
                    fill = (k, t[1], t[0])
                    break
        if fill is None:
            i += 1
            continue
        k, px, t_in = fill
        risk = SL_ATR * atr
        sl = px - side * risk
        tp = px + side * TP_R * risk if exit_mode == "X1" else None
        out, why, j = None, None, k
        # Fuell-Tag: Stop zaehlt (konservativ), Ziel nur bei Market-Open-Einstieg
        if entry == "E3":
            rest = h1().loc[t_in: days[k] + pd.Timedelta(hours=23)]
            lo_, hi_ = rest.Low.min(), rest.High.max()
        else:
            lo_, hi_ = d.Low.iloc[k], d.High.iloc[k]
        if (side > 0 and lo_ <= sl) or (side < 0 and hi_ >= sl):
            out, why = sl, "sl"
        elif tp is not None and entry in ("E1", "E4") and ((side > 0 and hi_ >= tp) or (side < 0 and lo_ <= tp)):
            out, why = tp, "tp"
        while out is None:
            # Ausstieg am Open j+1, wenn Score am Schluss j neutral/gegen ist oder Zeitstopp
            if j - k + 1 >= MAX_DAYS or j >= n - 1:
                out, why = (d.Close.iloc[j], "time") if j >= n - 1 else (d.Open.iloc[j + 1], "time")
                j = min(j + 1, n - 1)
                break
            sc = s.iloc[j]
            if sc == sc and ((side > 0 and sc < EXIT_NEUTRAL) or (side < 0 and sc > 100 - EXIT_NEUTRAL)):
                out, why = d.Open.iloc[j + 1], "score"
                j += 1
                break
            j += 1
            o, h_, l_ = d.Open.iloc[j], d.High.iloc[j], d.Low.iloc[j]
            if (side > 0 and o <= sl) or (side < 0 and o >= sl):
                out, why = o, "sl_gap"
            elif (side > 0 and l_ <= sl) or (side < 0 and h_ >= sl):
                out, why = sl, "sl"
            elif tp is not None and ((side > 0 and h_ >= tp) or (side < 0 and l_ <= tp)):
                out, why = (o if (side > 0 and o >= tp) or (side < 0 and o <= tp) else tp), "tp"
        nights = max((days[j] - days[k]).days, 0)
        r_gross = side * (out - px) / risk
        r = r_gross - COST_PRICE / risk - SWAP_PA * px * nights / 365 / risk
        trades.append({"signal": sig_day, "tag": days[k], "seite": side, "kurs": px, "ausstieg": out, "grund": why,
                       "tage": j - k, "r_brutto": r_gross, "r": r})
        i = j + 1 if why in ("score", "time", "sl_gap") else j + 1
    return pd.DataFrame(trades)


def stats(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) == 0:
        return {"n": 0}
    eq = r.cumsum()
    win, loss = r[r > 0].sum(), -r[r < 0].sum()
    return {"n": len(r), "avg_R": round(r.mean(), 3), "sum_R": round(r.sum(), 1), "t": round(tstat(r), 2),
            "PF": round(win / loss, 2) if loss > 0 else np.nan, "hit_%": round((r > 0).mean() * 100, 0),
            "maxDD_R": round((eq - eq.cummax()).min(), 1)}


EDGE_GRID = list(itertools.product([65, 80], ["daily", "weekly"], ["E1", "E2", "E3", "E4"], ["X1", "X2"]))


def edge_variant(s: pd.Series, thr: int, cad: str, ent: str, ex: str) -> pd.DataFrame:
    sig = signals(s, thr, cad, "cross" if ent == "E4" else "state")
    return simulate(sig, s, ent, ex)


def split_stats(t: pd.DataFrame) -> dict:
    t = t.set_index("tag")
    is_, oos = LOCK.is_only(t), LOCK.oos_only(t)
    a, b = stats(is_["r"]), stats(oos["r"])
    return {**{f"IS_{k}": v for k, v in a.items()}, **{f"OOS_{k}": v for k, v in b.items()}}


def stage_edge() -> None:
    f = frame()
    s = f["score"]
    LOCK.log_trials(len(EDGE_GRID), "Stufe 2: Score-Edge 2 Schwellen x 2 Takte x 4 Entries x 2 Exits")
    rows, all_trades = [], []
    for thr, cad, ent, ex in EDGE_GRID:
        t = edge_variant(s, thr, cad, ent, ex)
        if t.empty:
            continue
        t["variante"] = f"{thr}_{cad}_{ent}_{ex}"
        all_trades.append(t)
        rows.append({"variante": t["variante"].iloc[0], "thr": thr, "takt": cad, "entry": ent, "exit": ex,
                     "long_%": round((t.seite > 0).mean() * 100), **split_stats(t)})
    # Kontrollen (nicht gezaehlt, keine Auswahl): immer long, 20-T-Momentum mit derselben Mechanik
    d = daily()
    mom = np.log(d.Close).diff(20)
    controls = {"K_immer_long": pd.Series(100.0, index=d.index),
                "K_momentum20": (50 + 50 * np.sign(mom)).where(mom.notna())}
    for name, cs in controls.items():
        t = edge_variant(cs, 65, "daily", "E1", "X1")
        t["variante"] = name
        all_trades.append(t)
        rows.append({"variante": name, "thr": 65, "takt": "daily", "entry": "E1", "exit": "X1",
                     "long_%": round((t.seite > 0).mean() * 100), **split_stats(t)})
    res = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    res.to_csv(OUT / "stage2_edge.csv", index=False)
    pd.concat(all_trades).to_csv(OUT / "stage2_trades.csv", index=False)
    cols = ["variante", "long_%", "IS_n", "IS_avg_R", "IS_t", "IS_PF", "IS_maxDD_R", "OOS_n", "OOS_avg_R", "OOS_t", "OOS_PF"]
    print(res[cols].sort_values("IS_t", ascending=False).to_string(index=False))


# ------------------------------------------------------------------ Stufe 3: Veto auf bestehende Edges

def asb_trades() -> pd.DataFrame:
    """Gold ASB, eingefrorene Basis: 2010-15 neu erzeugt (mit Richtung, wie im Blindtest 18.10.),
    11/2016-09/2026 aus is_reopt_trades_cost.csv (TTP-Kosten)."""
    cache = OUT / "asb_trades.csv"
    if cache.exists():
        return pd.read_csv(cache, parse_dates=["tag"])
    sys.path.insert(0, str(ROOT / "scripts"))
    import research_gold_asb_paper_filters as pf
    days, m5 = pf.build_days(*pf.load_pre2016())
    days = pf.add_features(days, m5)
    t0 = pf.trades_for(days, m5)
    a = pd.DataFrame({"tag": pd.to_datetime(t0["window_end"]).dt.tz_localize(None).dt.normalize(),
                      "seite": t0["dir"].astype(int), "r": t0["R"]})
    a = a[(a.tag >= "2010-01-01") & (a.tag <= "2015-12-31")]
    b = pd.read_csv(ROOT / "asian_range_breakout" / "results" / "is_reopt_trades_cost.csv")
    b = pd.DataFrame({"tag": pd.to_datetime(b["time"].str[:10]), "seite": b["dir"].astype(int), "r": b["r"]})
    out = pd.concat([a, b], ignore_index=True).sort_values("tag")
    out.to_csv(cache, index=False)
    return out


def c2_trades() -> pd.DataFrame:
    hd = ROOT / "htf_daily_trade"
    a = pd.read_csv(hd / "c2_blind_trades.csv")
    a = a[a.markt == "XAUUSD"]
    b = pd.read_csv(hd / "c2_bis_heute_trades.csv")
    b = b[(b.markt == "XAUUSD") & (b.variante == "EL")]
    out = pd.concat([pd.DataFrame({"tag": pd.to_datetime(a.einstieg), "seite": np.where(a.seite == "long", 1, -1), "r": a.r_TTP}),
                     pd.DataFrame({"tag": pd.to_datetime(b.einstieg), "seite": np.where(b.seite == "long", 1, -1), "r": b.r_TTP})])
    return out.sort_values("tag").reset_index(drop=True)


def ctnl_trades() -> pd.DataFrame:
    p = OUT / "ctnl_reversal_trades.csv"
    if not p.exists():
        return pd.DataFrame(columns=["tag", "seite", "r"])
    t = pd.read_csv(p)
    side_col = next(c for c in ("direction", "dir", "side") if c in t)
    side = t[side_col]
    side = np.where(side.astype(str).str.lower().isin(["1", "long", "buy", "1.0"]), 1, -1)
    rcol = next(c for c in ("r_live", "R", "r", "pnl_r") if c in t)
    tag = pd.to_datetime(t["entry_time"], utc=True).dt.tz_localize(None).dt.normalize()
    return pd.DataFrame({"tag": tag, "seite": side, "r": t[rcol]})


EDGES = {"ASB": asb_trades, "C2": c2_trades, "CTNL": ctnl_trades}
VETO_COLS = ["score", *BLOCKS]


def prior_value(series: pd.Series, tags: pd.Series) -> np.ndarray:
    """Wert vom letzten Handelstag strikt vor `tag` (Score am Schluss t-1 -> Trade am Tag t)."""
    s = series.dropna()
    pos = s.index.searchsorted(pd.DatetimeIndex(tags), side="left") - 1
    vals = np.where(pos >= 0, s.values[np.clip(pos, 0, None)], np.nan)
    return vals


def attach_scores(t: pd.DataFrame, f: pd.DataFrame) -> pd.DataFrame:
    t = t.copy()
    for c in VETO_COLS:
        t[c] = prior_value(f[c] * (1 if c == "score" else 100), t["tag"])
    return t


def veto_masks(t: pd.DataFrame, hi: float = 65, lo: float = 35) -> dict[str, np.ndarray]:
    m = {}
    for c in VETO_COLS:
        v = t[c].values
        dirn = np.where(v >= hi, 1, np.where(v <= lo, -1, 0))
        m[f"{c}: kein Trade gegen"] = ~((dirn != 0) & (dirn == -t["seite"].values))
        m[f"{c}: nur mit"] = dirn == t["seite"].values
    return m


def keep_vs_drop(t: pd.DataFrame, mask: np.ndarray) -> dict:
    t = t.set_index("tag")
    out = {}
    for per, sl in (("IS", LOCK.is_only), ("OOS", LOCK.oos_only)):
        k, d = sl(t[mask]), sl(t[~mask])
        a, b = stats(k["r"]), stats(d["r"])
        out.update({f"{per}_n_beh": a.get("n", 0), f"{per}_R_beh": a.get("avg_R"), f"{per}_t_beh": a.get("t"),
                    f"{per}_DD_beh": a.get("maxDD_R"), f"{per}_n_weg": b.get("n", 0), f"{per}_R_weg": b.get("avg_R")})
    return out


def stage_filter(edges: list[str] | None = None) -> None:
    f = frame()
    rows = []
    for name, fn in EDGES.items():
        if edges and name not in edges:
            continue
        t = fn()
        if t.empty:
            print(f"{name}: keine Trades (CTNL-Cache fehlt?)")
            continue
        t = attach_scores(t, f).dropna(subset=["score"])
        masks = veto_masks(t)
        LOCK.log_trials(len(masks), f"Stufe 3: Veto-Varianten auf {name}")
        rows.append({"edge": name, "variante": "Basis", **keep_vs_drop(t, np.ones(len(t), bool))})
        for k, m in masks.items():
            rows.append({"edge": name, "variante": k, **keep_vs_drop(t, m)})
    res = pd.DataFrame(rows)
    p = OUT / "stage3_veto.csv"
    if edges and p.exists():  # Teil-Lauf: andere Edges in der Datei behalten
        old = pd.read_csv(p)
        res = pd.concat([old[~old.edge.isin(res.edge.unique())], res], ignore_index=True)
    res.to_csv(p, index=False)
    cols = ["edge", "variante", "IS_n_beh", "IS_R_beh", "IS_t_beh", "IS_n_weg", "IS_R_weg",
            "OOS_n_beh", "OOS_R_beh", "OOS_t_beh", "OOS_n_weg", "OOS_R_weg"]
    print(res[cols].to_string(index=False))


# ------------------------------------------------------------------ main

# ------------------------------------------------------------------ Stufe 4: Kombination mit bisherigen Filtern

def trend_directions(d: pd.DataFrame) -> pd.DataFrame:
    """T3 SMA200, T5 Ribbon, T6 Faber, T7 Weekly EMA 9/21 -- gleiche Logik wie htf_daily_trade/filter_matrix.trend_dirs,
    auf dem XAUUSD-D1 dieses Projekts (Stand Tagesschluss)."""
    from htf_daily_trade.filter_matrix import _htf
    c = d["Close"]
    sgn = lambda s: np.sign(s).fillna(0).astype(int)  # noqa: E731
    out = pd.DataFrame(index=d.index)
    out["T3_SMA200"] = sgn(c - c.rolling(200).mean())
    wk = _htf(c, "W-FRI")
    w50 = wk.ewm(span=50, adjust=False).mean().shift(1).reindex(d.index, method="ffill")
    e50, e200 = c.ewm(span=50, adjust=False).mean(), c.ewm(span=200, adjust=False).mean()
    out["T5_Ribbon"] = ((c > e50) & (c > e200) & (c > w50)).astype(int) - ((c < e50) & (c < e200) & (c < w50)).astype(int)
    mo = _htf(c, "ME")
    out["T6_Faber"] = sgn((mo - mo.rolling(10).mean()).shift(1).reindex(d.index, method="ffill"))
    out["T7_WEMA9_21"] = sgn((wk.ewm(span=9, adjust=False).mean() - wk.ewm(span=21, adjust=False).mean())
                             .shift(1).reindex(d.index, method="ffill"))
    si = load("yf")["si_close"]
    si = si.reindex(d.index.union(si.index)).ffill().reindex(d.index)
    out["ASB_Silber5"] = sgn(si.diff(5))  # Gold-ASB-Filter: Silber 5 T in Trade-Richtung
    return out


def combo_dirs(tags: pd.Series) -> pd.DataFrame:
    from fusion_lab.filters.cot_flow import CotFlowFilter
    from fusion_lab.filters.zinskurve_regime import GoldZinskurvenFilter
    td = trend_directions(daily())
    out = pd.DataFrame({c: prior_value(td[c].astype(float), tags) for c in td}, index=tags.index)
    z, cot = GoldZinskurvenFilter(), CotFlowFilter(n=4)
    out["Zins_Kurve"] = [z.direction(t) for t in tags]
    out["COT_Fluss4"] = [cot.direction("XAUUSD", t) for t in tags]
    return out


def combo_bases() -> dict[str, pd.DataFrame]:
    """Basen fuer Stufe 4 (vorab festgelegt): bester Score-Edge aus Stufe 2 (IS-t), seine Long-Variante
    (Befund Stufe 2: Short verliert in IS und OOS -> gezaehlte Variante) und Gold ASB mit Score-Veto."""
    tr = pd.read_csv(OUT / "stage2_trades.csv", parse_dates=["tag", "signal"])
    best = "65_daily_E2_X1"
    a = tr[tr.variante == best][["tag", "seite", "r"]].reset_index(drop=True)
    f = frame()
    asb = attach_scores(asb_trades(), f).dropna(subset=["score"])
    sdir = np.where(asb.score >= 65, 1, np.where(asb.score <= 35, -1, 0))
    asb_veto = asb[~((sdir != 0) & (sdir == -asb.seite))][["tag", "seite", "r"]].reset_index(drop=True)
    return {f"Score {best}": a, f"Score {best} nur long": a[a.seite > 0].reset_index(drop=True),
            "ASB + Score-Veto": asb_veto}


def stage_combo() -> None:
    rows = []
    bases = combo_bases()
    for name, t in bases.items():
        dirs = combo_dirs(t["tag"])
        LOCK.log_trials(len(dirs.columns) + (1 if "nur long" in name else 0), f"Stufe 4: {name} x Filter")
        rows.append({"basis": name, "filter": "-", **keep_vs_drop(t, np.ones(len(t), bool))})
        for c in dirs:
            m = ~((dirs[c].values != 0) & (dirs[c].values == -t["seite"].values))  # nicht gegen den Filter
            rows.append({"basis": name, "filter": f"{c} (nicht gegen)", **keep_vs_drop(t, m)})
            m2 = dirs[c].values == t["seite"].values
            rows.append({"basis": name, "filter": f"{c} (nur mit)", **keep_vs_drop(t, m2)})
        LOCK.log_trials(len(dirs.columns), f"Stufe 4: {name} x Filter (nur-mit-Variante)")
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "stage4_combo.csv", index=False)
    cols = ["basis", "filter", "IS_n_beh", "IS_R_beh", "IS_t_beh", "IS_DD_beh", "OOS_n_beh", "OOS_R_beh", "OOS_t_beh"]
    print(res[cols].to_string(index=False))


# ------------------------------------------------------------------ Stufe 6: Risikoskalierung CTNL nach MACRO (15.11.)
# Eigene Sperre: gold_confirm_v1 ist eingefroren. Idee stammt aus dem Tresor-Ergebnis -> Tresor hier NICHT
# unabhaengig (nur der Vollstaendigkeit halber ausgewiesen). Gilt nur IS -> OOS, danach Forward.
LOCK_SIZE = Lock("gold_confirm_v2_sizing")

SIZING = {  # name -> (veto, gewicht_mit_long, gewicht_mit_short, gewicht_neutral)
    "A Basis": (False, 1, 1, 1),
    "B Veto": (True, 1, 1, 1),
    "C Veto + 2x mit Makro (beide)": (True, 2, 2, 1),
    "D Veto + 2x mit Makro (nur Long)": (True, 2, 1, 1),
    "E Veto + 2x mit Makro (nur Short)": (True, 1, 2, 1),
    "F Nur mit Makro (beide)": (True, 1, 1, 0),
    "G Nur mit Makro (nur Long)": (True, 1, 0, 0),
    "H 2x mit Makro ohne Veto": (False, 2, 2, 1),
}


def sized(t: pd.DataFrame, cfg) -> pd.Series:
    veto, wl, ws, wn = cfg
    d = np.where(t.MACRO >= 65, 1, np.where(t.MACRO <= 35, -1, 0))
    mit, gegen = d == t.seite.values, (d != 0) & (d == -t.seite.values)
    w = np.where(gegen, 0 if veto else 1, np.where(mit, np.where(t.seite.values > 0, wl, ws), wn)).astype(float)
    return pd.Series(t.r.values * w, index=t.tag.values), pd.Series(w, index=t.tag.values)


def size_stats(r: pd.Series, w: pd.Series) -> dict:
    r, w = r[w > 0], w[w > 0]
    if len(r) < 3:
        return {"n": len(r)}
    eq = r.cumsum(); dd = float((eq - eq.cummax()).min())
    rng = np.random.default_rng(11); mc = []
    for _ in range(2000):
        e = rng.permutation(r.values).cumsum(); mc.append((e - np.maximum.accumulate(e)).min())
    yrs = max((r.index.max() - r.index.min()).days / 365.25, 0.5)
    return {"n": len(r), "risk_einh": round(w.sum(), 0), "sum_R": round(r.sum(), 1), "R_je_Einh": round(r.sum() / w.sum(), 3),
            "t": round(tstat(r), 2), "maxDD": round(dd, 1), "MC_DD95": round(float(np.percentile(mc, 5)), 1),
            "R_pro_Jahr": round(r.sum() / yrs, 1), "sum/MC_DD95": round(r.sum() / -np.percentile(mc, 5), 2)}


def stage_sizing() -> None:
    LOCK_SIZE.register_split(*SPLIT)
    t = attach_scores(ctnl_trades(), frame()).dropna(subset=["MACRO"]).sort_values("tag")
    LOCK_SIZE.log_trials(len(SIZING) - 2, "Stufe 6: Risikoskalierung/Nur-mit auf CTNL (A/B Referenz)")
    rows, yearly = [], {}
    for name, cfg in SIZING.items():
        r, w = sized(t, cfg)
        for per, sl in (("IS", LOCK_SIZE.is_only), ("OOS", LOCK_SIZE.oos_only)):
            rows.append({"variante": name, "periode": per, **size_stats(sl(r), sl(w))})
        tr = (r.index >= "2026-05-11") & (r.index <= "2026-11-10")
        rows.append({"variante": name, "periode": "Tresor*", **size_stats(r[tr], w[tr])})
        yearly[name] = r.groupby(r.index.year).sum().round(1)
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "stage6_sizing.csv", index=False)
    print(res.to_string(index=False))
    print("\nSumme R je Jahr:\n", pd.DataFrame(yearly).to_string())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["data", "single", "edge", "filter", "combo", "robust", "sizing"])
    ap.add_argument("--edges", default="", help="Stufe 3: nur diese Edges, z. B. ASB,C2")
    a = ap.parse_args()
    LOCK.register_split(*SPLIT)
    if a.stage == "sizing":
        return stage_sizing()
    if a.stage == "filter":
        return stage_filter([e for e in a.edges.split(",") if e] or None)
    {"data": stage_data, "single": stage_single, "edge": stage_edge, "filter": stage_filter, "combo": stage_combo}[a.stage]()


if __name__ == "__main__":
    main()
