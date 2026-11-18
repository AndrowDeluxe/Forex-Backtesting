"""Gold-Richtungs-Komposition: Stufe 0 (Ueberlappung) und Stufe A (Richtung) -- Plan 18.11.2026.

    python scripts/research_gold_komposition.py --stage overlap     # Stufe 0, nur IS
    python scripts/research_gold_komposition.py --stage direction   # Stufe A, IS waehlen, OOS vergleichen

Lock `gold_richtung_komposition`: IS 2010–2019, OOS bis 18.05.2026 (frei), Tresor bis 18.11.2026
(nur informativ: fuer den MACRO-Block am 15.11. schon geoeffnet), Blind 2006–2009, Forward bis 31.03.2027.

VORAB FESTGELEGT (vor dem ersten Lauf, 18.11.2026):
- Stufe 0: Stimmen zweier Bausteine mit |Spearman| >= 0,6 (Wochenwerte, IS) gelten als doppelt; behalten wird
  der fruehere in der Reihenfolge Z, M, R2, RR, C.
- Stufe A: Entscheidung am Tag t mit Daten < t, Rendite Gold Schluss t -> Schluss t+h (h = 5, 20), log.
  Kennzahl je Variante: mittlere Rendite in Signalrichtung je Signaltag (bp/Tag), Trefferquote, Abdeckung.
  Kontrollen: (1) „immer long“ = mittlere Rendite aller Tage der Periode; (2) zirkulaere Verschiebung der
  Richtungsreihe gegen die Renditen (500 Verschiebungen, mind. 250 Tage), p = Anteil >= Ist.
  BESTANDEN, wenn in IS **und** OOS: Signal > immer long, und p <= 0,05 (IS) bzw. <= 0,10 (OOS), fuer h = 20.
- Varianten: Z20, Z10, Z5, Z20-twistfest × Regeln K1, K2, K3 = 12 (+ 5 Einzelbausteine als Info) = 17 Versuche.
"""

from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fusion_lab.filters.gold_komposition import BAUSTEINE, REGELN, combine, macro_series, vote_frame  # noqa: E402
from research_lock import Lock  # noqa: E402

LOCK = Lock("gold_richtung_komposition")
LOCK.register_split("2010-01-01", "2019-12-31", "2026-05-18", "2026-11-18")
LOCK.register_blind("2006-01-01", "2009-12-31")
OUT = ROOT / "fusion_lab" / "data" / "gold_komposition"
Z_VARIANTEN = {"Z20": (20, True), "Z10": (10, True), "Z5": (5, True), "Z20tf": (20, False)}
HORIZONTE = (5, 20)
_CACHE: dict = {}


def votes(name: str) -> pd.DataFrame:
    if "macro" not in _CACHE:
        _CACHE["macro"] = macro_series()
    if name not in _CACHE:
        lag, tw = Z_VARIANTEN[name]
        _CACHE[name] = vote_frame(lag, tw, macro=_CACHE["macro"])
    return _CACHE[name]


def fwd_returns() -> pd.DataFrame:
    """Log-Renditen Schluss t -> t+h; Spot (Dukascopy, ab 2009), sonst GC=F (davor und nach Spot-Ende)."""
    from fusion_lab.gold_confirm.data import load
    spot = load("spot")["Close"].dropna()
    gc = load("yf")["gc_close"].dropna()
    out = {}
    for h in HORIZONTE:
        rs = np.log(spot).shift(-h) - np.log(spot)
        rg = np.log(gc).shift(-h) - np.log(gc)
        out[h] = rs.combine_first(rg)
    return pd.DataFrame(out).sort_index()


def kennzahlen(d: pd.Series, r: pd.Series, h: int, rng: np.random.Generator, n_shift: int = 500) -> dict:
    x = pd.concat([d, r], axis=1, keys=["d", "r"]).dropna()
    sig = x[x["d"] != 0]
    if len(sig) < 30:
        return {"n_sig": len(sig)}
    ist = float((sig["d"] * sig["r"]).mean())
    dd, rr = x["d"].to_numpy(), x["r"].to_numpy()
    shifts = rng.integers(250, max(len(x) - 250, 251), n_shift)
    null = []
    for k in shifts:
        ds = np.roll(dd, k)
        m = ds != 0
        null.append((ds[m] * rr[m]).mean() if m.any() else 0.0)
    p = float((np.array(null) >= ist).mean())
    return {"n_sig": len(sig), "abdeckung_%": round(len(sig) / len(x) * 100), "long_%": round((sig["d"] > 0).mean() * 100),
            "bp/T": round(ist / h * 1e4, 2), "immer_long_bp/T": round(float(x["r"].mean()) / h * 1e4, 2),
            "treffer_%": round(float(((sig["d"] * sig["r"]) > 0).mean()) * 100, 1), "p_shift": round(p, 3)}


