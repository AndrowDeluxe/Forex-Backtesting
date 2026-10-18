"""NASDAQ K2 + Oel-Korr. 60 T. < 0: SL / TP / Haltedauer (Nutzerauftrag 2026-10-15).

Basis: Forward-Regel aus forward_noise_area_k60.py (unveraendert, laeuft weiter). Hier nur, ob
ein harter SL, ein TP oder eine kuerzere Haltedauer den Edge verbessern.

M1-Simulation: Einstieg zum Open der Entscheidungs-Bar (wie Engine), danach Bar fuer Bar:
SL/TP intrabar ueber High/Low; trifft eine Bar beide, zaehlt der SL (konservativ). Zeit-Exit
zum Close der Bar nach `hold` Minuten, spaetestens 16:00. Abstaende in Einheiten der
Tagesvola sigma (Std. der Tagesrenditen 14 T. bis Vortag) -- dieselbe Groesse wie im
1-%-Risiko-Sizing. Kosten 1,29 bps je Rundturn.

LOCK noise_area_k60_sltp_20261015 (Split wie Paper: IS 2016-07..2022 | OOS ..09/2025 | Tresor ..09/2026)
  Raster 9 Punkte (3 Dimensionen x 3 Werte = 27 Kombinationen, Richtwert eingehalten):
    sl   keiner / 0,5 / 1,0 sigma
    tp   keins / 1,0 / 2,0 sigma
    hold 16:00 / 240 / 120 Minuten
  Auswahl NUR auf IS: hoechstes Netto-Sharpe (1x, Tagesrenditen). OOS + Tresor je einmal
  (VORBELASTET: die Basisregel wurde nach Sicht auf alle Perioden gewaehlt).
  Vorab: Schlaegt der Gewinner die Basis (16:00, kein SL/TP) netto je Trade in OOS UND Tresor,
  wird er als zusaetzliche Forward-Variante registriert (ab 2026-10-16, Stichtag 2027-03-31).
Beschreibend (alle Perioden): Rendite-Verlauf nach Haltedauer, MAE/MFE in sigma.

  python scripts/research_noise_area_k60_sltp.py profil
  python scripts/research_noise_area_k60_sltp.py raster
"""
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).resolve().parent))

from noise_area_momentum.engine import DECISIONS, N_BARS, positions_general  # noqa: E402
from research_lock import Lock  # noqa: E402
from research_noise_area_momentum import COST_RT, IS_END, IS_START, OOS_END, TRESOR_END, grid  # noqa: E402
from research_noise_area_oel import oil_grid  # noqa: E402
from research_noise_area_oel_fit2026 import bases, features, masks  # noqa: E402

STRATEGY = "noise_area_k60_sltp_20261015"
INST = "NASDAQ"
FORWARD_START, EVAL_DATE = "2026-10-16", "2027-03-31"
OUT = ROOT / "noise_area_momentum" / "results"
SL, TP, HOLD = [None, 0.5, 1.0], [None, 1.0, 2.0], [None, 240, 120]
PERIODS = [("IS", IS_START, IS_END), ("OOS", "2023-01-01", OOS_END), ("Tresor", "2025-10-01", TRESOR_END)]


def entries() -> pd.DataFrame:
    """Einstiege der Forward-Regel: Tag, Bar-Index, Richtung, Einstiegskurs, sigma."""
    g = grid(INST)
    lo, so = masks(features(g, oil_grid("index")), k=(60, 0.0))
    pos, valid = positions_general(g, long_ok=lo, short_ok=so, **bases(INST)["k2"])
    close_d = pd.Series(g["close"][:, -1], index=g["dates"])
    sig = close_d.pct_change().rolling(14, min_periods=14).std(ddof=1).shift(1).to_numpy()
    rows = []
    for d in np.where(valid & (pos != 0).any(axis=1))[0]:
        j = int(np.argmax(pos[d] != 0))
        e = int(DECISIONS[j])
        rows.append({"date": g["dates"][d], "d": d, "bar": e, "side": int(pos[d, j]),
                     "entry": g["open"][d, e], "sigma": sig[d]})
    return pd.DataFrame(rows).set_index("date"), g


