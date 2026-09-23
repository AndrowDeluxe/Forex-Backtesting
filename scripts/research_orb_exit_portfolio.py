"""ORB: Portfolio-Entscheidung zwischen Ist-Zustand und gemischten Varianten.

Die Einzelinstrument-Tabellen (research_orb_exit_candidates.py) zeigen, dass
NICHT dieselbe Variante ueberall gewinnt: US30 braucht ein Ziel (ohne Ziel
kippt es out-of-sample auf -0,101R), NASDAQ ist ohne Ziel am besten. Deshalb
hier die gemischten Varianten -- und als eigentliche Entscheidungsgroesse
"Summe R bei GLEICHEM Drawdown": wenn eine Variante mehr Ertrag UND mehr
Drawdown bringt, kann man das Risiko je Trade so weit senken, dass der
Drawdown dem heutigen entspricht. Erst dann sind die Varianten fair
vergleichbar -- alle vier Konten haben harte Drawdown-Regeln.
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

START, END, IS_END = "2019-01-01", "2026-09-18", "2022-12-31"
SPREAD_BPS = {"SP500": 0.84, "US30": 0.48, "NASDAQ": 0.54}
RNG = np.random.default_rng(20260921)


def cfg(stop, target, partial, be, fraction=0.5):
    return dict(stop_atr_mult=stop, target_mode="r_multiple" if target is not None else None,
                target_r_mult=target, partial_exit_r=partial,
                partial_exit_fraction=fraction if partial is not None else 0.0,
                move_stop_to_be_after_partial=be)


VARIANTS = {
    # So laeuft es heute auf allen vier Konten.
    "IST (live)": {"SP500": cfg(0.6, 4.0, 2.0, True), "US30": cfg(0.6, 4.0, 2.0, True),
                   "NASDAQ": cfg(0.6, None, 1.5, True)},
    # Kleinster Eingriff: nur der Break-Even faellt weg.
    "A: nur BE weg": {"SP500": cfg(0.6, 4.0, 2.0, False), "US30": cfg(0.6, 4.0, 2.0, False),
                      "NASDAQ": cfg(0.6, None, 1.5, False)},
    # Teilausstieg bleibt, aber spaet (3R) -- und Ziele weiter.
    "B: Teil 3R spaet, TP 6R, kein BE": {"SP500": cfg(0.6, 6.0, 3.0, False), "US30": cfg(0.6, 6.0, 3.0, False),
                                         "NASDAQ": cfg(0.6, None, 3.0, False)},
    # Je Instrument das risikobereinigt Beste aus dem Gitter.
    "C: gemischt (SP500 ohne Teil)": {"SP500": cfg(0.6, 6.0, None, False), "US30": cfg(0.6, 6.0, 3.0, False),
                                      "NASDAQ": cfg(0.6, None, 3.0, False)},
    # Wie C, aber NASDAQ ganz ohne Teilausstieg (hoechstes Ø R, hoechster DD).
    "D: gemischt, NASDAQ ohne Teil": {"SP500": cfg(0.6, 6.0, None, False), "US30": cfg(0.6, 6.0, 3.0, False),
                                      "NASDAQ": cfg(0.6, None, None, False)},
    # Maximalvariante: ueberall ohne Teilausstieg/BE, Ziel nur wo noetig.
    "E: ueberall ohne Teilausstieg": {"SP500": cfg(0.6, 6.0, None, False), "US30": cfg(0.6, 6.0, None, False),
                                      "NASDAQ": cfg(0.6, None, None, False)},
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


def main() -> int:
    data = {i: load(i) for i in ("SP500", "US30", "NASDAQ")}
    rows = []
    for name, per_inst in VARIANTS.items():
        frames = []
        for inst, c in per_inst.items():
            frame, entries = data[inst]
            frames.append(simulate(frame, entries, spread_bps=SPREAD_BPS[inst], entry_slippage_bps=0.45,
                                   slippage_bps=0.30, entry_fill_mode="level", **c).assign(instrument=inst))
        allt = pd.concat(frames).sort_values("entry_time")
        r = allt["r_multiple"].to_numpy()
        et = pd.to_datetime(allt["entry_time"])
        eq = np.cumsum(r)
        dd = float((eq - np.maximum.accumulate(eq)).min())
        is_mask = (et <= pd.Timestamp(IS_END, tz=et.dt.tz)).to_numpy()
        draws = RNG.choice(r, size=(2000, len(r)), replace=True).mean(axis=1)
        per_year = pd.Series(r).groupby(et.dt.year.to_numpy()).sum()
        rows.append({"Variante": name, "n": len(r), "avg_r": r.mean(), "sum_r": r.sum(), "maxdd": dd,
                     "is": r[is_mask].mean(), "oos": r[~is_mask].mean(),
                     "lo": np.percentile(draws, 5), "p_neg": (draws < 0).mean(),
                     "years_pos": int((per_year > 0).sum()), "years": len(per_year)})

    df = pd.DataFrame(rows)
    base_dd = abs(df.loc[df.Variante == "IST (live)", "maxdd"].iloc[0])
    # Risiko je Trade so skalieren, dass der Drawdown dem heutigen entspricht.
    df["skalierung"] = base_dd / df["maxdd"].abs()
    df["sum_r_gl_dd"] = df["sum_r"] * df["skalierung"]
    base_sum = df.loc[df.Variante == "IST (live)", "sum_r_gl_dd"].iloc[0]
    df["vs_ist"] = df["sum_r_gl_dd"] / base_sum - 1

    print(f"\n{'='*118}\nPORTFOLIO (alle 3 Beine, 2019-2026, Stop-Order-Entry, gemessene Kosten)")
    print(f"{'Variante':<36} {'Ø R':>7} {'5%':>7} {'Summe':>7} {'MaxDD':>7} {'R/DD':>6} "
          f"{'IS':>7} {'OOS':>7} {'Jahre+':>7} {'Risiko-Skal.':>12} {'Summe@gl.DD':>12} {'vs IST':>8}")
    for _, r in df.iterrows():
        print(f"{r.Variante:<36} {r.avg_r:>+7.3f} {r.lo:>+7.3f} {r.sum_r:>+7.0f} {r.maxdd:>7.1f} "
              f"{abs(r.sum_r/r.maxdd):>6.1f} {r['is']:>+7.3f} {r.oos:>+7.3f} {r.years_pos:>4}/{r.years} "
              f"{r.skalierung:>11.0%} {r.sum_r_gl_dd:>+12.0f} {r.vs_ist:>+8.0%}")

    print("\nLesehilfe: 'Summe@gl.DD' = Ergebnis, wenn das Risiko je Trade so gesenkt wird,")
    print("dass der maximale Rueckgang dem heutigen entspricht. Das ist der faire Vergleich.")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
