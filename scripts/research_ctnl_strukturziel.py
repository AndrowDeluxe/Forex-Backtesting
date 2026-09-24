"""CTNL: Strukturziel statt festem R-Ziel -- naeher an der eigenen Handelslogik
(2026-09-24)

Nutzerbeschreibung (mit zwei M15-Charts der eigenen Trades belegt): Einstieg
nach dem Sweep eines Levels, Ziel an der NAECHSTEN LIQUIDITAET -- nicht an
einem festen R-Vielfachen. Beide Beine handeln beide Richtungen.

DAS ZIEL IST BEREITS IMPLEMENTIERT, NUR NICHT VERDRAHTET
`use_vwap_target=True` setzt bei diesen Pipelines NICHT VWAP, sondern
`h1_target` -- das naechste H4/H1-Strukturlevel (siehe continuation.py:292:
"vwap=h1_target always set for the h4_level/use_vwap_target"). In
`research_gold_smc_reversal_cascade.py` lief das als `tp_mode="h4_level"`
gegen `tp_mode="atr"` im Sweep.

Die gesperrte REV-Config nutzt stattdessen `use_vwap_target=False,
take_profit_r=5.0`. Das Strukturziel wurde also damals verglichen und
verworfen -- aber (a) nur auf dem IS-Fenster 2024-08/2025-08 und (b) ohne
Richtungsfilter. Mit dem Ribbon-Gate (Befund 15) ist die Ausgangslage eine
andere: wenn die Richtung stimmt, koennte ein strukturelles Ziel besser
passen als ein starres 5R.

GEPRUEFT WIRD
  Ziel:     5R (gesperrt) | Strukturziel (h1_target) | Struktur + BE-Stop
  Richtung: ungefiltert   | ribbon-konform           | ribbon long-only
Das Kreuzprodukt, jeweils durch Anker-Walk-Forward und Monte Carlo.

Das Continuation-Bein faehrt das Strukturziel bereits (`use_vwap_target=True`
in CONT_CFG) -- dort wird stattdessen die Gegenprobe gerechnet: was bringt
ein festes R-Ziel, und traegt ein weiterer Stop als die sehr engen 0,5 ATR?
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_DIR))
sys.path.insert(0, str(REPO_DIR / "scripts"))
sys.path.insert(0, str(REPO_DIR / "ou_paper_backtest"))

from gold_smc_htf_ltf.concurrent_backtest import simulate_trades_concurrent  # noqa: E402
from gold_smc_htf_ltf.continuation import run_pipeline as run_continuation  # noqa: E402
from gold_smc_htf_ltf.data import fetch_gold_d1, fetch_gold_w1  # noqa: E402
from gold_smc_htf_ltf.live_signal import CONT_KWARGS, REV_KWARGS, REV_MAX_CONCURRENT  # noqa: E402
from gold_smc_htf_ltf.reversal_cascade import run_pipeline as run_reversal  # noqa: E402
from monte_carlo import run_monte_carlo  # noqa: E402
from research_ctnl_execution_costs import _cap_concurrent, _utc_naive, load_bars  # noqa: E402
from research_ctnl_optimization import MEASURED_BPS, anchored_walk_forward, surface, to_live  # noqa: E402
from research_ctnl_ribbon_both_legs import ribbon_direction, stats  # noqa: E402
from strategy.backtest import BacktestConfig, simulate_trades  # noqa: E402

RISK_PCT = {"ctnl_reversal": 0.0015, "ctnl_continuation": 0.005}
JUNG = pd.Timestamp("2024-01-01")


def rev_trades(bars: dict, *, ziel: str, be: float | None = None) -> pd.DataFrame:
    cfg = dict(spread_bps=MEASURED_BPS, stop_atr_mult=3.0, max_hold_bars=96 * 4,
               breakeven_trigger_r=be)
    if ziel == "5R":
        cfg.update(use_vwap_target=False, take_profit_r=5.0)
    elif ziel == "struktur":
        cfg.update(use_vwap_target=True)
    else:
        raise ValueError(ziel)
    sig = run_reversal(bars["h4"], bars["h1"], bars["m15"], **REV_KWARGS)
    tr = simulate_trades_concurrent(sig, BacktestConfig(**cfg))
    return _cap_concurrent(tr, REV_MAX_CONCURRENT)


def cont_trades(bars: dict, *, ziel: str, stop: float) -> pd.DataFrame:
    cfg = dict(spread_bps=MEASURED_BPS, stop_atr_mult=stop, max_hold_bars=24 * 12,
               breakeven_trigger_r=None)
    if ziel == "struktur":
        cfg.update(use_vwap_target=True)
    else:
        cfg.update(use_vwap_target=False, take_profit_r=float(ziel.rstrip("R")))
    sig = run_continuation(bars["h4"], bars["h1"], bars["m5"], trend_df=bars["m15"], **CONT_KWARGS)
    return simulate_trades(sig, BacktestConfig(**cfg))


def mc(d: pd.DataFrame, risk_pct: float) -> dict:
    daily = (d.set_index(_utc_naive(d["entry_time"]))["r"] * risk_pct).resample("D").sum()
    daily = daily[daily.index.dayofweek < 5]
    if len(daily) < 250:
        return {}
    m = run_monte_carlo(daily, initial_equity=100_000.0, block_size=20, n_sims=2000, seed=42)
    s = m["summary"] if isinstance(m, dict) and "summary" in m else m
    dd = s["max_drawdown_pct"]
    return {"median_maxdd_pct": float(np.median(dd)),
            "P_maxdd_ueber_6pct": float((np.abs(dd) > 6).mean()),
            "median_return_pct": float(np.median(s["total_return_pct"])),
            "median_sharpe": float(np.median(s["sharpe"]))}


def bewerte(varianten: dict, leg: str, titel: str, baseline: str, res: dict) -> None:
    print(f"\n  {titel}")
    print(f"    {'Variante':>26} | {'--- 2016-2026 ---':^32} | {'-- 2024-2026 --':^26}")
    print(f"    {'':>26} | {'n':>5} {'ØR':>8} {'ΣR':>8} {'PF':>6} | {'n':>4} {'ØR':>8} {'PF':>6}")
    for name, d in varianten.items():
        v, j = stats(d["r"]), stats(d[_utc_naive(d["entry_time"]) >= JUNG]["r"])
        res.setdefault("vergleich", {})[name] = {"voll": v, "2024_2026": j}
        print(f"    {name:>26} | {v['trades']:>5} {v['avg_r']:>+8.3f} {v['summe_r']:>+8.1f} "
              f"{v['profit_factor']:>6.2f} | {j['trades']:>4} {j['avg_r']:>+8.3f} {j['profit_factor']:>6.2f}")
    res["walkforward"] = anchored_walk_forward(varianten, baseline, titel)
    print(f"\n    Monte Carlo ({RISK_PCT[leg]:.2%}/Trade):")
    print(f"      {'Variante':>26} {'MedDD':>9} {'P(>6%)':>8} {'Return':>9} {'Sharpe':>8}")
    res["monte_carlo"] = {}
    for name, d in varianten.items():
        m = mc(d, RISK_PCT[leg])
        if not m:
            continue
        res["monte_carlo"][name] = m
        print(f"      {name:>26} {m['median_maxdd_pct']:>8.2f}% {m['P_maxdd_ueber_6pct']:>7.1%} "
              f"{m['median_return_pct']:>8.1f}% {m['median_sharpe']:>8.2f}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default="2016-01-01")
    ap.add_argument("--end", default=pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d"))
    ap.add_argument("--out", type=Path,
                    default=REPO_DIR / "knowledge" / "_data" / "ctnl_strukturziel.json")
    args = ap.parse_args()

    bars = load_bars(args.start, args.end)
    rib = ribbon_direction(bars["h4"], fetch_gold_d1(args.start, args.end),
                           fetch_gold_w1(args.start, args.end))
    result: dict = {}

    def gate(rep: pd.DataFrame, modus: str) -> pd.DataFrame:
        r = rep.assign(rib=rib.reindex(_utc_naive(rep["entry_time"]), method="ffill").to_numpy())
        if modus == "alle":
            return r
        if modus == "konform":
            return r[((r["direction"] == 1) & (r["rib"] > 0)) | ((r["direction"] == -1) & (r["rib"] < 0))]
        return r[(r["direction"] == 1) & (r["rib"] > 0)]

    # ---------------- REVERSAL: Ziel x Richtung
    print(f"\n{'='*98}\nctnl_reversal -- Strukturziel gegen festes 5R-Ziel\n{'='*98}")
    roh = {"5R": to_live(rev_trades(bars, ziel="5R"), bars["m15"]),
           "Struktur": to_live(rev_trades(bars, ziel="struktur"), bars["m15"]),
           "Struktur+BE": to_live(rev_trades(bars, ziel="struktur", be=1.0), bars["m15"])}
    for k, v in roh.items():
        print(f"  {k}: {len(v)} handelbare Trades")
    varianten = {f"{z} / {m}": gate(d, m)
                 for z, d in roh.items() for m in ("alle", "konform", "long-only")}
    result["ctnl_reversal"] = {}
    bewerte(varianten, "ctnl_reversal", "ctnl_reversal: Ziel x Richtung",
            "5R / alle", result["ctnl_reversal"])

    # ---------------- CONTINUATION: Gegenprobe Ziel + Stopweite
    print(f"\n{'='*98}\nctnl_continuation -- Gegenprobe: Ziel und Stopweite\n{'='*98}")
    roh2 = {}
    for stop in (0.5, 1.0, 2.0):
        roh2[f"Struktur/stop{stop:g}"] = to_live(cont_trades(bars, ziel="struktur", stop=stop), bars["m5"])
    roh2["3R/stop1.0"] = to_live(cont_trades(bars, ziel="3R", stop=1.0), bars["m5"])
    for k, v in roh2.items():
        print(f"  {k}: {len(v)} handelbare Trades")
    varianten2 = {f"{z} / {m}": gate(d, m)
                  for z, d in roh2.items() for m in ("alle", "konform")}
    result["ctnl_continuation"] = {}
    bewerte(varianten2, "ctnl_continuation", "ctnl_continuation: Ziel/Stop x Richtung",
            "Struktur/stop0.5 / alle", result["ctnl_continuation"])

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"\nGeschrieben: {args.out}")


if __name__ == "__main__":
    main()
