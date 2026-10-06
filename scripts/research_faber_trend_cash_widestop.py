"""Explorativ (Nutzerfrage 05.10., NICHT vorab ausgewaehlt): Hauptfinalist
kombi_r0.5 ohne Gold-Switch (Cash only) und mit den weitesten getesteten
Stopps, echte MT5-Kosten. Vergleich gegen den Finalisten wie gewaehlt."""
import glob, json, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import research_faber_trend_funded as R
import research_faber_trend_realkosten as K
from faber_trend import data as D, engine as E

specs = json.load(open(sorted(glob.glob(os.path.join(D.FROZEN_DIR, "faber_symbol_specs_*.json")))[-1], encoding="utf-8"))
isr = json.load(open(R.OUT_IS, encoding="utf-8"))
prep = R.load_all(with_btc=True)
cal = pd.DatetimeIndex(sorted(set().union(*[v["df"].index for v in prep.values()])))
irx = K.irx_series()
grid = R.stop_grid(isr["mae_params"])
sp = isr["stufe3_kandidaten"]["kombi_r0.5"]["spec"]
eurusd = specs["konten"]["TTP"]["symbole"]["EURUSD"]["bid"]
accs = {"TTP": E.Account("TTP", specs["konten"]["TTP"]["equity"], True),
        "EK": E.Account("EK", specs["konten"]["EK"]["equity"] * eurusd, True)}
costs = {}
for a, acc in accs.items():
    spread_by, swap_by, lot, shift = K.build(specs["konten"][a], prep, irx, cal)
    acc.specs = lot
    costs[a] = E.Costs(spread_by=spread_by, swap_by=swap_by, shift=shift, shift_insts=K.SHIFT_INSTS)

# mittlere Stoppweite je Variante in % vom Kurs (ueber die Instrumente des Finalisten, IS-Ende)
def width(name):
    r = grid[name]; w = []
    for k in sp["insts"]:
        d = prep[k]["df"].loc[:R.IS_END].iloc[-1]
        if r.kind in ("pct", "mae_pct"): w.append(r.p(k))
        elif r.kind in ("atr", "trail", "mae_atr"): w.append(r.p(k) * d.atr / d.close)
        else: w.append(r.sizing_pct_if_none)
    return float(np.median(w))

widths = {n: round(width(n) * 100, 1) for n in grid}
cands = ["A5_mae_atr_q90", "A5_mae_pct_q95", "A5_mae_atr_q95", "A1_pct20", "A0_none"]
sz = E.Sizing(sp["risk"], vol_filter_half=sp["vol_filter_half"])
res = {"stoppweite_median_pct": widths, "laeufe": {}}
for alts_lab, alts in (("gold", ["GOLD"]), ("cash", None)):
    sl = R.sleeves_for(prep, sp["insts"], sp["mode"], (), alts)
    for st in cands:
        for a, acc in accs.items():
            for lab, (s0, s1) in {"is": (R.IS_START, R.IS_END), "oos": (R.OOS_START, R.END)}.items():
                m, _ = R.evaluate(prep, sl, grid[st], sz, costs=costs[a], account=acc, start=s0, end=s1,
                                  mc=(a == "TTP" and lab == "oos"))
                res["laeufe"][f"{alts_lab}|{st}|{a}|{lab}"] = m
                print(alts_lab, st, a, lab, {k: m.get(k) for k in ("cagr_pct","maxdd_pct","ratio","worst_day_pct","trades","skipped","p_trailing7_pa")}, flush=True)
json.dump(res, open(os.path.join(R.ROOT, "Claude outputs", "faber_trend_cash_widestop.json"), "w", encoding="utf-8"), indent=1, default=float)
print(json.dumps(widths))
