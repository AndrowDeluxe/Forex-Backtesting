"""VIX / Zinsen / DXY -> S&P 500 und Gold: Wirkkette und Gold-Bodensignal (Nutzerauftrag 22.11.2026).

Anlass: SMT-Gold-Report 22.11. (Signal 1 „Stresstag“) und Dennis im Call 22.11.: „Fallen VIX und Zinsen,
ist das gut für Gold und Indizes.“

Vorab festgelegt (vor dem ersten Lauf, 22.11.2026):
  Split IS 2005-2017, OOS 2018 - 21.05.2026, Tresor 22.05.-20.11.2026 (bleibt zu).
  Daten: S&P = ^GSPC, Gold = GLD (Schluss 16:00 ET wie S&P/VIX), VIX = ^VIX, DXY = DX-Y.NYB, 2J = FRED DGS2.
  Vorwärts-Renditen ab dem Schluss des FOLGEtages (Signal erst nach Schluss bekannt), Horizonte 5/20/60 Tage.
  Statistik: y = a + b*Signal, b = Abstand zum Rest, HAC (Newey-West, Lags = Horizont).

  T1 Gold-Boden „Stresstag“: GLD > 0 und S&P <= -1 % am selben Tag, GLD >= 10 % unter 252-Tage-Hoch.
     Varianten: ohne Drawdown-Bedingung; Drawdown >= 20 %. Vergleich: alle Tage mit gleichem Drawdown.
  T2 Gleichlauf (Wochen): Korrelation dVIX, d2J, dDXY mit S&P- und Gold-Rendite derselben Woche.
  T3 Vorlauf (Wochen): dVIX, d2J, dDXY in Woche t -> S&P/Gold in Woche t+1 und t+1..t+4.
  T4 VIX > 30: Tage mit VIX-Schluss > 30 und erster Schluss über 30 (Ereignis) -> S&P/Gold vorwärts.
  T5 Dennis-Faktor: VIX und 2J fallen beide über 5 Tage -> S&P/Gold vorwärts (und im selben Fenster).
     Variante: nur wenn VIX vor 5 Tagen > 30 war (Entspannung aus Stress).
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import yfinance as yf

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research_lock import Lock  # noqa: E402
from fusion_lab.g8.data import fetch_fred  # noqa: E402

lock = Lock("vix_zins_wirkkette")
lock.register_split("2005-01-01", "2017-12-31", "2026-05-21", "2026-11-20")
lock.log_trials(48, "T1 3 Varianten x 3 Horizonte, T3 3 Treiber x 2 Ziele x 2 Horizonte, "
                    "T4 2 x 2 Ziele x 3 Horizonte, T5 2 x 2 Ziele x 2 Horizonte (+ Gleichlauf beschreibend)")

TICK = {"SPX": "^GSPC", "GOLD": "GLD", "VIX": "^VIX", "DXY": "DX-Y.NYB"}
px = pd.DataFrame({k: yf.download(t, start="2004-01-01", end="2026-11-21", progress=False,
                                  auto_adjust=True)["Close"].squeeze() for k, t in TICK.items()})
px.index = pd.to_datetime(px.index).tz_localize(None)
y2 = fetch_fred("DGS2")
y2.index = pd.to_datetime(y2.index).tz_localize(None)
px["Y2"] = y2.reindex(px.index).ffill()
px = px.dropna(subset=["SPX", "GOLD", "VIX"]).ffill()
px = px.loc[:"2026-11-20"]

ret = np.log(px[["SPX", "GOLD"]]).diff() * 100
HOR = [5, 20, 60]


def fwd(col, h):
    """Log-Rendite vom Schluss t+1 bis Schluss t+1+h (in %)."""
    lp = np.log(px[col])
    return (lp.shift(-(1 + h)) - lp.shift(-1)) * 100


def test(sig, y, h, base_mask=None):
    d = pd.concat([y.rename("y"), sig.astype(float).rename("s")], axis=1).dropna()
    if base_mask is not None:
        d = d[base_mask.reindex(d.index).fillna(False)]
    out = []
    for name, sub in [("IS", lock.is_only(d)), ("OOS", lock.oos_only(d))]:
        n = int(sub["s"].sum())
        if n < 5:
            out.append(f"{name} n={n:3d} zu wenig")
            continue
        m = sm.OLS(sub["y"], sm.add_constant(sub["s"])).fit(cov_type="HAC", cov_kwds={"maxlags": h})
        ev = sub.loc[sub["s"] == 1, "y"]
        out.append(f"{name} n={n:4d} Ø {ev.mean():+6.2f} % (Rest {sub.loc[sub['s']==0,'y'].mean():+5.2f}) "
                   f"Treffer {100*(ev>0).mean():3.0f} % Δ t={m.tvalues['s']:+5.2f}")
    return " | ".join(out)


def episodes(sig, gap=10):
    idx = sig[sig].index
    if len(idx) == 0:
        return 0
    return 1 + int((pd.Series(idx).diff().dt.days > gap * 1.4).sum())


# ---------------- T1 Gold-Boden ----------------
print("\n=== T1 Gold-Bodensignal: GLD grün, S&P <= -1 % ===")
dd = (px["GOLD"] / px["GOLD"].rolling(252, min_periods=60).max() - 1) * 100
stress = (ret["GOLD"] > 0) & (ret["SPX"] <= -1)
for label, cond, base in [("ohne DD", stress, None),
                          ("DD >= 10 %", stress & (dd <= -10), dd <= -10),
                          ("DD >= 20 %", stress & (dd <= -20), dd <= -20)]:
    print(f" {label}: Tage gesamt {int(cond.sum())}, Episoden {episodes(cond)}")
    for h in HOR:
        print(f"   Gold +{h:2d}T: {test(cond, fwd('GOLD', h), h, base)}")
# Ereignisliste DD>=20 %
ev = (stress & (dd <= -20)).loc[:lock._load()["split"]["oos_end"]]  # Tresor nicht auflisten
if ev.any():
    print("  Ereignisse DD >= 20 %:", ", ".join(f"{d.date()} ({dd[d]:.0f} %)" for d in ev[ev].index))

# ---------------- T2/T3 Wochen ----------------
w = px.resample("W-FRI").last()
wk = pd.DataFrame({"dVIX": w["VIX"].diff(), "d2J": w["Y2"].diff() * 100, "dDXY": np.log(w["DXY"]).diff() * 100,
                   "SPX": np.log(w["SPX"]).diff() * 100, "GOLD": np.log(w["GOLD"]).diff() * 100}).dropna()
print("\n=== T2 Gleichlauf (Wochen, Korrelation) ===")
for name, sub in [("IS", lock.is_only(wk)), ("OOS", lock.oos_only(wk))]:
    c = sub.corr().loc[["dVIX", "d2J", "dDXY"], ["SPX", "GOLD"]]
    print(f" {name} n={len(sub)}\n{c.round(2).to_string()}")
print(" Gold~d2J je Jahr:", " ".join(f"{y}:{g['GOLD'].corr(g['d2J']):+.2f}" for y, g in wk.groupby(wk.index.year)))
print(" Gold~dVIX je Jahr:", " ".join(f"{y}:{g['GOLD'].corr(g['dVIX']):+.2f}" for y, g in wk.groupby(wk.index.year)))

print("\n=== T3 Vorlauf (Wochen): Treiber Woche t -> Ziel danach ===")
for tgt in ["SPX", "GOLD"]:
    for k, lab in [(1, "t+1"), (4, "t+1..t+4")]:
        y = sum(wk[tgt].shift(-i) for i in range(1, k + 1))
        for drv in ["dVIX", "d2J", "dDXY"]:
            d = pd.concat([y.rename("y"), wk[drv].rename("x")], axis=1).dropna()
            out = []
            for name, sub in [("IS", lock.is_only(d)), ("OOS", lock.oos_only(d))]:
                m = sm.OLS(sub["y"], sm.add_constant(sub["x"])).fit(cov_type="HAC", cov_kwds={"maxlags": k})
                out.append(f"{name} r={sub['y'].corr(sub['x']):+.2f} t={m.tvalues['x']:+5.2f}")
            print(f"  {drv:5s} -> {tgt:4s} {lab:9s} | " + " | ".join(out))

# ---------------- T4 VIX > 30 ----------------
print("\n=== T4 VIX > 30 ===")
v30 = px["VIX"] > 30
cross = v30 & ~v30.shift(1, fill_value=False)
print(f" Tage > 30: {int(v30.sum())}, Erstschlüsse über 30: {int(cross.sum())} (Episoden {episodes(cross, 20)})")
for lab, s in [("VIX-Schluss > 30", v30), ("erster Schluss > 30", cross)]:
    for tgt in ["SPX", "GOLD"]:
        for h in HOR:
            print(f"  {lab:20s} {tgt:4s} +{h:2d}T: {test(s, fwd(tgt, h), h)}")

# ---------------- T5 Dennis-Faktor ----------------
print("\n=== T5 VIX und 2J fallen beide (5 Tage) ===")
dv5 = px["VIX"].diff(5)
dy5 = px["Y2"].diff(5)
both = (dv5 < 0) & (dy5 < 0)
relax = both & (px["VIX"].shift(5) > 30)
same = {t: (np.log(px[t]) - np.log(px[t]).shift(5)) * 100 for t in ["SPX", "GOLD"]}
for lab, s in [("beide fallen", both), ("beide fallen, VIX vorher > 30", relax)]:
    print(f" {lab}: Tage {int(s.sum())}")
    for tgt in ["SPX", "GOLD"]:
        d = pd.concat([same[tgt].rename("y"), s.rename("s")], axis=1).dropna()
        print(f"   {tgt:4s} im selben Fenster: Ø {d.loc[d.s, 'y'].mean():+.2f} % vs Rest {d.loc[~d.s, 'y'].mean():+.2f} %")
        for h in [5, 20]:
            print(f"   {tgt:4s} +{h:2d}T: {test(s, fwd(tgt, h), h)}")

# Vier Quadranten Gleichlauf (Wochen) für Gold: Zins x VIX
print("\n=== Gold je Wochen-Quadrant (Gleichlauf, Ø Wochenrendite %) ===")
q = wk.assign(Z=np.where(wk.d2J < 0, "Zins fällt", "Zins steigt"), V=np.where(wk.dVIX < 0, "VIX fällt", "VIX steigt"))
for name, sub in [("IS", lock.is_only(q)), ("OOS", lock.oos_only(q))]:
    print(f" {name}\n" + sub.pivot_table(index="Z", columns="V", values=["GOLD", "SPX"], aggfunc="mean").round(2).to_string())
