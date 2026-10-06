"""Explorativ (Nutzerfrage 06.10.): EK, einfache Variante (SMA10, SL 20 %, 8 Instr.
ohne Oel als Primaer), Cash-Monate rotieren in OIL, wenn OIL > SMA10.
Vergleich: Cash only (ohne Oel). Oel-Reihe = CL=F (Roll-/2020-Artefakte) ->
zusaetzlich Kennzahlen ohne das Jahr 2020."""
import sys, os, json
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "research_faber_trend_ek_hochrisiko.py"), encoding="utf-8").read()
exec(compile(src.split('res = {"konto_usd"')[0], "setup", "exec"))

insts = [k for k in fin["insts"] if k != "OIL"]


def ohne_jahr(eqs, year):
    e = eqs[eqs.index.dayofweek < 5]
    r = e.pct_change().dropna()
    r = r[r.index.year != year]
    eq = (1 + r).cumprod()
    yrs = len(r) / 252
    return {"cagr_pct": round((eq.iloc[-1] ** (1 / yrs) - 1) * 100, 2),
            "maxdd_pct": round(float((eq / eq.cummax() - 1).min() * 100), 2)}


out = {}
for lab_v, alts in (("cash", None), ("oel_rotation", ["OIL"]), ("gold_rotation", ["GOLD"])):
    sl = R.sleeves_for(prep, insts, "sma10", (), alts)
    for risk in (0.05, 0.075, 0.10):
        for lab, (s0, s1) in {"is": (R.IS_START, R.IS_END), "oos": (R.OOS_START, R.END)}.items():
            r = E.run(prep, sl, grid["A1_pct20"], E.Sizing(risk), costs["zinsangep"], ek, start=s0, end=s1)
            m = E.metrics(r["equity"]); t = r["trades"]; x = r["exposure"].dropna()
            m["hebel_max"] = round(float(x.max()), 2)
            m["oel_trades"] = int(((t.inst == "OIL") & (t.reason != "rebalance")).sum()) if len(t) else 0
            m["oel_pnl_anteil_pct"] = round(float(t.loc[t.inst == "OIL", "pnl"].sum() / max(t.pnl.sum(), 1e-9) * 100), 1) if len(t) else 0
            m["p_dd20_pa"] = mc(r["equity"], 0.2); m["p_dd45_pa"] = mc(r["equity"], 0.45)
            if lab == "oos":
                m["ohne_2020"] = ohne_jahr(r["equity"], 2020)
            key = f"{lab_v}|r{risk*100:g}|{lab}"
            out[key] = m
            print(key, json.dumps(m, default=float), flush=True)
json.dump(out, open(os.path.join(R.ROOT, "Claude outputs", "faber_trend_ek_oelrotation.json"), "w"), indent=1, default=float)
