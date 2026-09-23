"""ORB: die Kandidaten aus dem Gitter (research_orb_exit_grid.py) ehrlich
gegen den Ist-Zustand stellen -- mit Bootstrap, Drawdown und PORTFOLIO-Sicht.

WARUM NICHT EINFACH DAS GITTER-MAXIMUM NEHMEN: bei 396 Kombinationen je
Instrument ist die beste Zahl zwangslaeufig auch die mit dem meisten Glueck.
Der Repo-Standard (knowledge/areas/realkosten-und-ausfuehrungs-probe.md)
verlangt: Gitter-Raender verwerfen, benachbarte Zellen pruefen, Bootstrap
statt Punktschaetzung -- und die Entscheidung am DRAWDOWN messen, nicht nur am
Mittelwert, weil alle vier Konten harte Drawdown-Regeln haben.

Ø R je Trade ist hier die richtige Vergleichsgroesse: das Dollar-Risiko je
Trade ist fix (Stop-Order, Sizing gegen das Level), also ist mehr Ø R direkt
mehr Geld -- aber ein engerer Stop bedeutet eine groessere Position, und die
gemessene Einstiegs-Slippage frisst dann einen groesseren Anteil von R. Genau
das modelliert die Engine mit, deshalb sind die Zahlen vergleichbar.
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
IS_END = "2022-12-31"
SPREAD_BPS = {"SP500": 0.84, "US30": 0.48, "NASDAQ": 0.54}
ENTRY_SLIPPAGE_BPS = 0.45
EXIT_SLIPPAGE_BPS = 0.30
N_BOOT = 2000
RNG = np.random.default_rng(20260921)

def cfg(stop, target, partial, be, fraction=0.5):
    return dict(stop_atr_mult=stop,
                target_mode="r_multiple" if target is not None else None,
                target_r_mult=target, partial_exit_r=partial,
                partial_exit_fraction=fraction if partial is not None else 0.0,
                move_stop_to_be_after_partial=be)

# Kandidaten. Gleiche Namen ueber alle drei Instrumente, damit die
# Portfolio-Auswertung unten dieselbe Variante zusammenfassen kann. "IST" ist
# je Instrument der heute LIVE gefahrene Stand (NASDAQ hat kein Ziel und einen
# frueheren Teilausstieg, siehe config ORB_EXIT_CFG_BY_INSTRUMENT).
_COMMON = {
    "ohne BE":                    lambda t, p: cfg(0.6, t, p, False),
    "Teil spaeter 3.0, ohne BE":  lambda t, p: cfg(0.6, t, 3.0, False),
    "TP 6R, Teil 3.0, ohne BE":   lambda t, p: cfg(0.6, 6.0, 3.0, False),
    "TP 6R, kein Teilausstieg":   lambda t, p: cfg(0.6, 6.0, None, False),
    "TP 5R, Teil 2.5, ohne BE":   lambda t, p: cfg(0.6, 5.0, 2.5, False),
    "kein TP, kein Teilausstieg": lambda t, p: cfg(0.6, None, None, False),
}
_IST = {"SP500": (4.0, 2.0), "US30": (4.0, 2.0), "NASDAQ": (None, 1.5)}
CANDIDATES = {
    inst: {"IST (live)": cfg(0.6, t, p, True), **{name: fn(t, p) for name, fn in _COMMON.items()}}
    for inst, (t, p) in _IST.items()
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


def bootstrap(r: np.ndarray) -> tuple[float, float, float]:
    """Ø R mit 5-%/95-%-Band und P(Ø R < 0), gezogen mit Zuruecklegen."""
    draws = RNG.choice(r, size=(N_BOOT, len(r)), replace=True).mean(axis=1)
    return float(np.percentile(draws, 5)), float(np.percentile(draws, 95)), float((draws < 0).mean())


def describe(trades: pd.DataFrame) -> dict:
    r = trades["r_multiple"].to_numpy()
    et = pd.to_datetime(trades["entry_time"])
    is_mask = (et <= pd.Timestamp(IS_END, tz=et.dt.tz)).to_numpy()
    eq = np.cumsum(r)
    lo, hi, p_neg = bootstrap(r)
    per_year = pd.Series(r).groupby(et.dt.year.to_numpy()).sum()
    wins, losses = r[r > 0].sum(), -r[r < 0].sum()
    return {"n": len(r), "avg_r": r.mean(), "lo": lo, "hi": hi, "p_neg": p_neg,
            "pf": wins / losses if losses > 0 else np.inf, "win": (r > 0).mean(),
            "sum_r": r.sum(), "maxdd_r": float((eq - np.maximum.accumulate(eq)).min()),
            "is_avg": r[is_mask].mean(), "oos_avg": r[~is_mask].mean(),
            "years_pos": int((per_year > 0).sum()), "years": int(len(per_year))}


def main() -> int:
    per_instrument_trades = {}
    for instrument, cands in CANDIDATES.items():
        frame, entries = load(instrument)
        print(f"\n{'='*112}\n{instrument}")
        print(f"{'Variante':<38} {'n':>4} {'Ø R':>7} {'5-95%':>16} {'P(<0)':>6} {'PF':>5} "
              f"{'Summe':>7} {'MaxDD':>7} {'IS':>7} {'OOS':>7} {'Jahre+':>7}")
        for name, c in cands.items():
            trades = simulate(frame, entries, spread_bps=SPREAD_BPS[instrument],
                              entry_slippage_bps=ENTRY_SLIPPAGE_BPS, slippage_bps=EXIT_SLIPPAGE_BPS,
                              entry_fill_mode="level", **c)
            d = describe(trades)
            per_instrument_trades.setdefault(name, []).append(trades.assign(instrument=instrument))
            print(f"{name:<38} {d['n']:>4} {d['avg_r']:>+7.3f} "
                  f"[{d['lo']:+.3f},{d['hi']:+.3f}] {d['p_neg']:>6.1%} {d['pf']:>5.2f} "
                  f"{d['sum_r']:>+7.0f} {d['maxdd_r']:>7.1f} {d['is_avg']:>+7.3f} {d['oos_avg']:>+7.3f} "
                  f"{d['years_pos']:>4}/{d['years']}")

    # ---- Portfolio: alle drei Beine chronologisch, gleiches Risiko je Trade --
    # Das ist die Zahl, die fuer die Challenge-Regeln zaehlt: der Drawdown des
    # GESAMTEN Beins, nicht der eines Instruments.
    print(f"\n{'='*112}\nPORTFOLIO (alle 3 Instrumente, gleiches Risiko je Trade)")
    print(f"{'Variante':<38} {'n':>5} {'Ø R':>7} {'P(<0)':>6} {'PF':>5} {'Summe':>7} {'MaxDD':>8} {'OOS Ø R':>8}")
    for name, frames in per_instrument_trades.items():
        if len(frames) != 3:
            continue
        allt = pd.concat(frames).sort_values("entry_time")
        d = describe(allt)
        print(f"{name:<38} {d['n']:>5} {d['avg_r']:>+7.3f} {d['p_neg']:>6.1%} {d['pf']:>5.2f} "
              f"{d['sum_r']:>+7.0f} {d['maxdd_r']:>8.1f} {d['oos_avg']:>+8.3f}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