def stage_overlap() -> None:
    v = LOCK.is_only(votes("Z20"))
    wk = v.resample("W-FRI").last()
    corr = wk.corr(method="spearman").round(2)
    print("Stufe 0 -- Stimmen, Spearman (Wochenwerte, IS 2010–2019):\n", corr.to_string())
    from fusion_lab.gold_confirm.data import load
    spot = load("spot")["Close"]
    mom = np.sign(np.log(spot).diff(20)).reindex(v.index, method="ffill")
    print("\nKorrelation mit dem Vorzeichen des 20-T-Gold-Momentums (gleiches Fenster):\n",
          v.apply(lambda s: s.corr(mom, method="spearman")).round(2).to_string())
    print("\nAnteil Tage mit Stimme != 0 (IS):\n", (v != 0).mean().round(2).to_string())
    doppelt = [(a, b, corr.loc[a, b]) for a, b in itertools.combinations(BAUSTEINE, 2) if abs(corr.loc[a, b]) >= 0.6]
    raus = sorted({b for a, b, _ in doppelt})
    print("\n|rho| >= 0,6:", doppelt or "keine", "-> raus:", raus or "keiner")
    OUT.mkdir(parents=True, exist_ok=True)
    corr.to_csv(OUT / "stage0_corr.csv")
    (OUT / "stage0_raus.txt").write_text(",".join(raus), encoding="utf-8")


def stage_direction() -> None:
    raus_f = OUT / "stage0_raus.txt"
    raus = [x for x in raus_f.read_text(encoding="utf-8").split(",") if x] if raus_f.exists() else []
    bausteine = tuple(b for b in BAUSTEINE if b not in raus)
    print("Bausteine nach Stufe 0:", bausteine)
    r = fwd_returns()
    rng = np.random.default_rng(20261118)
    rows = []
    varianten = [(z, rule) for z in Z_VARIANTEN for rule in REGELN]
    LOCK.log_trials(len(varianten) + len(bausteine), "Stufe A: 4 Z-Varianten x 3 Regeln + Einzelbausteine")
    def run(label, d):
        for h in HORIZONTE:
            for per, sl in (("IS", LOCK.is_only), ("OOS", LOCK.oos_only)):
                k = kennzahlen(sl(d.reindex(r.index)), sl(r[h]), h, rng)
                rows.append({"variante": label, "h": h, "periode": per, **k})
    for b in bausteine:
        run(f"nur {b}", votes("Z20")[b])
    for z, rule in varianten:
        bs = tuple(b if b != "Z" else "Z" for b in bausteine)
        run(f"{z}·{rule}", combine(votes(z), rule, bs))
    t = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    t.to_csv(OUT / "stageA_direction.csv", index=False)
    piv = t.pivot_table(index=["variante", "h"], columns="periode",
                        values=["bp/T", "immer_long_bp/T", "treffer_%", "p_shift", "abdeckung_%", "long_%"])
    pd.set_option("display.width", 250)
    print(piv.round(2).to_string())
    ok = []
    for lab in t["variante"].unique():
        a = t[(t.variante == lab) & (t.h == 20)].set_index("periode")
        if {"IS", "OOS"} <= set(a.index) and "bp/T" in a and a["bp/T"].notna().all():
            if (a.loc["IS", "bp/T"] > a.loc["IS", "immer_long_bp/T"] and a.loc["OOS", "bp/T"] > a.loc["OOS", "immer_long_bp/T"]
                    and a.loc["IS", "p_shift"] <= 0.05 and a.loc["OOS", "p_shift"] <= 0.10):
                ok.append(lab)
    print("\nBESTANDEN (h 20, Kriterium vorab):", ok or "keine")
    print("Versuche gesamt:", LOCK.trials)


# ------------------------------------------------------------------ Stufe B: Veto auf bestehende Gold-Edges
# VORAB FESTGELEGT (18.11.2026, vor dem Lauf):
# - Edges: Gold ASB und Daily-C2 Gold (Trade-Saetze aus research_gold_confirm, TTP-Kosten), CTNL-Reversal
#   Live-Set (Ribbon + Spike >= SPIKE_MIN_ATR, research_ctnl_confirm_wf.trades()-Cache).
# - Veto = Trade entfaellt, wenn die Richtung am Einstiegstag (Daten < Tag) GEGEN die Trade-Seite zeigt.
# - Messlatte: M allein (Makro-Veto). Eine Komposition BESTEHT auf einem Edge, wenn in IS und OOS
#   (a) die behaltenen Trades im Schnitt mehr R bringen als mit M allein und
#   (b) die gesperrten Trades im Schnitt negativ sind.
# - Versuche: 12 Kompositionen x 3 Edges = 36.

