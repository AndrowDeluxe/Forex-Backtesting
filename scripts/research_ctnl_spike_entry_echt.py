"""CTNL: Spike-Einstieg ECHT simuliert (2026-09-25)

Loest die methodische Grenze aus Befund 17 auf. Der erste Versuch
(`research_ctnl_spike_entry.py`) rechnete nur den Einstiegspreis neu und
uebernahm die `mae_r` des urspruenglichen Trades -- damit war die
Kernbehauptung des Nutzers ("fast kein Drawdown, BE fast sofort moeglich")
NICHT pruefbar, und die BE-Zahlen dort waren ein Artefakt der Umrechnung.

Jetzt laeuft der Trade Bar fuer Bar AB DEM NEUEN EINSTIEG neu durch die
Engine (`strategy/backtest.py`, neuer `entry_mode`/`entry_wait_bars`):
MFE, MAE, Stop, Ziel und Haltedauer werden alle aus der Fuellbar heraus
gerechnet. Die MAE ist damit die echte.

GEPRUEFTE EINSTIEGE
  next_open             -- heute: Marktorder zum Open der Folgebar
  limit_trigger_level   -- Limit auf das gesweepte Strukturlevel
                           (prev_low/prev_high) -- dort liegt die Liquiditaet
  limit_signal_extreme  -- Limit auf das Extrem der Signalbar (der Spike selbst),
                           optimistischer
jeweils mit Wartefenstern von 0, 2 und 6 Bars, dazu der Ribbon-Richtungsfilter
aus Befund 15 und Breakeven-Stufen.

EHRLICHE GRENZE, DIE BLEIBT
"Tief beruehrt" ist nicht "Order gefuellt" (Spread in der Spitze,
Teilfuellung, Slippage). Die Fuellquoten sind weiterhin optimistisch. Was
sich gegenueber dem ersten Versuch aendert: die MAE und alles davon
Abgeleitete sind jetzt echt gerechnet, nicht umskaliert.
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
from gold_smc_htf_ltf.data import fetch_gold_d1, fetch_gold_w1  # noqa: E402
from gold_smc_htf_ltf.live_signal import REV_KWARGS, REV_MAX_CONCURRENT  # noqa: E402
from gold_smc_htf_ltf.reversal_cascade import run_pipeline as run_reversal  # noqa: E402
from monte_carlo import run_monte_carlo  # noqa: E402
from research_ctnl_execution_costs import _cap_concurrent, _utc_naive, load_bars  # noqa: E402
from research_ctnl_optimization import MEASURED_BPS, anchored_walk_forward, surface, to_live  # noqa: E402
from research_ctnl_ribbon_both_legs import ribbon_direction, stats  # noqa: E402
from strategy.backtest import BacktestConfig, simulate_trades  # noqa: E402

JUNG = pd.Timestamp("2024-01-01")


def bauen(sig: pd.DataFrame, *, entry_mode: str, wait: int, be: float | None) -> pd.DataFrame:
    cfg = BacktestConfig(spread_bps=MEASURED_BPS, stop_atr_mult=3.0, use_vwap_target=False,
                         take_profit_r=5.0, max_hold_bars=96 * 4, breakeven_trigger_r=be,
                         entry_mode=entry_mode, entry_wait_bars=wait)
    tr = simulate_trades_concurrent(sig, cfg) if entry_mode == "next_open" else simulate_trades(sig, cfg)
    return _cap_concurrent(tr, REV_MAX_CONCURRENT)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default="2016-01-01")
    ap.add_argument("--end", default=pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d"))
    ap.add_argument("--out", type=Path,
                    default=REPO_DIR / "knowledge" / "_data" / "ctnl_spike_entry_echt.json")
    args = ap.parse_args()

    bars = load_bars(args.start, args.end)
    rib = ribbon_direction(bars["h4"], fetch_gold_d1(args.start, args.end),
                           fetch_gold_w1(args.start, args.end))
    sig = run_reversal(bars["h4"], bars["h1"], bars["m15"], **REV_KWARGS)
    n_sig = int((sig["signal"] != 0).sum())
    print(f"Rohsignale: {n_sig}")

    kandidaten = [("next_open", 0, None)]
    for modus in ("limit_trigger_level", "limit_signal_extreme"):
        for wait in (0, 2, 6):
            kandidaten.append((modus, wait, None))
    # Breakeven nur auf dem realistischeren Level-Limit
    for be in (0.25, 0.5, 1.0):
        kandidaten.append(("limit_trigger_level", 2, be))

    result: dict = {"rohsignale": n_sig, "varianten": {}}
    varianten: dict = {}

    print(f"\n  {'Variante':>34} {'Trades':>7} {'Quote':>7} {'MAE p50':>8} {'MAE p90':>8} {'ØR':>8}")
    for modus, wait, be in kandidaten:
        tr = bauen(sig, entry_mode=modus, wait=wait, be=be)
        if tr.empty:
            continue
        rep = to_live(tr, bars["m15"]) if modus == "next_open" else tr.copy()
        if modus != "next_open":
            # kein Lag noetig: die Limit-Order liegt im Markt, sie wird
            # beruehrt oder nicht -- ein Scan-Versatz aendert daran nichts.
            rep = rep.assign(r=rep["r_multiple"], entry_time=rep["entry_time"],
                             direction=rep["direction"])
            rep["jahr"] = _utc_naive(rep["entry_time"]).dt.year
        rep = rep.assign(rib=rib.reindex(_utc_naive(rep["entry_time"]), method="ffill").to_numpy())
        label = f"{modus}/w{wait}" + (f"/BE{be:g}" if be else "")
        varianten[label] = rep
        varianten[label + " +ribbon"] = rep[((rep["direction"] == 1) & (rep["rib"] > 0)) |
                                            ((rep["direction"] == -1) & (rep["rib"] < 0))]
        mae = tr["mae_r"].abs().dropna()
        st = stats(rep["r"])
        print(f"  {label:>34} {len(tr):>7} {len(tr)/n_sig:>6.1%} "
              f"{mae.median():>8.2f} {mae.quantile(0.90):>8.2f} {st['avg_r']:>+8.3f}")

    print()
    result["flaeche"] = surface(varianten, "ctnl_reversal: Einstieg, echt simuliert")

    print(f"\n  Nur 2024-2026:")
    print(f"    {'Variante':>34} {'n':>5} {'ØR':>8} {'ΣR':>8} {'PF':>6}")
    result["jung"] = {}
    for name, d in varianten.items():
        j = stats(d[_utc_naive(d["entry_time"]) >= JUNG]["r"])
        result["jung"][name] = j
        print(f"    {name:>34} {j['trades']:>5} {j['avg_r']:>+8.3f} {j['summe_r']:>+8.1f} {j['profit_factor']:>6.2f}")

    result["walkforward"] = anchored_walk_forward(varianten, "next_open/w0",
                                                  "ctnl_reversal: Einstieg")

    print(f"\n  Monte Carlo (0,15 %/Trade):")
    print(f"    {'Variante':>34} {'MedDD':>9} {'P(>6%)':>8} {'Return':>9} {'Sharpe':>8}")
    result["monte_carlo"] = {}
    for name, d in varianten.items():
        daily = (d.set_index(_utc_naive(d["entry_time"]))["r"] * 0.0015).resample("D").sum()
        daily = daily[daily.index.dayofweek < 5]
        if len(daily) < 250:
            continue
        m = run_monte_carlo(daily, initial_equity=100_000.0, block_size=20, n_sims=2000, seed=42)
        s = m["summary"] if isinstance(m, dict) and "summary" in m else m
        dd = s["max_drawdown_pct"]
        result["monte_carlo"][name] = {
            "median_maxdd_pct": float(np.median(dd)),
            "P_maxdd_ueber_6pct": float((np.abs(dd) > 6).mean()),
            "median_return_pct": float(np.median(s["total_return_pct"])),
            "median_sharpe": float(np.median(s["sharpe"]))}
        r_ = result["monte_carlo"][name]
        print(f"    {name:>34} {r_['median_maxdd_pct']:>8.2f}% {r_['P_maxdd_ueber_6pct']:>7.1%} "
              f"{r_['median_return_pct']:>8.1f}% {r_['median_sharpe']:>8.2f}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"\nGeschrieben: {args.out}")


if __name__ == "__main__":
    main()