def simulate(t: pd.DataFrame, g: dict, sl, tp, hold) -> pd.DataFrame:
    out = []
    cost = COST_RT[INST] * 1e-4
    for date, r in t.iterrows():
        d, e, s, px, sg = int(r.d), int(r.bar), r.side, r.entry, r.sigma
        end = N_BARS - 1 if hold is None else min(e + hold - 1, N_BARS - 1)
        hi, lo, cl = g["high"][d, e:end + 1], g["low"][d, e:end + 1], g["close"][d, end]
        slp = None if sl is None else px * (1 - s * sl * sg)
        tpp = None if tp is None else px * (1 + s * tp * sg)
        exit_px, why = cl, "zeit"
        for k in range(len(hi)):
            adv = lo[k] if s > 0 else hi[k]
            fav = hi[k] if s > 0 else lo[k]
            if slp is not None and (adv <= slp if s > 0 else adv >= slp):
                exit_px, why = slp, "sl"
                break
            if tpp is not None and (fav >= tpp if s > 0 else fav <= tpp):
                exit_px, why = tpp, "tp"
                break
        ret = s * (exit_px / px - 1) - cost
        out.append({"date": date, "ret": ret, "exit": why, "sigma": sg,
                    "r_mult": ret / (sl * sg) if sl else np.nan})
    return pd.DataFrame(out).set_index("date")


def daily_series(tr: pd.DataFrame, g: dict, a: str, b: str) -> pd.Series:
    days = g["dates"][(g["dates"] >= a) & (g["dates"] <= b)]
    return tr["ret"].reindex(days).fillna(0.0)


def summary(tr: pd.DataFrame, g: dict, a: str, b: str) -> dict:
    x = tr[(tr.index >= a) & (tr.index <= b)]
    r = daily_series(tr, g, a, b)
    w, l = x.ret[x.ret > 0], x.ret[x.ret < 0]
    return {"trades": len(x), "netto_bps": x.ret.mean() * 1e4, "sharpe": r.mean() / r.std(ddof=1) * np.sqrt(252),
            "pf": w.sum() / -l.sum() if len(l) else np.inf, "treffer_%": (x.ret > 0).mean() * 100,
            "sl_%": (x.exit == "sl").mean() * 100, "tp_%": (x.exit == "tp").mean() * 100}


def account_1pct(tr: pd.DataFrame, g: dict, a: str, b: str, sl) -> dict:
    """100k, 1 % Risiko: mit SL -> Positionsgroesse = 1 % / SL-Abstand; ohne SL -> 1 sigma = 1 %. Hebel <= 4."""
    x = tr[(tr.index >= a) & (tr.index <= b)]
    dist = (sl if sl else 1.0) * x["sigma"]
    lev = np.minimum(4.0, 0.01 / dist)
    eq = 100_000 * (1 + lev * x["ret"]).cumprod()
    pnl = eq.diff().fillna(eq.iloc[0] - 100_000)
    return {"endstand": eq.iloc[-1], "maxdd_%": (eq / eq.cummax() - 1).min() * 100,
            "oe_verlierer_%": (lev * x.ret)[x.ret < 0].mean() * 100, "schlimmster_%": (lev * x.ret).min() * 100,
            "oe_trade_eur": pnl.mean()}


def stage_profil() -> None:
    t, g = entries()
    t["periode"] = np.where(t.index <= IS_END, "IS", np.where(t.index <= OUT_END_OOS, "OOS", "Tresor"))
    marks = [15, 30, 60, 120, 180, 240, 300, 360]
    rows, mm = [], []
    for date, r in t.iterrows():
        d, e, s, px = int(r.d), int(r.bar), r.side, r.entry
        path = s * (g["close"][d, e:] / px - 1) / r.sigma
        row = {"periode": r.periode}
        for m in marks:
            row[f"{m}m"] = path[min(m, len(path)) - 1] * r.sigma * 1e4 if m <= len(path) else np.nan
        row["16:00"] = path[-1] * r.sigma * 1e4
        rows.append(row)
        hi = s * ((g["high"][d, e:] if s > 0 else g["low"][d, e:]) / px - 1) / r.sigma
        lo = s * ((g["low"][d, e:] if s > 0 else g["high"][d, e:]) / px - 1) / r.sigma
        mm.append({"periode": r.periode, "mae_sigma": lo.min(), "mfe_sigma": hi.max(), "end_sigma": path[-1],
                   "restzeit_min": len(path)})
    p = pd.DataFrame(rows)
    m = pd.DataFrame(mm)
    pd.set_option("display.width", 250)
    print("Oe Brutto-Rendite (bps) nach Minuten seit Einstieg (NaN = Trade vorher schon 16:00):")
    print(p.groupby("periode").mean().round(2).to_string())
    print("\nAnzahl Trades:", p.groupby("periode").size().to_dict())
    print("Oe Restzeit bis 16:00 (Min.):", m.groupby("periode")["restzeit_min"].mean().round(0).to_dict())
    print("\nMAE / MFE in Tagesvola-Einheiten (Median) und Anteile:")
    q = m.groupby("periode").agg(mae_median=("mae_sigma", "median"), mfe_median=("mfe_sigma", "median"),
                                 end_median=("end_sigma", "median"))
    for th in (0.5, 1.0):
        q[f"MAE<-{th}"] = m.groupby("periode").apply(lambda x: (x.mae_sigma < -th).mean())
        q[f"MAE<-{th} & Gewinner"] = m.groupby("periode").apply(lambda x: ((x.mae_sigma < -th) & (x.end_sigma > 0)).mean())
        q[f"MFE>{th} & Verlierer"] = m.groupby("periode").apply(lambda x: ((x.mfe_sigma > th) & (x.end_sigma < 0)).mean())
    print(q.round(3).to_string())
    m.to_csv(OUT / "k60_mae_mfe.csv", index=False)


