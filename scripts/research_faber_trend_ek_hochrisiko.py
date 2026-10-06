"""Explorativ (Nutzerfrage 06.10.): gesamtes Faber-Trend-Edge auf dem EK-Konto
(Tickmill, echte MT5-Kosten/Kontrakte, 2.817 EUR) mit 5 / 7,5 / 10 % Risiko je
Position. Zusaetzlich: Bruttohebel (Nominal/Equity) gegen ESMA-Retail-Grenzen,
Wahrscheinlichkeit, dass der EK-Kill-Switch (-45 % trailing) ausloest.
Nicht vorab ausgewaehlt -> Erkundung, kein sauberer Test."""
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
eurusd = specs["konten"]["TTP"]["symbole"]["EURUSD"]["bid"]
ek = E.Account("EK", specs["konten"]["EK"]["equity"] * eurusd, True)
sp_by, sw_by, lot, shift = K.build(specs["konten"]["EK"], prep, irx, cal)
ek.specs = lot
costs = {"zinsangep": E.Costs(spread_by=sp_by, swap_by=sw_by, shift=shift, shift_insts=K.SHIFT_INSTS),
         "heute": E.Costs(spread_by=sp_by, swap_by=sw_by)}
fin = isr["stufe3_kandidaten"]["kombi_r0.5"]["spec"]
VAR = {
    "finalist_ens_vol_gold_A5q90": (fin["insts"], "ens", ["GOLD"], "A5_mae_atr_q90", True),
    "cash_ens_vol_A5q90": (fin["insts"], "ens", None, "A5_mae_atr_q90", True),
    "cash_sma10_sl20": (fin["insts"], "sma10", None, "A1_pct20", False),
    "nur_indizes_cash_sma10_sl20": (["SP500", "NASDAQ", "US30", "DAX"], "sma10", None, "A1_pct20", False),
}


def mc(eqs, thr, days=252, paths=2000, block=20, seed=7):
    dr = eqs[eqs.index.dayofweek < 5].pct_change().dropna().values
    rng = np.random.default_rng(seed); n = len(dr); hit = 0
    for _ in range(paths):
        idx = np.concatenate([np.arange(s, s + block) % n for s in rng.integers(0, n, days // block + 1)])[:days]
        eq = np.cumprod(1 + dr[idx]); peak = np.maximum.accumulate(np.concatenate([[1.0], eq]))[1:]
        hit += (eq <= peak * (1 - thr)).any()
    return round(hit / paths, 4)


res = {"konto_usd": ek.equity0, "laeufe": {}}
for vname, (insts, mode, alts, st, volf) in VAR.items():
    sl = R.sleeves_for(prep, insts, mode, (), alts)
    for risk in (0.05, 0.075, 0.10):
        for model, c in costs.items():
            for lab, (s0, s1) in {"is": (R.IS_START, R.IS_END), "oos": (R.OOS_START, R.END)}.items():
                r = E.run(prep, sl, grid[st], E.Sizing(risk, vol_filter_half=volf), c, ek, start=s0, end=s1)
                m = E.metrics(r["equity"]); t = r["trades"]
                x = r["exposure"].dropna()
                m.update({"trades": int((t.reason != "rebalance").sum()) if len(t) else 0, "skipped": r["skipped"],
                          "endwert_usd": round(float(r["equity"].iloc[-1]), 0),
                          "hebel_median": round(float(x.median()), 2), "hebel_max": round(float(x.max()), 2),
                          "tage_hebel_ueber_10": round(float((x > 10).mean() * 100), 1),
                          "tage_hebel_ueber_20": round(float((x > 20).mean() * 100), 1)})
                if model == "zinsangep":
                    m.update({f"p_dd{int(th*100)}_pa": mc(r["equity"], th) for th in (0.2, 0.3, 0.45)})
                    e = r["equity"][r["equity"].index.dayofweek < 5]
                    y = e.groupby(e.index.year).last()
                    m["jahre_pct"] = {int(k): round(float(v) * 100, 1) for k, v in y.pct_change().fillna(y.iloc[0] / e.iloc[0] - 1).items()}
                key = f"{vname}|r{risk*100:g}|{model}|{lab}"
                res["laeufe"][key] = m
                print(key, {k: v for k, v in m.items() if k != "jahre_pct"}, flush=True)
json.dump(res, open(os.path.join(R.ROOT, "Claude outputs", "faber_trend_ek_hochrisiko.json"), "w", encoding="utf-8"),
          indent=1, default=float)
