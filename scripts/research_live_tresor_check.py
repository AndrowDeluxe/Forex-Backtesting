"""Tresor-Check aller Live-Beine (Nutzerauftrag 2026-10-14, "Tresor-Variante von Dennis").

Tresor = letzte 12 Monate (01.10.2025-30.09.2026), Vergleich mit der Zeit
davor. Quelle: Trade-Listen mit Live-Konfiguration und gemessenen Broker-
Kosten aus scripts/research_live_legs.py (Stand 04.10.2026). VORBELASTET:
Die Live-Konfigurationen wurden teils mit Blick auf 2026 gewaehlt
(z. B. CTNL Ribbon/Spike, ORB-Storno) -- das ist kein sauberer Holdout,
sondern ein Gesundheitscheck.

Teil 2 (Ursachen, nur ORB): Live-Konfigurationen (research_orb_is_only_reopt.LIVE)
mit dem Research-Simulator nach Ribbon-Zustand und Vortagesrichtung zerlegt.
Achtung: find_live_entries nimmt nur den ERSTEN Trade je Tag; live (und in
der Broker-Liste) kann NASDAQ nach einem Stop noch die Gegenseite ausloesen
(~200 statt ~90 Trades/Jahr). Teil 2 erklaert also den Mechanismus, nicht
die exakte Live-Zahl.

  python scripts/research_live_tresor_check.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).resolve().parent))

from ny_open_orb import regime  # noqa: E402
from ny_open_orb.data import fetch_m1, fetch_m15  # noqa: E402
from ny_open_orb.engine import build_frame  # noqa: E402
from research_orb_cancel_at_sl_and_hold import find_live_entries  # noqa: E402
from research_orb_exit_grid_m1 import prepare, sim  # noqa: E402
from research_orb_is_only_reopt import LIVE, allowed_for  # noqa: E402
from research_orb_oel_vergleich import session_points  # noqa: E402

PC = ROOT / "portfolio_construction" / "results"
OUT = ROOT / "ny_open_orb" / "results"
T0, T1 = "2025-10-01", "2026-10-01"


def m(r: pd.Series) -> dict:
    if len(r) < 2:
        return {"n": len(r)}
    loss = -r[r < 0].sum()
    eq = r.cumsum().to_numpy()
    return {"n": len(r), "pf": r[r > 0].sum() / loss if loss > 0 else np.inf, "avg": r.mean(), "sum": r.sum(),
            "t": r.mean() / r.std() * np.sqrt(len(r)), "win": (r > 0).mean(),
            "dd": (eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()}


def part1() -> pd.DataFrame:
    rows = []
    for b in ("tickmill", "ttp", "iq"):
        d = pd.read_csv(PC / f"live_trades_{b}_2019_2026.csv", parse_dates=["entry_time", "exit_time"])
        for leg, g in d.groupby("leg"):
            r = g.set_index("entry_time").r.sort_index()
            for per, x in (("vor 10/2025", r[r.index < T0]), ("Tresor", r[(r.index >= T0) & (r.index < T1)])):
                rows.append({"broker": b, "leg": leg, "periode": per, **m(x)})
    return pd.DataFrame(rows)


def part2() -> pd.DataFrame:
    rows = []
    for inst in ("SP500", "US30", "NASDAQ"):
        cfg = LIVE[inst]
        m15, m1 = fetch_m15(inst, "2016-07-28", "2026-09-30"), fetch_m1(inst, "2016-07-28", "2026-09-30")
        fr = build_frame(m15, m1, range_bars=1)
        ses = pd.DatetimeIndex(fr.session.dropna().unique())
        bias = regime.ema_trend_bias(m15, ses)
        pts = session_points(m1, "index")
        prev = (pts.close / pts.open - 1).shift(1)
        prep = prepare(fr, find_live_entries(fr, allowed_for(ses, bias, cfg["dirs"], "kein"), cfg["stop"], cfg["rule"]))
        res = sim(prep, inst, cfg["stop"], cfg["target"], cfg["partial"])
        res["d"] = res.entry_time.map({t["t"]: t["d"] for t in prep})
        s = pd.DatetimeIndex(res.entry_time).normalize()
        res["bias"], res["prev"] = s.map(bias), s.map(prev)
        if cfg["weekday"]:
            res = res[pd.DatetimeIndex(res.entry_time).day_name() != cfg["weekday"]]
        t = pd.DatetimeIndex(res.entry_time).tz_localize(None)
        res["periode"] = np.where(t >= T0, "Tresor", np.where(t >= pd.Timestamp("2023-01-01"), "OOS 23-09/25", "IS 16-22"))
        res["ribbon"] = np.where(res.bias == 0, "neutral", np.where(res.bias == res.d, "mit Trend", "gegen Trend"))
        res["vortag"] = np.where(res.prev * res.d > 0, "gleichlaeufig", "gegenlaeufig")
        res["gehandelt"] = (res.ribbon == "neutral") if cfg["ribbon"] == "neutral" else True
        for dim in ("ribbon", "vortag"):
            sub = res if dim == "ribbon" else res[res.gehandelt]
            for (per, val), g in sub.groupby(["periode", dim]):
                rows.append({"instrument": inst, "dimension": dim, "wert": val, "periode": per, **m(g.r)})
    return pd.DataFrame(rows)


def main() -> int:
    p1 = part1()
    p1.to_csv(OUT / "live_tresor_check_beine.csv", index=False)
    p2 = part2()
    p2.to_csv(OUT / "live_tresor_check_orb_ursachen.csv", index=False)
    pd.set_option("display.width", 200)
    print(p1.round(3).to_string(index=False))
    print(p2.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