def edge_trades() -> dict[str, pd.DataFrame]:
    sys.path.insert(0, str(ROOT / "scripts"))
    import research_gold_confirm as rgc
    from gold_smc_htf_ltf.spike_gate import SPIKE_MIN_ATR
    c = pd.read_pickle(rgc.OUT / "ctnl_live_set.pkl")
    c = c[c["spike"] >= SPIKE_MIN_ATR]
    ctnl = pd.DataFrame({"tag": pd.to_datetime(c["et"]).dt.normalize(), "seite": np.sign(c["direction"]).astype(int),
                         "r": c["r"]})
    return {"Gold ASB": rgc.asb_trades(), "Daily-C2 Gold": rgc.c2_trades(), "CTNL-Reversal live": ctnl}


def _stats(r: pd.Series) -> tuple[int, float, float]:
    r = r.dropna()
    if len(r) < 2:
        return len(r), float("nan"), float("nan")
    return len(r), round(float(r.mean()), 3), round(float(r.mean() / r.std(ddof=1) * np.sqrt(len(r))), 2)


def stage_edges() -> None:
    edges = edge_trades()
    varianten = {"M allein": ("Z20", "M")} | {f"{z}·{rule}": (z, rule) for z in Z_VARIANTEN for rule in REGELN}
    LOCK.log_trials(12 * len(edges), "Stufe B: 12 Kompositionen als Veto auf 3 Gold-Edges")
    rows = []
    for ename, t in edges.items():
        t = t.dropna(subset=["r"]).copy()
        t["tag"] = pd.to_datetime(t["tag"]).dt.tz_localize(None).dt.normalize() if getattr(
            pd.to_datetime(t["tag"]).dt, "tz", None) else pd.to_datetime(t["tag"]).dt.normalize()
        t = t.set_index("tag").sort_index()
        for vname, (z, rule) in varianten.items():
            v = votes(z)
            d = v["M"] if rule == "M" else combine(v, rule)
            pos = d.index.searchsorted(t.index, side="right") - 1  # Tageszeile = Daten < Tag
            dirn = np.where(pos >= 0, d.values[np.clip(pos, 0, None)], 0)
            weg = (dirn != 0) & (dirn == -t["seite"].values)
            row = {"edge": ename, "variante": vname}
            for per, sl in (("IS", LOCK.is_only), ("OOS", LOCK.oos_only)):
                k, w, a = sl(t[~weg])["r"], sl(t[weg])["r"], sl(t)["r"]
                nb, rb, tb = _stats(k)
                nw, rw, _ = _stats(w)
                row.update({f"{per}_n": len(a), f"{per}_R_alle": round(float(a.mean()), 3) if len(a) else np.nan,
                            f"{per}_n_beh": nb, f"{per}_R_beh": rb, f"{per}_t_beh": tb, f"{per}_n_weg": nw, f"{per}_R_weg": rw})
            rows.append(row)
    res = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    res.to_csv(OUT / "stageB_edges.csv", index=False)
    pd.set_option("display.width", 250)
    cols = ["edge", "variante", "IS_n", "IS_R_alle", "IS_n_weg", "IS_R_weg", "IS_R_beh", "IS_t_beh",
            "OOS_n", "OOS_R_alle", "OOS_n_weg", "OOS_R_weg", "OOS_R_beh", "OOS_t_beh"]
    print(res[cols].to_string(index=False))
    ok = []
    for ename in edges:
        e = res[res.edge == ename].set_index("variante")
        mb = e.loc["M allein"]
        for vname in e.index.drop("M allein"):
            x = e.loc[vname]
            if all(x[f"{p}_R_beh"] > mb[f"{p}_R_beh"] and x[f"{p}_R_weg"] < 0 for p in ("IS", "OOS")):
                ok.append(f"{ename}: {vname}")
    print("\nBESTANDEN (vorab: besser als M allein in IS+OOS, gesperrte Trades negativ):", ok or "keine")
    print("Versuche gesamt:", LOCK.trials)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["overlap", "direction", "edges"], required=True)
    a = ap.parse_args()
    {"overlap": stage_overlap, "direction": stage_direction, "edges": stage_edges}[a.stage]()
