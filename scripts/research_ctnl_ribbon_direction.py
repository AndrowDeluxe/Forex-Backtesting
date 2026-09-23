"""CTNL: der eigene MTF-EMA-Ribbon als TRENDRICHTUNG (2026-09-23)

`gold_smc_htf_ltf/ema_ribbon.py` haelt den MTF-EMA-Ribbon aus dem eigenen
Pine-Script des Nutzers (H4-EMA50, D1-EMA50, D1-EMA200, W1-EMA50). Er war
bisher NUR als Dehnungs-Filter verdrahtet (`require_ribbon_stretch`: "Preis
zu weit vom Ribbon entfernt") -- nie als Trendrichtung.

Dieses Skript prueft beide Lesarten gegeneinander:
  (A) Dehnung   -- die verdrahtete Variante, ueber require_ribbon_stretch
  (B) RICHTUNG  -- Preis ueber ALLEN vier EMAs = Aufwaerts, unter allen =
                   Abwaerts. Als direktionales Gate: long nur im Aufwaerts-,
                   short nur im Abwaertstrend.

KEINE PARAMETERSUCHE. Die EMA-Laengen sind die Script-Defaults, die Lesart
ist die naheliegende. Das ist Absicht: nach Befund 9b (Signal-Sweep als
IS-Sieger in 8/8 Jahren, der OOS verliert) ist jede zusaetzliche
Freiheitsgrad-Suche hier ein Risiko, kein Gewinn.

Ergebnis siehe knowledge/projects/ctnl-kostenvalidierung.md Befund 15:
als Dehnungsfilter wertlos, als Trendrichtung der staerkste Hebel der
gesamten Untersuchung -- und die einzige Variante, unter der die SHORT-Seite
positiv wird (+0,174 Ø R gegen -0,161 mit einem generischen EMA-Stapel).
"""

import sys
sys.path.insert(0, r"C:\Users\andre\Forex-Backtesting")
sys.path.insert(0, r"C:\Users\andre\Forex-Backtesting\scripts")
sys.path.insert(0, r"C:\Users\andre\Forex-Backtesting\ou_paper_backtest")
import numpy as np, pandas as pd
from gold_smc_htf_ltf.data import fetch_gold_d1, fetch_gold_w1
from gold_smc_htf_ltf.ema_ribbon import compute_ribbon
from gold_smc_htf_ltf.live_signal import REV_KWARGS
from research_ctnl_execution_costs import _utc_naive, load_bars
from research_ctnl_optimization import anchored_walk_forward, leg_trades, surface, to_live
from monte_carlo import run_monte_carlo

START, END = "2016-01-01", pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")
bars = load_bars(START, END)
d1, w1 = fetch_gold_d1(START, END), fetch_gold_w1(START, END)
print(f"D1 {len(d1)} Bars, W1 {len(w1)} Bars")

# --- A) Ribbon als eingebauter Pipeline-Filter
reps = {}
reps["baseline"] = to_live(leg_trades(bars, "ctnl_reversal", tp_r=5.0, sig_kwargs=REV_KWARGS), bars["m15"])
for ext in (2.0, 3.0, 4.0):
    kw = {**REV_KWARGS, "require_ribbon_stretch": True, "d1_df": d1, "w1_df": w1,
          "ribbon_extension_atr_min": ext}
    try:
        reps[f"ribbon_{ext:g}atr"] = to_live(leg_trades(bars, "ctnl_reversal", tp_r=5.0, sig_kwargs=kw), bars["m15"])
        print(f"  ribbon {ext} ATR: {len(reps[f'ribbon_{ext:g}atr'])} Trades")
    except Exception as e:
        print(f"  ribbon {ext}: {type(e).__name__}: {str(e)[:80]}")

# --- B) Ribbon als DIREKTIONALES Gate (nie getestet)
# Signatur: compute_ribbon(h4_df, d1_df, w1_df) -> ema_h4/ema_d1_fast/
# ema_d1_slow/ema_w1 + ribbon_mean + ribbon_extension_atr
rib = compute_ribbon(bars["h4"], d1, w1)
emacols = ["ema_h4", "ema_d1_fast", "ema_d1_slow", "ema_w1"]
idx = _utc_naive(rib.index)
px = pd.Series(rib["close"].to_numpy(), index=idx)
stack = pd.DataFrame({c: pd.Series(rib[c].to_numpy(), index=idx) for c in emacols}).dropna()
# Richtung: Preis ueber ALLEN vier Ribbon-EMAs = Aufwaerts, unter allen = Abwaerts,
# dazwischen = 0. Das ist die Ribbon-Lesart als TREND, nicht als Dehnung.
above = px.reindex(stack.index) > stack.max(axis=1)
below = px.reindex(stack.index) < stack.min(axis=1)
richtung = pd.Series(np.where(above, 1, np.where(below, -1, 0)), index=stack.index)

base = reps["baseline"].copy()
base["rib"] = richtung.reindex(_utc_naive(base["entry_time"]), method="ffill").to_numpy()
reps["ribbon-konform"] = base[((base["direction"] == 1) & (base["rib"] > 0)) |
                              ((base["direction"] == -1) & (base["rib"] < 0))]
reps["ribbon long-only"] = base[(base["direction"] == 1) & (base["rib"] > 0)]

print(f"\n  short im Ribbon-Abwaertstrend: n={len(base[(base['direction']==-1)&(base['rib']<0)])}, "
      f"Ø R {base[(base['direction']==-1)&(base['rib']<0)]['r'].mean():+.3f}")

surface(reps, "ctnl_reversal: MTF-EMA-Ribbon")
anchored_walk_forward(reps, "baseline", "ctnl_reversal: MTF-EMA-Ribbon")
print("\n  Monte Carlo (0,15 %/Trade):")
print(f"    {'Variante':>18} {'MedDD':>9} {'P(>6%)':>8} {'Return':>9} {'Sharpe':>8}")
for name, d in reps.items():
    daily = (d.set_index(_utc_naive(d["entry_time"]))["r"] * 0.0015).resample("D").sum()
    daily = daily[daily.index.dayofweek < 5]
    if len(daily) < 250: continue
    mc = run_monte_carlo(daily, initial_equity=100_000.0, block_size=20, n_sims=2000, seed=42)
    s = mc["summary"] if isinstance(mc, dict) and "summary" in mc else mc
    dd = s["max_drawdown_pct"]
    print(f"    {name:>18} {np.median(dd):>8.2f}% {(np.abs(dd)>6).mean():>7.1%} "
          f"{np.median(s['total_return_pct']):>8.1f}% {np.median(s['sharpe']):>8.2f}")