OUT_END_OOS = OOS_END


def lock() -> Lock:
    lk = Lock(STRATEGY)
    lk.register_split(IS_START, IS_END, OOS_END, TRESOR_END)
    return lk


def stage_raster() -> None:
    lk = lock()
    if lk.trials == 0:
        lk.log_trials(27, note="SL x TP x Haltedauer (3x3x3) auf der K60-Forward-Regel")
    t, g = entries()
    sims = {(sl, tp, h): simulate(t, g, sl, tp, h) for sl, tp, h in itertools.product(SL, TP, HOLD)}
    rows = [{"sl": sl, "tp": tp, "hold": h or "16:00", **summary(tr, g, IS_START, IS_END)}
            for (sl, tp, h), tr in sims.items()]
    rep = pd.DataFrame(rows).sort_values("sharpe", ascending=False)
    rep.to_csv(OUT / "k60_sltp_is.csv", index=False)
    pd.set_option("display.width", 250)
    print("IS 2016-07..2022 (Auswahl nach Sharpe):\n", rep.round(2).to_string(index=False))
    best = rep.iloc[0]
    key = (None if pd.isna(best.sl) else best.sl, None if pd.isna(best.tp) else best.tp,
           None if best.hold == "16:00" else int(best.hold))
    h = lk.freeze({"gewinner": {"sl": key[0], "tp": key[1], "hold": key[2]}, "auswahl": "max IS-Sharpe",
                   "basis": "forward_noise_area_k60 (16:00, kein SL/TP)"})
    for st in ("oos", "tresor"):
        if st not in lk._load()["unsealed"]:
            lk.unseal(st, h)
    base = (None, None, None)
    out = []
    for name, k in (("Basis 16:00", base), (f"Gewinner {key}", key)):
        for per, a, b in PERIODS:
            out.append({"variante": name, "periode": per, **summary(sims[k], g, a, b),
                        **account_1pct(sims[k], g, a, b, k[0])})
    res = pd.DataFrame(out)
    res.to_csv(OUT / "k60_sltp_unseal.csv", index=False)
    print("\nGewinner gegen Basis, alle Perioden (100k, 1 % Risiko):\n", res.round(2).to_string(index=False))
    print("\nAlle 27 Varianten, netto bps je Trade je Periode (nach dem Einfrieren, beschreibend):")
    allp = pd.DataFrame([{"sl": sl, "tp": tp, "hold": h or "16:00",
                          **{per: summary(tr, g, a, b)["netto_bps"] for per, a, b in PERIODS}}
                         for (sl, tp, h), tr in sims.items()])
    allp.to_csv(OUT / "k60_sltp_alle_perioden.csv", index=False)
    print(allp.round(2).to_string(index=False))
    rb = res.set_index(["variante", "periode"])["netto_bps"]
    beats = all(rb[(f"Gewinner {key}", p)] > rb[("Basis 16:00", p)] for p in ("OOS", "Tresor"))
    if key != base and beats and lk._load().get("forward") is None:
        lk.register_forward(FORWARD_START, EVAL_DATE, 10**6)
        print("Kriterium erfuellt -> Forward registriert ab", FORWARD_START)
    else:
        print("Kriterium NICHT erfuellt (oder Gewinner = Basis) -> kein zusaetzlicher Forward")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    {"profil": stage_profil, "raster": stage_raster}[sys.argv[1]]()
