"""Tagesend-Momentum nach Baltussen et al. (JFE 2021), mit echtem Dealer-Gamma.

Nutzerauftrag 2026-10-06: "Teste gerne mal den Baltussen-Edge als
Zwangsbedingung." Mechanismus (Feld 1, strukturelle Flows): Dealer, die short
Gamma sind, und gehebelte ETFs muessen vor Handelsschluss IN Bewegungsrichtung
nachhandeln. Wer zahlt: diese Zwangs-Hedger.

REGEL 1:1 aus dem Paper (keine Optimierung): Rendite vom Schluss des Vortags
(15:59-Bar) bis 15:30 NY ("rest of day") -> Einstieg um 15:30 in diese Richtung,
Ausstieg 16:00. Kosten: gemessener Spread + Slippage je Rundturn.

GAMMA: SqueezeMetrics-GEX (SPX, taeglich, Dollar-Gamma je 1 % Bewegung),
eingefroren in scripts/frozen_data/sqzme_dix_gex_20261006.csv. Verwendet wird
der Wert vom VORTAG (vor der Eroeffnung bekannt). Fuer NASDAQ dient SPX-GEX als
Naeherung.

VORAB FESTGELEGTE VARIANTEN (5 Trials, Lock baltussen_late_momentum_20261006):
  A  immer
  B  GEX Vortag < 0                            (Dealer short Gamma)
  C  GEX Vortag im unteren Fuenftel der letzten 252 Tage (relativ wenig Gamma)
  D  |Rest-of-day-Rendite| im oberen Drittel der letzten 60 Tage (grosser Hedge-Bedarf)
  E  C und D
SPLIT: IS 2016-07-28..2022-12-31 | OOS 2023-01-01..2026-09-30 (Bericht 2023-24 / 2025-26)
Die Regel ist fix; Auswahl findet nicht statt, IS/OOS dient nur der Stabilitaetspruefung.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).resolve().parent))

import challenge_portfolio.paper_bot as pb  # noqa: E402
from ny_open_orb.data import fetch_m1  # noqa: E402
from research_lock import Lock  # noqa: E402
from research_orb_cancel_at_sl_and_hold import ENTRY_SLIPPAGE_BPS, EXIT_SLIPPAGE_BPS, SPREAD_BPS  # noqa: E402

STRATEGY = "baltussen_late_momentum_20261006"
IS_START, IS_END, OOS_END = "2016-07-28", "2022-12-31", "2026-09-30"
RES = ROOT / "ny_open_orb" / "results"
GEX_FILE = ROOT / "scripts" / "frozen_data" / "sqzme_dix_gex_20261006.csv"
VARIANTS = ["A immer", "B GEX<0", "C GEX unteres Fuenftel", "D grosse Tagesbewegung", "E C+D"]
PERIODS = [("IS 2016-2022", IS_START, "2023-01-01"), ("OOS 2023-2024", "2023-01-01", "2025-01-01"),
           ("OOS 2025-09/2026", "2025-01-01", "2026-10-01")]


def sessions_table(inst: str) -> pd.DataFrame:
    m1 = pb._retry(lambda: fetch_m1(inst, IS_START, OOS_END), attempts=3, delay_seconds=5, timeout_seconds=1800)
    m1 = m1.copy()
    m1["date"] = m1.index.tz_localize(None).normalize()
    hm = m1.index.hour * 60 + m1.index.minute
    p1530 = m1[hm == 15 * 60 + 29].groupby("date")["close"].last()
    p1600 = m1[hm == 15 * 60 + 59].groupby("date")["close"].last()
    t = pd.DataFrame({"p1530": p1530, "p1600": p1600}).dropna()
    t["prev_close"] = t["p1600"].shift(1)
    t = t.dropna()
    t["rod"] = t["p1530"] / t["prev_close"] - 1
    t["lh"] = t["p1600"] / t["p1530"] - 1
    cost = (SPREAD_BPS[inst] + ENTRY_SLIPPAGE_BPS + EXIT_SLIPPAGE_BPS)
    t["gross_bps"] = np.sign(t["rod"]) * t["lh"] * 1e4
    t["net_bps"] = t["gross_bps"] - cost
    gex = pd.read_csv(GEX_FILE, parse_dates=["date"]).set_index("date")["gex"].sort_index()
    t["gex_prev"] = gex.shift(1).reindex(t.index, method="ffill")
    t["gex_q20"] = gex.shift(1).rolling(252, min_periods=120).quantile(0.2).reindex(t.index, method="ffill")
    big = t["rod"].abs().shift(1).rolling(60, min_periods=30).quantile(0.67)
    t["big_move"] = t["rod"].abs() > big
    masks = {
        "A immer": pd.Series(True, index=t.index),
        "B GEX<0": t["gex_prev"] < 0,
        "C GEX unteres Fuenftel": t["gex_prev"] < t["gex_q20"],
        "D grosse Tagesbewegung": t["big_move"],
    }
    masks["E C+D"] = masks["C GEX unteres Fuenftel"] & masks["D grosse Tagesbewegung"]
    for k, v in masks.items():
        t[k] = v.fillna(False)
    return t


def stats(x: pd.Series) -> dict:
    if len(x) < 5:
        return {"n": len(x)}
    yrs = max((x.index.max() - x.index.min()).days / 365.25, 0.25)
    return {"n": len(x), "per_year": len(x) / yrs, "net_bps": x.mean(), "hit": (x > 0).mean(),
            "t": x.mean() / x.std(ddof=1) * np.sqrt(len(x)),
            "sharpe_pa": x.mean() / x.std(ddof=1) * np.sqrt(len(x) / yrs), "sum_bps": x.sum()}


def main() -> int:
    lk = Lock(STRATEGY)
    lk.register_split(IS_START, IS_END, OOS_END)
    st = lk._load()
    if st["trials"] == 0:
        lk.log_trials(len(VARIANTS), note="Paper-Regel fix, 5 vorab festgelegte Gamma-/Bewegungs-Bedingungen")
    h = lk.freeze({"regel": "sign(rest of day bis 15:30) -> 15:30-16:00", "varianten": VARIANTS})
    if "oos" not in lk._load()["unsealed"]:
        lk.unseal("oos", h)
    rows, gex_years = [], []
    for inst in ("SP500", "NASDAQ"):
        t = sessions_table(inst)
        t.to_csv(RES / f"baltussen_sessions_{inst}.csv")
        for v in VARIANTS:
            for per, a, b in PERIODS:
                sub = t[(t.index >= a) & (t.index < b) & t[v]]
                rows.append({"inst": inst, "variante": v, "periode": per, **stats(sub["net_bps"]),
                             "gross_bps": sub["gross_bps"].mean() if len(sub) else np.nan})
        # Gegenprobe: bei positivem Gamma sollte Momentum NICHT funktionieren
        for per, a, b in PERIODS:
            sub = t[(t.index >= a) & (t.index < b) & (t["gex_prev"] > t["gex_prev"].rolling(252, min_periods=120).quantile(0.8))]
            rows.append({"inst": inst, "variante": "Gegenprobe GEX oberes Fuenftel", "periode": per,
                         **stats(sub["net_bps"]), "gross_bps": sub["gross_bps"].mean() if len(sub) else np.nan})
        if inst == "SP500":
            g = t.groupby(t.index.year).agg(gex_median=("gex_prev", "median"), anteil_gex_neg=("B GEX<0", "mean"),
                                            anteil_unteres_fuenftel=("C GEX unteres Fuenftel", "mean"))
            gex_years.append(g)
    rep = pd.DataFrame(rows)
    rep.to_csv(RES / "baltussen_report.csv", index=False)
    pd.set_option("display.width", 250)
    for inst in ("SP500", "NASDAQ"):
        print(f"\n===== {inst} (netto bps je Trade nach Kosten) =====")
        g = rep[rep.inst == inst]
        print(g.pivot(index="variante", columns="periode", values="net_bps").round(2).to_string())
        print("t-Wert:\n", g.pivot(index="variante", columns="periode", values="t").round(2).to_string())
        print("Trades:\n", g.pivot(index="variante", columns="periode", values="n").to_string())
    print("\nSPX-GEX je Jahr (Vortag):\n", gex_years[0].assign(gex_median=lambda d: (d.gex_median / 1e9).round(2)).round(3).to_string())
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
