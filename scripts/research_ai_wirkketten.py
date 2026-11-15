"""Wirkketten aus dem Danske „AI Investment Tracker" (19.10.2026) prüfen: tragen sie, und in welche Richtung?

Vorab festgelegt (vor dem ersten Lauf, 15.11.2026):
  Split IS 2004-2017, OOS 2018 - 15.05.2026, Tresor letzte 6 Monate (bleibt zu).
  Veröffentlichungs-Lag: Monatswert m ist erst am Ende von m+1 bekannt -> Markt-Ziel = Rendite in m+2.

  K1  China-Importpreise (FRED CHNTOT, US-Importpreise mit Ursprung China) -> Inflation -> Zins -> Gold
      x = 3-Monats-Änderung der J/J-Rate (Prozentpunkte)
      K1a  -> Änderung der US-Kern-Güter-CPI-J/J-Rate über die nächsten 6 Monate (Kette existiert?)  erwartet +
      K1b  -> DGS2-Änderung im Folgemonat (handelbar)                                                erwartet +
      K1c  -> Gold-Rendite im Folgemonat (Fed-Kanal)                                                  erwartet -
  K2  Korea-Exporte (FRED XTEXVA01KRM667S) x = 3-Monats-Änderung der J/J-Rate
      -> AUDUSD- und NDX-Rendite im Folgemonat                                                       erwartet +
  K3  Kredit-Spread (FRED BAA10Y; Variante HYG/IEF) Wochenänderung
      -> AUDUSD und NDX in der Folgewoche                                                             erwartet -
      Gegenrichtung (Aktien -> Spread) zum Prüfen der Annahme „Kredit reagiert vor Aktien".
  K4  Kupfer (HG=F) Monatsrendite -> AUDUSD im Folgemonat                                             erwartet +
      plus Gleichlauf AUD~Kupfer und AUD~NDX je Periode (hat sich die AUD-Kopplung verschoben?)
  K5  Faktencheck: Laufzeitprämie (THREEFYTP10), BAA10Y, CHNTOT J/J 2025 -> 2026 (beschreibend).
  K6  Mega-IPO-/Indexaufnahme-Tage: |NDX-Tagesrendite| als Perzentil (beschreibend, n klein).

Statistik: OLS mit HAC-Standardfehlern (Newey-West, Lags = Überlappung).
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import yfinance as yf
from scipy import stats

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research_lock import Lock  # noqa: E402
from fusion_lab.g8.data import fetch_fred  # noqa: E402

lock = Lock("ai_wirkketten")
lock.register_split("2004-01-01", "2017-12-31", "2026-05-15", "2026-11-13")
lock.log_trials(20, "K1 3 Ziele, K2 2 Ziele, K3 2 Ziele x 2 Spread-Proxies + Gegenrichtung, K4 1 + Gleichlauf")

TICK = {"AUD": "AUDUSD=X", "NDX": "^NDX", "GOLD": "GC=F", "COPPER": "HG=F", "HYG": "HYG", "IEF": "IEF"}
px = pd.DataFrame({k: yf.download(t, start="2003-01-01", end="2026-11-15", progress=False,
                                  auto_adjust=True)["Close"].squeeze() for k, t in TICK.items()})


def reg(y, x, lags, label, sign):
    d = pd.concat([y.rename("y"), x.rename("x")], axis=1).dropna()
    out = []
    for name, sub in [("IS", lock.is_only(d)), ("OOS", lock.oos_only(d))]:
        if len(sub) < 12:
            out.append(f"{name} n={len(sub)} zu wenig")
            continue
        m = sm.OLS(sub["y"], sm.add_constant(sub["x"])).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
        r = sub["y"].corr(sub["x"])
        ok = "✓" if np.sign(m.params["x"]) == sign and abs(m.tvalues["x"]) > 2 else (
            "≈" if np.sign(m.params["x"]) == sign else "✗")
        out.append(f"{name} n={len(sub):4d} r={r:+.2f} t={m.tvalues['x']:+.2f} {ok}")
    print(f"  {label:48s} | " + " | ".join(out))


def mstart(s):
    s = s.copy()
    s.index = s.index.to_period("M").to_timestamp()
    return s.groupby(level=0).last()


mpx = px.resample("MS").last()  # Monatsschluss, auf Monatsanfang gestempelt
mret = np.log(mpx).diff() * 100
d2y_m = mstart(fetch_fred("DGS2")).diff() * 100  # bp-Änderung im Monat


def yoy_chg3(series):
    s = mstart(series)
    yoy = (s / s.shift(12) - 1) * 100
    return yoy.diff(3), yoy


def to_target(x):
    """Wert für Monat m -> verwendbar für Markt-Rendite in m+2."""
    return x.shift(2)


print("\n=== K1 China-Importpreise -> Inflation -> Zins -> Gold ===")
chn_x, chn_yoy = yoy_chg3(fetch_fred("CHNTOT"))
_, cg_yoy = yoy_chg3(fetch_fred("CUSR0000SACL1E"))
reg(cg_yoy.shift(-6) - cg_yoy, chn_x, 6, "K1a -> Kern-Güter-CPI J/J, Änderung 6 M", +1)
reg(d2y_m, to_target(chn_x), 1, "K1b -> DGS2-Änderung Folgemonat (bp)", +1)
reg(mret["GOLD"], to_target(chn_x), 1, "K1c -> Gold Folgemonat", -1)
print("  Kontrolle: Gold ~ DGS2 gleichzeitig (Fed-Kanal da?)")
reg(mret["GOLD"], d2y_m, 1, "     Gold ~ DGS2-Änderung gleicher Monat", -1)

print("\n=== K2 Korea-Exporte -> AUD / Nasdaq ===")
kor_x, kor_yoy = yoy_chg3(fetch_fred("XTEXVA01KRM667S"))
reg(mret["AUD"], to_target(kor_x), 1, "K2 -> AUDUSD Folgemonat", +1)
reg(mret["NDX"], to_target(kor_x), 1, "K2 -> NDX Folgemonat", +1)
print("  Kontrolle gleichzeitig (Kette existiert, aber nicht handelbar):")
reg(mret["AUD"], kor_x, 1, "     AUDUSD ~ Korea-Exporte gleicher Monat", +1)
reg(mret["NDX"], kor_x, 1, "     NDX ~ Korea-Exporte gleicher Monat", +1)

print("\n=== K3 Kredit-Spread -> Risk-off (wöchentlich) ===")
wpx = px.resample("W-FRI").last()
wret = np.log(wpx).diff() * 100
baa = fetch_fred("BAA10Y").resample("W-FRI").last().diff() * 100  # bp
hy = -(np.log(wpx["HYG"] / wpx["IEF"]).diff() * 100)  # steigt = Spread weitet sich
for nm, sp in [("BAA10Y", baa), ("HYG/IEF", hy)]:
    reg(wret["NDX"].shift(-1), sp, 1, f"K3 {nm} -> NDX Folgewoche", -1)
    reg(wret["AUD"].shift(-1), sp, 1, f"K3 {nm} -> AUDUSD Folgewoche", -1)
    reg(sp.shift(-1), wret["NDX"], 1, f"   Gegenrichtung NDX -> {nm} Folgewoche", -1)
    reg(wret["NDX"], sp, 1, f"   Gleichlauf NDX ~ {nm} gleiche Woche", -1)
print("  4-Wochen-Blöcke (nicht überlappend), BAA10Y:")
wk = pd.concat([fetch_fred("BAA10Y").resample("W-FRI").last().rename("baa"), wpx[["NDX", "AUD"]]], axis=1).dropna()
wk = wk.iloc[::4]  # jede 4. Woche, gemeinsamer Anker
b4 = wk["baa"].diff() * 100
n4 = np.log(wk["NDX"]).diff() * 100
a4 = np.log(wk["AUD"]).diff() * 100
reg(n4.shift(-1), b4, 1, "K3 BAA10Y 4W -> NDX nächste 4W", -1)
reg(a4.shift(-1), b4, 1, "K3 BAA10Y 4W -> AUDUSD nächste 4W", -1)

print("\n=== K4 Kupfer -> AUD ===")
reg(mret["AUD"].shift(-1), mret["COPPER"], 1, "K4 Kupfer -> AUDUSD Folgemonat", +1)
print("  Gleichlauf je Periode (wöchentlich, Korrelation):")
for lo, hi in [("2004", "2012"), ("2013", "2019"), ("2020", "2022"), ("2023", "2024"), ("2025", "2026-05-15")]:
    w = wret.loc[lo:hi]
    print(f"   {lo}-{hi[:4]}: AUD~Kupfer {w['AUD'].corr(w['COPPER']):+.2f}  AUD~NDX {w['AUD'].corr(w['NDX']):+.2f}"
          f"  n={w['AUD'].count()}")

print("\n=== K5 Faktencheck (beschreibend) ===")
tp = fetch_fred("THREEFYTP10")
baa_l = fetch_fred("BAA10Y")
for dt in ["2025-01-15", "2025-10-15", "2026-01-15", "2026-06-15", "2026-10-15"]:
    print(f"  {dt}: Laufzeitprämie 10J {tp.asof(pd.Timestamp(dt)):+.2f} %  BAA10Y {baa_l.asof(pd.Timestamp(dt)):.2f} %"
          f"  DGS2 {fetch_fred('DGS2').asof(pd.Timestamp(dt)):.2f} %")
print(f"  Letzter Stand: TP {tp.index[-1].date()} {tp.iloc[-1]:+.2f}; BAA10Y {baa_l.index[-1].date()} {baa_l.iloc[-1]:.2f}")
print("  CHNTOT J/J (US-Importpreise aus China), letzte 8 Monate:")
print("   " + "  ".join(f"{i:%y-%m} {v:+.1f}" for i, v in chn_yoy.dropna().tail(8).items()))
print("  Korea-Exporte J/J, letzte 8 Monate:")
print("   " + "  ".join(f"{i:%y-%m} {v:+.1f}" for i, v in kor_yoy.dropna().tail(8).items()))
sp = fetch_fred("PCU334413334413")
sp_yoy = (mstart(sp) / mstart(sp).shift(12) - 1) * 100
print("  US-PPI Halbleiter J/J, letzte 8 Monate:")
print("   " + "  ".join(f"{i:%y-%m} {v:+.1f}" for i, v in sp_yoy.dropna().tail(8).items()))

print("\n=== K6 Mega-IPO-/Indexaufnahme-Tage: |NDX-Tagesrendite| ===")
nd = np.log(px["NDX"]).diff().dropna() * 100
absr = nd.abs()
EVENTS = {"FB IPO": "2012-05-18", "BABA IPO": "2014-09-19", "UBER IPO": "2019-05-10",
          "TSLA S&P-Aufnahme": "2020-12-18", "RIVN IPO": "2021-11-10", "ARM IPO": "2023-09-14"}
for nm, dt in EVENTS.items():
    t = pd.Timestamp(dt)
    win = absr.loc[t - pd.Timedelta(days=365):t - pd.Timedelta(days=1)]
    v = absr.get(t, np.nan)
    print(f"  {nm:20s} {dt}: NDX {nd.get(t, np.nan):+.2f} %  Perzentil im Vorjahr {(win < v).mean():.0%}")

print("\n=== Nachprüfungen (gezählt: +3) ===")
y = cg_yoy.shift(-6) - cg_yoy
keep = (y.index < "2020-07-01") | (y.index > "2022-12-31")
reg(y[keep], chn_x, 6, "K1a OOS ohne 07/2020-2022 (Inflationswelle)", +1)
reg(cg_yoy.shift(-8) - cg_yoy.shift(-2), chn_x, 6, "K1a mit 2 M Veröffentlichungs-Lag", +1)
ks = yf.download("^KS11", start="2003-01-01", end="2026-11-15", progress=False, auto_adjust=True)["Close"].squeeze()
kw = np.log(ks.resample("W-FRI").last()).diff() * 100
for lo, hi in [("2004", "2012"), ("2013", "2019"), ("2020", "2022"), ("2023", "2024"), ("2025", "2026-05-15")]:
    print(f"   {lo}-{hi[:4]}: AUD~KOSPI {wret['AUD'].loc[lo:hi].corr(kw.loc[lo:hi]):+.2f}")

print("\n=== K3b Kette ki_schulden_hy 1:1 (chains.py): HY 20T > +25 bp UND VIX < 20 -> NDX nächste 20 T ===")
hy_oas = fetch_fred("BAMLH0A0HYM2")
vix = yf.download("^VIX", start="1996-01-01", end="2026-11-15", progress=False, auto_adjust=True)["Close"].squeeze()
ndx_d = px["NDX"]
d = pd.concat([hy_oas.rename("hy"), vix.rename("vix"), ndx_d.rename("ndx")], axis=1).dropna()
d["hy20"] = d["hy"].diff(20) * 100
d["fwd"] = (np.log(d["ndx"]).shift(-20) - np.log(d["ndx"])) * 100
d["sig"] = (d["hy20"] > 25) & (d["vix"] < 20)
# nicht überlappend: erster Signaltag, dann 20 Tage Sperre
ev, last = [], None
for t, row in d[d["sig"]].iterrows():
    if last is None or (d.index.get_loc(t) - d.index.get_loc(last)) >= 20:
        ev.append(t); last = t
print(f"  HY-Historie {hy_oas.index.min().date()} - {hy_oas.index.max().date()}, n Tage {len(d)}")
base = d["fwd"].iloc[::20].dropna()
for nm, f in [("IS", lock.is_only), ("OOS", lock.oos_only)]:
    e = f(d.loc[ev, "fwd"].dropna())
    b = f(base)
    print(f"  {nm}: Signale {len(e):2d}  NDX 20T danach Ø {e.mean():+.2f} %  (fällt {(e < 0).mean():.0%})"
          f"  | alle 20T-Blöcke Ø {b.mean():+.2f} % (fällt {(b < 0).mean():.0%})")
    print("     " + "  ".join(f"{t:%Y-%m-%d} {v:+.1f}" for t, v in e.items()))

print("\n=== K3c Ersatz mit langer Historie: HYG/IEF 20T < -2 % UND VIX < 20 -> NDX nächste 20 T ===")
r = pd.concat([np.log(px["HYG"] / px["IEF"]).rename("hi"), vix.rename("vix"), ndx_d.rename("ndx")], axis=1).dropna()
r["hi20"] = r["hi"].diff(20) * 100
r["fwd"] = (np.log(r["ndx"]).shift(-20) - np.log(r["ndx"])) * 100
sig = r.index[(r["hi20"] < -2) & (r["vix"] < 20)]
ev, last = [], None
for t in sig:
    if last is None or (r.index.get_loc(t) - r.index.get_loc(last)) >= 20:
        ev.append(t); last = t
base = r["fwd"].iloc[::20].dropna()
for nm, f in [("IS", lock.is_only), ("OOS", lock.oos_only)]:
    e = f(r.loc[ev, "fwd"].dropna()); b = f(base)
    print(f"  {nm}: Signale {len(e):2d}  NDX 20T danach Ø {e.mean():+.2f} % (fällt {(e < 0).mean():.0%})"
          f"  | alle 20T-Blöcke Ø {b.mean():+.2f} % (fällt {(b < 0).mean():.0%})"
          f"  | Welch t={stats.ttest_ind(e, b, equal_var=False)[0]:+.2f}")
