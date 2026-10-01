"""ORB: Phase-6-Monte-Carlo fuer "Pending-Order am geplanten SL stornieren".

Nutzerentscheid 2026-10-01 (B): vor einem Live-Einsatz fuer NASDAQ die
Storno-am-SL-Regel per Monte Carlo pruefen. Grundlage:
scripts/research_orb_cancel_at_sl_and_hold.py, Notiz
knowledge/projects/orb-order-storno-und-haltedauer.md.

AUSFUEHRUNG AUF M1 -- auf M5 beruehrt bei ~70 % der Trades schon die Fuell-Bar
den SL, und simulate() prueft den Stop erst ab der Folgebar. Auf M1 bleiben
~1/3 (NASDAQ) mehrdeutige Fuell-Minuten. Deshalb drei Bewertungen:
  basis  -- wie simulate() (Fuell-Minute ohne Stop-Pruefung, optimistisch)
  mitte  -- mehrdeutige Fuell-Minuten zu 50 % als Stop-out (-1,05 R)
  pessim -- mehrdeutige Fuell-Minuten immer als Stop-out

METHODE wie scripts/research_orb_exit_montecarlo.py: Block-Bootstrap ueber
Kalendermonate (erhaelt Verlustcluster), 3.000 Pfade. Weil die SL-Regel nur
~1/3 der Trades uebrig laesst, ist "Summe R bei gleichem Risiko je Trade" kein
fairer Vergleich -- entscheidend ist Ertrag je Drawdown (skalierungsfrei:
wer weniger, sauberere Trades hat, kann das Risiko je Trade anheben).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import challenge_portfolio.paper_bot as pb  # noqa: E402
from ny_open_orb import regime  # noqa: E402
from ny_open_orb.data import fetch_m1, fetch_m15  # noqa: E402
from ny_open_orb.engine import build_frame  # noqa: E402
from research_orb_cancel_at_sl_and_hold import (  # noqa: E402
    END, EXIT_CFG, START, fill_bar_sl_touch, find_live_entries, run,
)

N_PATHS = 3000
RNG = np.random.default_rng(20261001)
STOP_OUT_R = -1.05
RULES = {"NASDAQ": ("none", "sl"), "SP500": ("opposite", "sl")}


def load_m1(instrument):
    m15 = pb._retry(lambda: fetch_m15(instrument, START, END), attempts=3, delay_seconds=5, timeout_seconds=300)
    m1 = pb._retry(lambda: fetch_m1(instrument, START, END), attempts=3, delay_seconds=5, timeout_seconds=900)
    frame = build_frame(m15, m1, range_bars=1)
    sessions = pd.DatetimeIndex(frame["session"].dropna().unique())
    if instrument == "NASDAQ":
        allowed = {s: ([] if s.day_name() == "Wednesday" else [1, -1]) for s in sessions}
    else:
        bias = regime.ema_trend_bias(m15, sessions)
        allowed = {s: ([1] if (not pd.isna(bias.get(s, np.nan)) and float(bias.get(s)) == 0.0) else [])
                   for s in sessions}
    return frame, allowed


def month_blocks(r: pd.Series) -> list[np.ndarray]:
    return [g.to_numpy() for _, g in r.groupby(r.index.to_period("M"))]


def mc(blocks, n_months):
    idx = RNG.integers(0, len(blocks), size=(N_PATHS, n_months))
    total, maxdd = np.empty(N_PATHS), np.empty(N_PATHS)
    for p in range(N_PATHS):
        r = np.concatenate([blocks[i] for i in idx[p]])
        eq = np.cumsum(r)
        total[p] = eq[-1]
        maxdd[p] = (eq - np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]).min()
    return total, maxdd


def main() -> int:
    out_rows = []
    for instrument, rules in RULES.items():
        frame, allowed = load_m1(instrument)
        stop_atr = EXIT_CFG[instrument]["stop_atr_mult"]
        all_months = pd.period_range(pd.Timestamp(START), pd.Timestamp(END), freq="M")
        print(f"\n{'=' * 100}\n{instrument} [M1], {N_PATHS} Pfade, Block = Kalendermonat")
        for rule in rules:
            entries = find_live_entries(frame, allowed, stop_atr, rule)
            tr = run(frame, entries, instrument)
            hit = fill_bar_sl_touch(frame, entries, stop_atr)
            amb = tr["entry_time"].isin(hit).to_numpy()
            base = tr["r_multiple"].to_numpy()
            variants = {
                "basis": base,
                "mitte": np.where(amb, 0.5 * base + 0.5 * STOP_OUT_R, base),
                "pessim": np.where(amb, STOP_OUT_R, base),
            }
            et = pd.to_datetime(tr["entry_time"]).dt.tz_convert(None)
            for label, r in variants.items():
                s = pd.Series(r, index=et)
                blocks = month_blocks(s)
                # Monate ohne Trade zaehlen mit (leere Bloecke), sonst wird die
                # Stichprobe kuenstlich dichter
                blocks += [np.array([])] * max(0, len(all_months) - len(blocks))
                total, maxdd = mc(blocks, len(all_months))
                ratio = total / np.abs(np.minimum(maxdd, -1e-9))
                row = {
                    "instrument": instrument, "rule": rule, "bewertung": label, "n": len(r),
                    "mehrdeutig": int(amb.sum()), "avg_r": r.mean(),
                    "sum_r_med": np.median(total), "sum_r_p5": np.percentile(total, 5),
                    "p_sum_neg": (total < 0).mean(),
                    "maxdd_med": np.median(maxdd), "maxdd_p95": np.percentile(maxdd, 5),
                    "ret_dd_med": np.median(ratio), "ret_dd_p5": np.percentile(ratio, 5),
                }
                out_rows.append(row)
                print(f"  {rule:<9} {label:<6} n {len(r):>4} (mehrd. {amb.sum():>3}) | Ø R {r.mean():+.3f} | "
                      f"Σ R Median {row['sum_r_med']:+7.1f} (P5 {row['sum_r_p5']:+7.1f}) | P(Σ<0) {row['p_sum_neg']:.1%} | "
                      f"MaxDD Median {row['maxdd_med']:6.1f} / P95 {row['maxdd_p95']:6.1f} | "
                      f"Ertrag/DD Median {row['ret_dd_med']:.2f} (P5 {row['ret_dd_p5']:+.2f})")
    out = Path(__file__).resolve().parents[1] / "ny_open_orb" / "results" / "cancel_at_sl_montecarlo_m1.csv"
    pd.DataFrame(out_rows).to_csv(out, index=False)
    print(f"\nCSV -> {out}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
