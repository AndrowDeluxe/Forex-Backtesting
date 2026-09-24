"""CTNL: Einstieg AM Liquidity Spike statt zum Open der Folgebar (2026-09-24)

Nutzerbeschreibung: "Mein Entry sind immer H4 und hoehere Liquidity Spikes und
interessante Preislevel wie z.B. OBs, Newscandles oder Wholelevel. M5 BOS und
dann Entry bei Liq Spike -- mit meiner Variante bin ich fast nicht gross im
Drawdown und kann fast immer direkt BE setzen."

DIE STRUKTURELLE LUECKE, DIE DAS AUFDECKT
Die Engine steigt zum OPEN DER FOLGEBAR ein (strategy/backtest.py:
`raw_entry = open_[entry_i]`, entry_i = Signalbar + 1). Der Spike selbst
passiert WAEHREND der Signalbar; zum Open der Folgebar ist der Kurs davon
schon zurueckgelaufen. Genau das zeigt Befund 7d: die MAE der GEWINNER liegt
bei Median 0,50R, p90 bei 0,87R -- die Gewinner gehen routinemaessig tief ins
Minus, bevor sie laufen. Beim beschriebenen Einstieg am Spike kann das
strukturell nicht passieren.

WAS HIER GERECHNET WIRD
Statt der Marktorder auf die Folgebar eine LIMIT-Order auf das gesweepte
Extrem der Signalbar:
  * Fill nur, wenn der Kurs das Level innerhalb von `wait_bars` Bars
    wieder erreicht -- sonst FAELLT DER TRADE AUS (das ist der Preis dieser
    Variante und wird als Fuellquote ausgewiesen).
  * Das Stop-NIVEAU bleibt unveraendert (es haengt am Signal, nicht am
    Einstieg). Ein besserer Einstieg heisst damit: kleinere Risikodistanz,
    groesseres R bei derselben Bewegung.
  * Ausstiegsseite unveraendert.

Damit wird nachpruefbar, was der Nutzer beobachtet: faellt die MAE, steigt
das R, und wie teuer ist die Nicht-Fuellung?

EHRLICHE GRENZE DIESER SIMULATION
Ob eine Limit-Order an einem durchlaufenen Level wirklich gefuellt wird, sagt
eine OHLC-Bar nicht -- "Tief beruehrt" und "Order gefuellt" sind nicht
dasselbe (Spread, Slippage in der Spitze, Teilfuellung). Die Rechnung ist
deshalb OPTIMISTISCH und beantwortet "wie gross waere der Effekt maximal",
nicht "so viel bringt es sicher". Sie taugt zur Groessenordnung, nicht als
Ertragsversprechen.

Zusaetzlich getestet: frueher Breakeven-Stop (0,25R / 0,5R), der beim
Nutzer funktioniert -- er sollte bei kleiner MAE billig sein.
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

from gold_smc_htf_ltf.data import fetch_gold_d1, fetch_gold_w1  # noqa: E402
from gold_smc_htf_ltf.live_signal import REV_KWARGS  # noqa: E402
from monte_carlo import run_monte_carlo  # noqa: E402
from research_ctnl_execution_costs import _utc_naive, load_bars, stop_level  # noqa: E402
from research_ctnl_optimization import MEASURED_BPS, anchored_walk_forward, leg_trades, surface  # noqa: E402
from research_ctnl_ribbon_both_legs import ribbon_direction, stats  # noqa: E402

JUNG = pd.Timestamp("2024-01-01")
MAX_CONSUMED_R = 0.50


def spike_entry(trades: pd.DataFrame, bars: pd.DataFrame, wait_bars: int,
                be_trigger: float | None = None) -> pd.DataFrame:
    """Limit-Order auf das Extrem der Signalbar statt Marktorder zum Open.

    Signalbar = Entry-Bar der Engine minus 1. Ihr Tief (long) bzw. Hoch
    (short) ist das gesweepte Level -- dort liegt der Liquidity Spike.
    """
    idx = _utc_naive(bars.index)
    pos = {t: i for i, t in enumerate(idx)}
    op, hi, lo = (bars[c].to_numpy() for c in ("open", "high", "low"))
    half = MEASURED_BPS / 10_000.0 / 2.0

    rows = []
    for _, t in trades.iterrows():
        i = pos.get(_utc_naive(t["entry_time"]))
        if i is None or i < 1 or i + wait_bars >= len(op):
            continue
        d = int(t["direction"])
        sl = stop_level(t)
        planned = float(t["initial_risk"])
        if planned <= 0:
            continue

        # Das gesweepte Extrem der SIGNALBAR (i-1)
        level = lo[i - 1] if d == 1 else hi[i - 1]

        # Fill, sobald der Kurs das Level in den naechsten wait_bars erreicht
        seg = slice(i, i + wait_bars + 1)
        touched = (lo[seg] <= level).any() if d == 1 else (hi[seg] >= level).any()
        if not touched:
            rows.append({"entry_time": t["entry_time"], "gefuellt": False})
            continue

        entry = level * (1 + d * half)
        eff = (entry - sl) * d
        if eff <= 0:
            rows.append({"entry_time": t["entry_time"], "gefuellt": False})
            continue
        consumed = (planned - eff) / planned
        if consumed > MAX_CONSUMED_R:      # R-Detektor, wie live
            rows.append({"entry_time": t["entry_time"], "gefuellt": False})
            continue

        exit_price = float(t["exit_price"])
        mae_r = abs(float(t.get("mae_r", np.nan))) * planned / eff if eff > 0 else np.nan
        r = d * (exit_price - entry) / eff
        # Frueher Breakeven: haette die MAE ihn ausgeloest, endet der Trade bei 0
        if be_trigger is not None and np.isfinite(mae_r) and mae_r >= be_trigger and r > 0:
            r = 0.0
        rows.append({"entry_time": t["entry_time"], "exit_time": t["exit_time"],
                     "direction": d, "gefuellt": True, "entry": entry,
                     "effective_risk": eff, "mae_r": mae_r, "r": r,
                     "entry_backtest": float(t["entry_price"])})
    df = pd.DataFrame(rows)
    if not df.empty and "r" in df:
        df["jahr"] = _utc_naive(df["entry_time"]).dt.year
    return df


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default="2016-01-01")
    ap.add_argument("--end", default=pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d"))
    ap.add_argument("--out", type=Path,
                    default=REPO_DIR / "knowledge" / "_data" / "ctnl_spike_entry.json")
    args = ap.parse_args()

    bars = load_bars(args.start, args.end)
    rib = ribbon_direction(bars["h4"], fetch_gold_d1(args.start, args.end),
                           fetch_gold_w1(args.start, args.end))
    tr = leg_trades(bars, "ctnl_reversal", tp_r=5.0, sig_kwargs=REV_KWARGS)
    print(f"Signal-Trades: {len(tr)}")

    result: dict = {}
    varianten: dict = {}

    # Referenz: der heutige Einstieg (Marktorder Folgebar, Lag 1)
    from research_ctnl_optimization import to_live
    ref = to_live(tr, bars["m15"])
    ref = ref.assign(rib=rib.reindex(_utc_naive(ref["entry_time"]), method="ffill").to_numpy())
    varianten["heute: Markt Folgebar"] = ref
    varianten["heute + ribbon"] = ref[((ref["direction"] == 1) & (ref["rib"] > 0)) |
                                      ((ref["direction"] == -1) & (ref["rib"] < 0))]

    print(f"\n  {'Variante':>28} {'Signale':>8} {'gefuellt':>9} {'Quote':>7} {'MAE p50':>8} {'MAE p90':>8}")
    st = stats(ref["r"])
    print(f"  {'heute: Markt Folgebar':>28} {len(ref):>8} {'—':>9} {'—':>7} "
          f"{abs(ref['r']).median():>8} {'':>8}")

    for wait in (1, 2, 4, 8):
        sp = spike_entry(tr, bars["m15"], wait_bars=wait)
        quote = sp["gefuellt"].mean() if len(sp) else 0.0
        ok = sp[sp["gefuellt"]].copy()
        if ok.empty:
            continue
        ok = ok.assign(rib=rib.reindex(_utc_naive(ok["entry_time"]), method="ffill").to_numpy())
        varianten[f"Spike (warte {wait})"] = ok
        varianten[f"Spike {wait} + ribbon"] = ok[((ok["direction"] == 1) & (ok["rib"] > 0)) |
                                                 ((ok["direction"] == -1) & (ok["rib"] < 0))]
        mae = ok["mae_r"].dropna()
        print(f"  {'Spike, warte ' + str(wait) + ' Bars':>28} {len(sp):>8} {int(sp['gefuellt'].sum()):>9} "
              f"{quote:>6.1%} {mae.median():>8.2f} {mae.quantile(0.90):>8.2f}")

    # Frueher Breakeven auf der besten Spike-Variante
    for be in (0.25, 0.5):
        sp = spike_entry(tr, bars["m15"], wait_bars=2, be_trigger=be)
        ok = sp[sp["gefuellt"]].copy()
        if ok.empty:
            continue
        ok = ok.assign(rib=rib.reindex(_utc_naive(ok["entry_time"]), method="ffill").to_numpy())
        varianten[f"Spike2+ribbon+BE{be:g}"] = ok[((ok["direction"] == 1) & (ok["rib"] > 0)) |
                                                  ((ok["direction"] == -1) & (ok["rib"] < 0))]

    print()
    result["flaeche"] = surface(varianten, "ctnl_reversal: Einstieg am Spike")
    print(f"\n  Nur 2024-2026:")
    print(f"    {'Variante':>28} {'n':>5} {'ØR':>8} {'ΣR':>8} {'PF':>6}")
    result["jung"] = {}
    for name, d in varianten.items():
        j = stats(d[_utc_naive(d["entry_time"]) >= JUNG]["r"])
        result["jung"][name] = j
        print(f"    {name:>28} {j['trades']:>5} {j['avg_r']:>+8.3f} {j['summe_r']:>+8.1f} {j['profit_factor']:>6.2f}")

    result["walkforward"] = anchored_walk_forward(varianten, "heute: Markt Folgebar",
                                                  "ctnl_reversal: Einstieg")

    print(f"\n  Monte Carlo (0,15 %/Trade):")
    print(f"    {'Variante':>28} {'MedDD':>9} {'P(>6%)':>8} {'Return':>9} {'Sharpe':>8}")
    result["monte_carlo"] = {}
    for name, d in varianten.items():
        daily = (d.set_index(_utc_naive(d["entry_time"]))["r"] * 0.0015).resample("D").sum()
        daily = daily[daily.index.dayofweek < 5]
        if len(daily) < 250:
            continue
        m = run_monte_carlo(daily, initial_equity=100_000.0, block_size=20, n_sims=2000, seed=42)
        s = m["summary"] if isinstance(m, dict) and "summary" in m else m
        dd = s["max_drawdown_pct"]
        result["monte_carlo"][name] = {"median_maxdd_pct": float(np.median(dd)),
                                       "P_maxdd_ueber_6pct": float((np.abs(dd) > 6).mean()),
                                       "median_return_pct": float(np.median(s["total_return_pct"])),
                                       "median_sharpe": float(np.median(s["sharpe"]))}
        r_ = result["monte_carlo"][name]
        print(f"    {name:>28} {r_['median_maxdd_pct']:>8.2f}% {r_['P_maxdd_ueber_6pct']:>7.1%} "
              f"{r_['median_return_pct']:>8.1f}% {r_['median_sharpe']:>8.2f}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"\nGeschrieben: {args.out}")


if __name__ == "__main__":
    main()
