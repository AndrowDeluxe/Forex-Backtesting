"""ORB NASDAQ live: mit gegen ohne Storno am geplanten SL (Nutzerfrage 2026-10-16).

Beide Varianten im selben M1-Simulator (research_orb_exit_grid_m1.sim, Kosten wie
IS-only-ORB), Live-Config sonst gleich: long + short, OCO, kein Ribbon, ohne
Mittwoch, Stop 0,6 x M15-ATR, kein Ziel, Exit 16:00.
  "sl"   = Storno einer Seite, deren geplanter SL vor dem Fill beruehrt wird (live seit 04.10.)
  "none" = keine Stornierung (vor 04.10.)
Beschreibend, keine Auswahl. Die Wahl vom 04.10. fiel mit Blick auf Daten bis 09/2026;
der Tresor ist fuer beide Varianten vorbelastet.

  python scripts/research_orb_nasdaq_storno_vergleich.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).resolve().parent))

from ny_open_orb.data import fetch_m1, fetch_m15  # noqa: E402
from ny_open_orb.engine import build_frame  # noqa: E402
from research_orb_cancel_at_sl_and_hold import ENTRY_SLIPPAGE_BPS, EXIT_SLIPPAGE_BPS, SPREAD_BPS, find_live_entries  # noqa: E402
from research_orb_exit_grid_m1 import prepare, sim  # noqa: E402

OUT = ROOT / "ny_open_orb" / "results"
PERIODS = [("IS 2016-22", "2016-07-28", "2023-01-01"), ("OOS 2023-09/25", "2023-01-01", "2025-10-01"),
           ("Tresor 10/25-09/26", "2025-10-01", "2026-10-01"), ("gesamt", "2016-07-28", "2026-10-01")]


def stats(r: pd.Series, c: pd.Series) -> dict:
    loss = -r[r < 0].sum()
    eq = r.cumsum().to_numpy()
    dd = (eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    yrs = max(0.5, (r.index.max() - r.index.min()).days / 365.25)
    return {"n": len(r), "je_jahr": len(r) / yrs, "pf": r[r > 0].sum() / loss, "avg": r.mean(), "sum": r.sum(),
            "t": r.mean() / r.std() * np.sqrt(len(r)), "win": (r > 0).mean(), "maxdd": dd,
            "sum_je_dd": r.sum() / -dd if dd < 0 else np.nan, "avg_kosten_x2": (r - c).mean()}


def main() -> int:
    m15, m1 = fetch_m15("NASDAQ", "2016-07-28", "2026-09-30"), fetch_m1("NASDAQ", "2016-07-28", "2026-09-30")
    fr = build_frame(m15, m1, range_bars=1)
    ses = pd.DatetimeIndex(fr.session.dropna().unique())
    allowed = {s: ([] if s.day_name() == "Wednesday" else [1, -1]) for s in ses}
    bps = (SPREAD_BPS["NASDAQ"] + ENTRY_SLIPPAGE_BPS + EXIT_SLIPPAGE_BPS) / 10_000
    rows, yearly, series = [], {}, {}
    for rule in ("sl", "none"):
        prep = prepare(fr, find_live_entries(fr, allowed, 0.6, rule))
        res = sim(prep, "NASDAQ", 0.6, None, None)
        by_t = {t["t"]: t for t in prep}
        idx = pd.DatetimeIndex(res.entry_time).tz_localize(None)
        r = pd.Series(res.r.to_numpy(), index=idx)
        c = pd.Series([by_t[t]["level"] * bps / (0.6 * by_t[t]["atr"]) for t in res.entry_time], index=idx)
        series[rule] = r
        for per, a, b in PERIODS:
            m = (r.index >= a) & (r.index < b)
            rows.append({"variante": "mit Storno" if rule == "sl" else "ohne Storno", "periode": per, **stats(r[m], c[m])})
        yearly["mit Storno" if rule == "sl" else "ohne Storno"] = r.groupby(r.index.year).sum()
    # Was faellt durch das Storno weg? Tage, die nur "ohne" einen Trade haben
    only = series["none"][~series["none"].index.normalize().isin(series["sl"].index.normalize())]
    extra = pd.DataFrame([{"periode": per, "n": int(((only.index >= a) & (only.index < b)).sum()),
                           "sum": only[(only.index >= a) & (only.index < b)].sum(),
                           "avg": only[(only.index >= a) & (only.index < b)].mean()} for per, a, b in PERIODS])
    tab, yr = pd.DataFrame(rows), pd.DataFrame(yearly)
    tab.to_csv(OUT / "nasdaq_storno_vergleich.csv", index=False)
    yr.to_csv(OUT / "nasdaq_storno_vergleich_jahre.csv")
    extra.to_csv(OUT / "nasdaq_storno_weggefallene_tage.csv", index=False)
    pd.set_option("display.width", 200)
    print(tab.round(3).to_string(index=False))
    print("\nJe Kalenderjahr Summe R:\n" + yr.round(1).to_string())
    print("\nNur ohne Storno gehandelte Tage (fallen mit Storno weg):\n" + extra.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
