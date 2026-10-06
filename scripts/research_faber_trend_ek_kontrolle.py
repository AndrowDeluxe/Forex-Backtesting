import sys, os, json
sys.path.insert(0, r"C:\Users\andre\Forex-Backtesting\scripts")
sys.argv = ["x"]
import importlib.util
src = open(r"C:\Users\andre\Forex-Backtesting\scripts\research_faber_trend_ek_hochrisiko.py", encoding="utf-8").read()
src = src.split('res = {"konto_usd"')[0]  # nur Setup ausfuehren
exec(compile(src, "setup", "exec"))
out = {}
for mode in ("sma10", "always"):
    sl = R.sleeves_for(prep, fin["insts"], mode, (), None)
    for risk in (0.05, 0.075, 0.10):
        for lab, (s0, s1) in {"is": (R.IS_START, R.IS_END), "oos": (R.OOS_START, R.END)}.items():
            r = E.run(prep, sl, grid["A1_pct20"], E.Sizing(risk), costs["zinsangep"], ek, start=s0, end=s1)
            m = E.metrics(r["equity"]); x = r["exposure"].dropna()
            m["hebel_median"] = round(float(x.median()), 2)
            out[f"{mode}|r{risk*100:g}|{lab}"] = m
            print(mode, risk, lab, {k: float(v) for k, v in m.items()}, flush=True)
json.dump(out, open(r"C:\Users\andre\Forex-Backtesting\Claude outputs\faber_trend_ek_kontrolle_immer_long.json", "w"), indent=1, default=float)
