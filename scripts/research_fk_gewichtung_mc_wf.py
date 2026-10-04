"""FK Instant Funding -- neue Gewichtung per Monte Carlo + Walk-Forward.

Nutzerauftrag 2026-10-03 (nach dem Gesamtportfolio-Backtest 2026, der am
26.08. die 5-%-Trailing-Grenze riss): "Rechne fuer Monte Carlo und Walk
Forward eine neue optimierte Gewichtung aus."

WAS ANDERS IST ALS BEI DER GEWICHTUNG VOM 2026-08-29
(portfolio_construction/results/fk_instant_funding_final.json):
  1. Datengrundlage: Trade-Listen mit ECHTER FK-Ausfuehrung (Kosten, Versatz,
     Gates -- research_fk_gesamtportfolio_2026.py) ueber 2019-01 bis 2026-10
     statt reibungsfreier Kurven ueber 2024-08 bis 2026-07.
  2. Nur die 6 heutigen LIVE_LEGS; die drei ORB-Instrumente bekommen je ein
     EIGENES Gewicht (vorher ein gemeinsamer Topf).
  3. Walk-Forward: verankert, IS 2019..Y-1 -> Gewichte waehlen -> OOS-Jahr Y,
     Y = 2021..2026. Erst das zeigt, ob die Optimierung ueberhaupt etwas
     Uebertragbares findet.

ZIELFUNKTION (wie 08-29): hoechster Median-Jahresertrag unter
P(Trailing-DD >= 5 % innerhalb eines Jahres) <= 1 %, Block-Bootstrap der
Tagesrenditen (Bloecke von 10 Handelstagen, gemeinsame Bloecke fuer alle
Beine -> Korrelation bleibt erhalten).

ENTSCHEIDUNGSVARIABLE: Risiko je Trade in % der Equity = Gewicht x
LEG_RISK_PCT. Ausgewiesen zusaetzlich als CAPITAL_WEIGHT-Wert fuer
fk_instant_funding/paper_bot.py (ORB: Bein-Risiko ist dort 1 %/3 je
Instrument, also CAPITAL_WEIGHT = 3 x Anteil). Harte Grenze: 0,5 % je Trade.

Naeherung im Optimierer: Tagesrenditen additiv (kein Compounding, keine
Lot-Rundung). Die gewaehlte Gewichtung wird danach mit der echten
Ereignis-Simulation (Lot-Rundung, Mindestlot, Kill-Switch) gegengeprueft.
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import research_fk_gesamtportfolio_2026 as fk  # noqa: E402

pb = fk.pb
LEGS = ["gold_asb", "cls_practical", "ctnl_reversal", "orb_sp500", "orb_us30", "orb_nasdaq"]
# Bein-Risiko bei Gewicht 1,0. ORB je Instrument 1 % (der Bridge-Wert 1 %/3 x 3).
UNIT_RISK = {"gold_asb": pb.LEG_RISK_PCT["gold_asb"], "cls_practical": pb.LEG_RISK_PCT["cls_practical"],
             "ctnl_reversal": pb.LEG_RISK_PCT["ctnl_reversal"],
             "orb_sp500": 0.01, "orb_us30": 0.01, "orb_nasdaq": 0.01}
MAX_RISK = pb.MAX_POSITION_LOSS_PCT
CURRENT = {"gold_asb": 0.0606, "cls_practical": 0.1919, "ctnl_reversal": 0.2525,
           "orb_sp500": 0.3737 / 3, "orb_us30": 0.3737 / 3, "orb_nasdaq": 0.3737 / 3}

H0, END = "2019-01-01", fk.END
OOS_YEARS = list(range(2021, 2027))
N_PATHS, HORIZON, BLOCK = 2000, 252, 10
P_BREACH_MAX = 0.01
DD_LIMIT = 0.05
CACHE = REPO / "portfolio_construction" / "results" / "fk_trades_2019_2026_live.csv"
OUT = REPO / "knowledge" / "_data" / "fk_gewichtung_mc_wf.json"


# ------------------------------------------------------------ Trade-Listen
def build_trades(refresh: bool = False) -> pd.DataFrame:
    if CACHE.exists() and not refresh:
        t = pd.read_csv(CACHE, parse_dates=["entry_time", "exit_time"])
        print(f"Trade-Listen aus Cache: {len(t)} Trades")
        return t
    fk.Y0 = pd.Timestamp(H0)
    fk.ORB_M15_START = fk.ORB_M1_START = H0          # = Chunk-Anker der vorhandenen M1-Caches
    fk.CLS_START = "2018-01-01"
    fk.CTNL_START = "2018-01-01"
    t = pd.concat([fk.orb_trades(), fk.gold_asb_trades("live"), fk.cls_trades(), fk.ctnl_trades()],
                  ignore_index=True).sort_values("entry_time").reset_index(drop=True)
    t = t[t["leg"].isin(LEGS)]
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    t.to_csv(CACHE, index=False)
    return t


def daily_matrix(t: pd.DataFrame) -> pd.DataFrame:
    """Tagesrendite je Bein bei Gewicht 1 (Summe R der an dem Tag geschlossenen
    Trades x Bein-Risiko). Werktage, Luecken = 0."""
    days = pd.bdate_range(H0, END)
    d = t.assign(day=t["exit_time"].dt.normalize()).groupby(["day", "leg"])["r"].sum().unstack(fill_value=0.0)
    d = d.reindex(index=days, columns=LEGS, fill_value=0.0).fillna(0.0)
    return d * pd.Series(UNIT_RISK)


# ------------------------------------------------------------ Monte Carlo
def bootstrap_cum(D: np.ndarray, seed: int) -> np.ndarray:
    """Kumulierte Bein-Pfade (Beine, Pfade, Horizont) mit GEMEINSAMEN Bloecken."""
    rng = np.random.default_rng(seed)
    n = len(D)
    nb = int(np.ceil(HORIZON / BLOCK))
    starts = rng.integers(0, n - BLOCK, size=(N_PATHS, nb))
    idx = (starts[:, :, None] + np.arange(BLOCK)[None, None, :]).reshape(N_PATHS, -1)[:, :HORIZON]
    paths = D[idx]                      # (Pfade, Horizont, Beine)
    return np.cumsum(paths, axis=1).transpose(2, 0, 1)


def evaluate(W: np.ndarray, C: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """W (B, Beine) -> (Median-Ertrag, P(Bruch), Median-MaxDD) je Kandidat."""
    eq = 1.0 + np.tensordot(W, C, axes=(1, 0))          # (B, Pfade, Horizont)
    peak = np.maximum.accumulate(np.concatenate([np.ones(eq.shape[:2] + (1,)), eq], axis=2), axis=2)[:, :, 1:]
    dd = (eq / peak - 1).min(axis=2)
    return np.median(eq[:, :, -1] - 1, axis=1), (dd <= -DD_LIMIT).mean(axis=1), np.median(dd, axis=1)


def candidates(step: float) -> np.ndarray:
    caps = np.array([min(1.0, MAX_RISK / UNIT_RISK[l]) for l in LEGS])
    grid = [np.round(np.arange(0, c + 1e-9, step), 4) for c in caps]
    out = [w for w in itertools.product(*grid) if 0 < sum(w) <= 1.0 + 1e-9]
    return np.array(out)


def _best_of(W: np.ndarray, C: np.ndarray, best: dict | None) -> dict | None:
    for i in range(0, len(W), 16):
        Wb = W[i:i + 16]
        med, pbr, mdd = evaluate(Wb, C)
        ok = pbr <= P_BREACH_MAX
        if ok.any():
            j = np.argmax(np.where(ok, med, -np.inf))
            if best is None or med[j] > best["median_return"] + 1e-12:
                best = {"w": Wb[j].copy(), "median_return": float(med[j]), "p_breach": float(pbr[j]),
                        "median_maxdd": float(mdd[j])}
    return best


def optimise(D: np.ndarray, seed: int = 7) -> dict:
    """Grobraster 0,1, danach koordinatenweise Verfeinerung in 0,025-Schritten
    (je Bein +-0,025, auch paarweise Umschichtung), bis nichts mehr besser wird."""
    C = bootstrap_cum(D, seed)
    best = _best_of(candidates(0.1), C, None)
    if best is None:
        raise RuntimeError("kein Kandidat erfuellt P(Bruch) <= 1 %")
    caps = np.array([min(1.0, MAX_RISK / UNIT_RISK[l]) for l in LEGS])
    step = 0.025
    for _ in range(40):
        base = best["w"]
        moves = []
        for i in range(len(LEGS)):
            for dlt in (-step, step):
                w = base.copy(); w[i] += dlt; moves.append(w)
            for j in range(len(LEGS)):
                if i != j:
                    w = base.copy(); w[i] += step; w[j] -= step; moves.append(w)
        W = np.array([w for w in moves if (w >= -1e-9).all() and (w <= caps + 1e-9).all() and 0 < w.sum() <= 1 + 1e-9])
        W = np.clip(W, 0, None)
        new = _best_of(W, C, dict(best))
        if new["median_return"] <= best["median_return"] + 1e-9:
            break
        best = new
    return best


def realised(w: np.ndarray, D: np.ndarray) -> dict:
    eq = 1.0 + np.cumsum(D @ w)
    peak = np.maximum.accumulate(np.concatenate([[1.0], eq]))[1:]
    dd = eq / peak - 1
    return {"return_pct": float((eq[-1] - 1) * 100) if len(eq) else 0.0,
            "maxdd_pct": float(dd.min() * 100) if len(dd) else 0.0, "breach": bool((dd <= -DD_LIMIT).any())}


def fmt_w(w) -> str:
    return "  ".join(f"{l.replace('orb_', '')}={x:.3f}" for l, x in zip(LEGS, w))


def main() -> None:
    trades = build_trades(refresh="--refresh" in sys.argv)
    print(trades.groupby("leg")["r"].agg(["count", "mean", "sum"]).round(3).to_string())
    Dm = daily_matrix(trades)
    cur = np.array([CURRENT[l] for l in LEGS])
    ohne = cur * np.array([1, 1, 1, 0, 0, 1])
    result: dict = {"legs": LEGS, "unit_risk": UNIT_RISK, "aktuell": CURRENT, "walk_forward": {}}

    # ---------------- Walk-Forward
    print("\n=== Anker-Walk-Forward (IS 2019..Y-1 -> OOS Y) ===")
    rows = []
    for y in OOS_YEARS:
        IS = Dm[Dm.index < f"{y}-01-01"].to_numpy()
        OOS = Dm[(Dm.index >= f"{y}-01-01") & (Dm.index <= f"{y}-12-31")].to_numpy()
        b = optimise(IS, seed=y)
        r = {"opt": realised(b["w"], OOS), "aktuell": realised(cur, OOS), "ohne_sp500_us30": realised(ohne, OOS)}
        rows.append((y, b, r))
        result["walk_forward"][y] = {"gewichte": dict(zip(LEGS, b["w"].round(4).tolist())),
                                     "is_mc": {k: v for k, v in b.items() if k != "w"}, "oos": r}
        print(f"{y}: {fmt_w(b['w'])}  | IS-MC Median {b['median_return']*100:+.1f} % P(Bruch) {b['p_breach']:.1%}")
        for k, v in r.items():
            print(f"      OOS {k:16} {v['return_pct']:+6.2f} %  MaxDD {v['maxdd_pct']:6.2f} %  Bruch {v['breach']}")
    oos = {k: [r[k] for _, _, r in rows] for k in ("opt", "aktuell", "ohne_sp500_us30")}
    summary = {k: {"summe_return_pct": sum(x["return_pct"] for x in v), "schlechtestes_maxdd_pct": min(x["maxdd_pct"] for x in v),
                   "jahre_mit_bruch": sum(x["breach"] for x in v)} for k, v in oos.items()}
    result["walk_forward_summary"] = summary
    print("\nOOS-Summe 2021-2026:")
    for k, v in summary.items():
        print(f"  {k:16} Σ Rendite {v['summe_return_pct']:+6.2f} %  schlechtestes MaxDD {v['schlechtestes_maxdd_pct']:6.2f} %  "
              f"Jahre mit Bruch {v['jahre_mit_bruch']}")

    # ---------------- Endgueltige Gewichtung auf voller Historie
    full = optimise(Dm.to_numpy(), seed=2026)
    C = bootstrap_cum(Dm.to_numpy(), 99)    # unabhaengige Pfade zur Kontrolle
    vergleich = {}
    for name, w in (("neu", full["w"]), ("aktuell", cur), ("ohne_sp500_us30", ohne)):
        med, pbr, mdd = evaluate(w[None, :], C)
        vergleich[name] = {"median_return_pct": float(med[0] * 100), "p_breach": float(pbr[0]),
                           "median_maxdd_pct": float(mdd[0] * 100),
                           "risiko_je_trade_pct": {l: float(x * UNIT_RISK[l] * 100) for l, x in zip(LEGS, w)}}
    result["voll"] = {"gewichte": dict(zip(LEGS, full["w"].round(4).tolist())), "mc_kontrolle": vergleich}
    print(f"\n=== Volle Historie 2019-2026: {fmt_w(full['w'])}")
    for k, v in vergleich.items():
        print(f"  {k:16} MC-Median {v['median_return_pct']:+6.2f} %/Jahr  P(Bruch) {v['p_breach']:.1%}  "
              f"Median-MaxDD {v['median_maxdd_pct']:.2f} %  Risiko/Trade "
              + " ".join(f"{l.replace('orb_','')} {x:.3f}%" for l, x in v["risiko_je_trade_pct"].items()))

    # ---------------- Gegenprobe mit der echten Ereignis-Simulation (Lot-Rundung etc.)
    bridge_cw = {l: (3 * x if l.startswith("orb") else x) for l, x in zip(LEGS, full["w"])}
    result["capital_weight_bridge"] = {k: round(v, 4) for k, v in bridge_cw.items()}
    ev = {}
    orig = dict(pb.CAPITAL_WEIGHT)
    for name, cw in (("neu", bridge_cw), ("aktuell", {l: orig[l] for l in LEGS})):
        pb.CAPITAL_WEIGHT.update(cw)
        for label, sub in (("2019-2026", trades), ("2026", trades[trades["entry_time"] >= "2026-01-01"])):
            pb.TRAILING_DD_PCT = 9.99   # Pfad nicht abbrechen, Bruch separat zaehlen
            r = fk.run_portfolio(sub.reset_index(drop=True))
            eod = r.pop("eod"); r.pop("taken")
            dd = eod / eod.cummax() - 1
            ev[f"{name}_{label}"] = {"return_pct": r["return_pct"], "maxdd_pct": r["max_dd_eod_pct"],
                                     "erster_bruch": str(dd[dd <= -DD_LIMIT].index.min()),
                                     "min_lot_bumps": r["min_lot_bumps"]}
    pb.CAPITAL_WEIGHT.update(orig)
    result["ereignis_sim"] = ev
    print("\n=== Ereignis-Simulation (Lot-Rundung, Mindestlot, Compounding) ===")
    for k, v in ev.items():
        print(f"  {k:22} Rendite {v['return_pct']:+7.2f} %  MaxDD {v['maxdd_pct']:6.2f} %  erster 5%-Bruch {v['erster_bruch']}")
    print(f"\nCAPITAL_WEIGHT fuer die Bridge: {result['capital_weight_bridge']}")

    OUT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"Geschrieben: {OUT}")


if __name__ == "__main__":
    main()
