import sys; sys.path.insert(0, r"C:\Users\andre\Forex-Backtesting")
import logging; logging.disable(logging.CRITICAL)
import numpy as np, pandas as pd
from asian_range_breakout import pending as P
from asian_range_breakout.engine import simulate_asian_breakout
from asian_range_breakout.filters import (apply_adx_filter, apply_entry_delay_filter, apply_silver_alignment_filter,
    apply_trend_bias_filter, attach_series_level, rolling_liquidity_threshold)
from asian_range_breakout.sizing import simulate_equity
from bond_yield_indicator.friction import fetch_fx_friction, corwin_schultz_spread, _K
from combined_strategy.data import fetch_timeframe
from asian_range_breakout.data import fetch_gold_m15
END="2026-11-01"
gold=fetch_gold_m15(P.HISTORY_START,END); silver=fetch_timeframe("SILVER","M15",P.HISTORY_START,END)
d1=fetch_timeframe("GOLD","D1",P.HISTORY_START,END); fr=fetch_fx_friction("GOLD",P.HISTORY_START,END)
dc=gold["close"].tz_localize(None).resample("D").last().dropna(); ds=silver["Close"].tz_localize(None).resample("D").last().dropna()
print("D1-Index Beispiel:",d1.index[:2].tolist())
raw=simulate_asian_breakout(gold,range_start=P.RANGE_START,range_end=P.RANGE_END,exit_time=P.EXIT_TIME,stop_frac=P.STOP_FRAC)
raw=apply_entry_delay_filter(apply_adx_filter(raw,adx_min=P.ADX_MIN),max_delay_bars=P.MAX_DELAY_BARS)
# Live-Wissensstand: Friktion[t] mit Handelstag t+1 nur bis Range-Ende (01:00 NY)
m=gold.tz_convert("UTC"); H,L=d1["High"].copy(),d1["Low"].copy()
idx=d1.index
hp,lp=[],[]
for ts in idx:
    bar=ts.tz_convert("UTC") if ts.tzinfo else ts.tz_localize("UTC")
    ny=bar.tz_convert(P.NY).normalize()
    # Handelstag = UTC-Datum des D1-Balkens; Range-Ende 01:00 NY dieses Datums
    re=pd.Timestamp(bar.date()).tz_localize(P.NY)+pd.Timedelta(hours=1)
    w=m[(m.index>=bar)&(m.index<re.tz_convert("UTC"))]
    hp.append(w["high"].max() if len(w) else np.nan); lp.append(w["low"].min() if len(w) else np.nan)
hp=pd.Series(hp,index=idx); lp=pd.Series(lp,index=idx)
h2n,l2n=hp.shift(-1),lp.shift(-1)
ok=h2n.notna()
h2=pd.concat([H,h2n],axis=1).max(axis=1); l2=pd.concat([L,l2n],axis=1).min(axis=1)
gamma=np.log(h2/l2)**2; beta=(np.log(H/L)+np.log(h2n/l2n))**2
alpha=(np.sqrt(2*beta)-np.sqrt(beta))/_K-np.sqrt(gamma/_K)
fl=(2*(np.exp(alpha)-1)/(1+np.exp(alpha))).where(ok)
if fl.index.tz is not None: fl.index=fl.index.tz_localize(None)
print("Friktion Korrelation Backtest/Live:",round(fr.corr(fl),3),"gueltig:",fl.notna().sum())
thr0=rolling_liquidity_threshold(fr,quantile=P.LIQUIDITY_QUANTILE,min_periods=P.LIQUIDITY_MIN_PERIODS)
def run(k=0,frs=None,thr=None):
    t=apply_trend_bias_filter(raw,dc.shift(k).dropna(),sma_window=P.TREND_SMA_WINDOW)
    t=apply_silver_alignment_filter(t,ds.shift(k).dropna(),window=P.SILVER_ALIGNMENT_WINDOW)
    t=attach_series_level(t,frs,"friction_prior"); t=attach_series_level(t,thr,"thr").dropna(subset=["thr","friction_prior"])
    t=t[t["friction_prior"]<=t["thr"]]
    t=simulate_equity(t,starting_equity=100_000.0,risk_pct=0.005).copy()
    t["day"]=t["entry_time"].dt.tz_localize(None).dt.normalize(); return t.set_index("day")
def st(x):
    r=x["r_multiple"]; n=len(r)
    if n<2: return f"n={n}"
    return f"n={n:4d} OeR {r.mean():+.3f} t {r.mean()/r.std()*n**.5:+.2f} SumR {r.sum():+7.1f}"
A=run(0,fr,thr0)        # wie Produktions-Backtest (Vorgriff)
B=run(0,fl,thr0)        # Live-Wissensstand 01:00 NY
# Vergleich Pruefung gegen scan_trades-Kette: n sollte zu Produktion passen
print("A Backtest bisher  ",st(A)); print("B Live-Wissensstand",st(B))
print("  nur A:",st(A.loc[A.index.difference(B.index)])); print("  nur B:",st(B.loc[B.index.difference(A.index)]))
V={"A":A,"B":B}
rng=np.random.default_rng(1)
for k in (1,2,3):
    # Datenstand D-1-k: Friktion braucht t+1 -> zuletzt gueltig eine Position aelter
    t=run(k,fr.shift(k+1),thr0.shift(k)); V[f"k{k}"]=t
    both=B.index.intersection(t.index); new=t.index.difference(B.index); lost=B.index.difference(t.index)
    b=[t["r_multiple"].to_numpy()[rng.integers(0,len(t),len(t))].mean() for _ in range(4000)]
    print(f"\nk={k} Ersatz",st(t),f"| 95% {np.percentile(b,2.5):+.3f}..{np.percentile(b,97.5):+.3f}")
    print("  gleiche Tage wie B",st(t.loc[both]),f"({len(both)/len(B):.0%} von B)"); print("  nur Ersatz  ",st(t.loc[new])); print("  nur B       ",st(B.loc[lost]))
print()
for lab,a,z in (("2016-19","2016","2020"),("2020-22","2020","2023"),("2023-24","2023","2025"),("2025-26","2025","2027"),("letzte12M","2025-11-01","2027")):
    print(f"{lab:10s}",*[f"{n}: {st(v[(v.index>=a)&(v.index<z)])}\n          " for n,v in V.items()])
print("Doppelausfall nur Ausfalltage egal -- 30.10.:")
for n,v in V.items(): print(n, "2026-10-30" in v.index.strftime("%Y-%m-%d"), v[v.index=="2026-10-30"][["direction","r_multiple","friction_prior","thr"]].to_dict("records"))
print("Friktion live 29.10:",fl.get(pd.Timestamp("2026-10-29")),"Backtest:",fr.get(pd.Timestamp("2026-10-29")),"Schwelle:",thr0.get(pd.Timestamp("2026-10-29")))
