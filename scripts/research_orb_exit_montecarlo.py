"""ORB: Phase-6-Robustheit fuer die Exit-Entscheidung (IST vs. Variante D).

WARUM NOETIG: der Vergleich "Summe R bei gleichem Drawdown"
(research_orb_exit_portfolio.py) skaliert auf den EINEN historisch
realisierten Maximalrueckgang. Der ist eine Zufallsziehung -- eine andere
Reihenfolge derselben Trades haette einen anderen Wert ergeben. Der
Repo-Standard (CLAUDE.md: Phase 6 VOR Portfolio-/Risikoarbeit) verlangt hier
eine Verteilung statt einer Punktschaetzung.

METHODE: Block-Bootstrap ueber KALENDERMONATE statt ueber einzelne Trades.
Einzelne Trades zu ziehen wuerde die Cluster zerstoeren (mehrere Beine
verlieren am selben Tag, Verlustserien in ruhigen Regimen) und den Drawdown
systematisch zu klein schaetzen -- genau der Fehler, der eine Risikofreigabe
wertlos macht.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import challenge_portfolio.paper_bot as pb  # noqa: E402
from ny_open_orb import filters, regime  # noqa: E402
from ny_open_orb.data import fetch_m5, fetch_m15  # noqa: E402
from ny_open_orb.engine import build_frame, find_entries, simulate  # noqa: E402

START, END = "2019-01-01", "2026-09-18"
SPREAD_BPS = {"SP500": 0.84, "US30": 0.48, "NASDAQ": 0.54}
N_PATHS = 3000
RNG = np.random.default_rng(20260921)


def cfg(stop, target, partial, be, fraction=0.5):
    return dict(stop_atr_mult=stop, target_mode="r_multiple" if target is not None else None,
                target_r_mult=target, partial_exit_r=partial,
                partial_exit_fraction=fraction if partial is not None else 0.0,
                move_stop_to_be_after_partial=be)


VARIANTS = {
    "IST (live)": {"SP500": cfg(0.6, 4.0, 2.0, True), "US30": cfg(0.6, 4.0, 2.0, True),
                   "NASDAQ": cfg(0.6, None, 1.5, True)},
    "D: gemischt, NASDAQ ohne Teil": {"SP500": cfg(0.6, 6.0, None, False), "US30": cfg(0.6, 6.0, 3.0, False),
                                      "NASDAQ": cfg(0.6, None, None, False)},
    "C: gemischt (NASDAQ Teil 3R)": {"SP500": cfg(0.6, 6.0, None, False), "US30": cfg(0.6, 6.0, 3.0, False),
                                     "NASDAQ": cfg(0.6, None, 3.0, False)},
}


def load(instrument):
    m15 = pb._retry(lambda: fetch_m15(instrument, START, END), attempts=3, delay_seconds=5, timeout_seconds=300)
    m5 = pb._retry(lambda: fetch_m5(instrument, START, END), attempts=3, delay_seconds=5, timeout_seconds=300)
    frame = build_frame(m15, m5, range_bars=1)
    all_entries = find_entries(frame, "stop_breakout")
    if instrument == "NASDAQ":
        entries = filters.filter_by_weekday(all_entries, exclude=["Wednesday"])
    else:
        long_entries = filters.filter_by_direction(all_entries, 1)
        bias = regime.ema_trend_bias(m15, frame["session"].unique())
        entries = filters.filter_by_category(long_entries, filters.values_at(long_entries, bias), (0.0,))
    return frame, entries


def month_blocks(trades: pd.DataFrame) -> list[np.ndarray]:
    et = pd.to_datetime(trades["entry_time"])
    key = et.dt.year * 100 + et.dt.month
    return [g["r_multiple"].to_numpy() for _, g in trades.groupby(key.to_numpy())]


def mc(blocks: list[np.ndarray], n_months: int) -> tuple[np.ndarray, np.ndarray]:
    total, maxdd = np.empty(N_PATHS), np.empty(N_PATHS)
    idx = RNG.integers(0, len(blocks), size=(N_PATHS, n_months))
    for p in range(N_PATHS):
        r = np.concatenate([blocks[i] for i in idx[p]])
        eq = np.cumsum(r)
        total[p] = eq[-1]
        maxdd[p] = (eq - np.maximum.accumulate(eq)).min()
    return total, maxdd


def main() -> int:
    data = {i: load(i) for i in ("SP500", "US30", "NASDAQ")}
    results = {}
    for name, per_inst in VARIANTS.items():
        frames = [simulate(data[i][0], data[i][1], spread_bps=SPREAD_BPS[i], entry_slippage_bps=0.45,
                           slippage_bps=0.30, entry_fill_mode="level", **c).assign(instrument=i)
                  for i, c in per_inst.items()]
        allt = pd.concat(frames).sort_values("entry_time")
        blocks = month_blocks(allt)
        total, maxdd = mc(blocks, len(blocks))
        results[name] = {"total": total, "maxdd": maxdd, "hist_sum": allt["r_multiple"].sum(),
                         "n": len(allt), "months": len(blocks)}

    print(f"\n{'='*104}\nMONTE CARLO: {N_PATHS} Pfade, Block-Bootstrap ueber Kalendermonate")
    print(f"{'Variante':<32} {'Summe R Median':>15} {'5%':>8} {'MaxDD Median':>13} {'MaxDD 95%':>10} "
          f"{'P(Summe<0)':>11} {'R/DD(95%)':>10}")
    for name, r in results.items():
        dd95 = np.percentile(r["maxdd"], 5)   # 5. Perzentil = die schlimmen 5 % der Pfade
        print(f"{name:<32} {np.median(r['total']):>+15.0f} {np.percentile(r['total'], 5):>+8.0f} "
              f"{np.median(r['maxdd']):>13.1f} {dd95:>10.1f} {(r['total'] < 0).mean():>10.1%} "
              f"{abs(np.median(r['total'])/dd95):>10.2f}")

    base = results["IST (live)"]
    base_dd95 = abs(np.percentile(base["maxdd"], 5))
    base_med = np.median(base["total"])
    print(f"\nFairer Vergleich -- Risiko je Trade so skaliert, dass der 95-%-Drawdown dem heutigen "
          f"({base_dd95:.1f}R) entspricht:")
    for name, r in results.items():
        dd95 = abs(np.percentile(r["maxdd"], 5))
        scale = base_dd95 / dd95
        med = np.median(r["total"]) * scale
        print(f"  {name:<32} Risiko {scale:>5.0%} -> Summe R {med:>+7.0f} "
              f"({med/base_med - 1:+.0%} gegenueber heute)")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
