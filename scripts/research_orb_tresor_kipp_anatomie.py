"""Anatomie des Tresor-Kipps der IS-only-ORB (7 Punkte) + Exit-Varianten.

Nutzerfrage 2026-10-07: "Was genau war das Problem beim kippenden Tresor?
Winrate, zu kurze Haltezeit, zu schnelle Verluste oder kippt der Edge
vollstaendig? Koennte man es mit BE-Setzung, anderen TPs oder Teilausstiegen
aendern?"

DIAGNOSE auf bereits geoeffnetem Tresor -- keine Auswahl. Eine Exit-Variante
zaehlt nur als Hinweis, wenn sie in IS, OOS UND Tresor hilft; dann waere sie
vorab zu registrieren und forward zu pruefen.

Konfiguration: eingefrorene IS-only-7p-Gewinner (is_only_7p_selection.json).
Perioden: IS 2016-07..2022-12 | OOS 2023-01..2025-09 | Tresor 2025-10..2026-09.
Simulator: Pfad ab der Bar nach der Fuellung bis 16:00 (wie sim()), Kosten
wie sim(); Stop vor Ziel in derselben Minute (konservativ).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).resolve().parent))

from research_orb_cancel_at_sl_and_hold import ENTRY_SLIPPAGE_BPS, EXIT_SLIPPAGE_BPS, SPREAD_BPS, find_live_entries  # noqa: E402
from research_orb_exit_grid_m1 import prepare, sim  # noqa: E402
from research_orb_is_only_reopt import allowed_for, load  # noqa: E402

RES = ROOT / "ny_open_orb" / "results"
PERIODS = [("IS 2016-22", "2016-07-28", "2023-01-01"), ("OOS 2023-09/25", "2023-01-01", "2025-10-01"),
           ("Tresor 10/25-09/26", "2025-10-01", "2026-10-01")]
EXITS = {
    "Basis (8R / 16:00)": dict(tp=8.0),
    "TP 2R": dict(tp=2.0),
    "TP 3R": dict(tp=3.0),
    "TP 4R": dict(tp=4.0),
    "BE ab +1R": dict(tp=8.0, be=1.0),
    "BE ab +2R": dict(tp=8.0, be=2.0),
    "50 % bei 2R + BE": dict(tp=8.0, part=2.0, be_after_part=True),
    "50 % bei 1R + BE": dict(tp=8.0, part=1.0, be_after_part=True),
    "Zeitstopp 60 Min.": dict(tp=8.0, tmax=60),
    "Zeitstopp 120 Min.": dict(tp=8.0, tmax=120),
}


def run_trade(tr, inst, stop_m, tp=None, be=None, part=None, be_after_part=False, tmax=None):
    half = SPREAD_BPS[inst] / 10_000 / 2
    es, xs = ENTRY_SLIPPAGE_BPS / 10_000, EXIT_SLIPPAGE_BPS / 10_000
    d, lvl = tr["d"], tr["level"]
    entry = lvl * (1 + (half + es) * d)
    stop = lvl * (1 + half * d) - d * stop_m * tr["atr"]
    risk = abs(entry - stop)
    hi, lo, cl = tr["hi"], tr["lo"], tr["cl"]
    n = len(cl) if tmax is None else min(len(cl), tmax)
    sl, done_part, booked, rem = stop, False, 0.0, 1.0
    mfe = 0.0
    for k in range(n):
        fav = (hi[k] - entry) / risk if d == 1 else (entry - lo[k]) / risk
        adv_hit = (lo[k] <= sl) if d == 1 else (hi[k] >= sl)
        if adv_hit:
            xp = sl * (1 - (half + xs) * d)
            return booked + rem * d * (xp - entry) / risk, "stop" if sl == stop else "be", k, max(mfe, 0)
        mfe = max(mfe, fav)
        if part is not None and not done_part and fav >= part:
            pp = entry + d * part * risk
            booked += 0.5 * d * (pp * (1 - (half + xs) * d) - entry) / risk
            rem, done_part = 0.5, True
            if be_after_part:
                sl = entry
        if tp is not None and fav >= tp:
            tpp = entry + d * tp * risk
            return booked + rem * d * (tpp * (1 - (half + xs) * d) - entry) / risk, "ziel", k, mfe
        if be is not None and fav >= be and sl == stop:
            sl = entry
    xp = cl[n - 1] * (1 - (half + xs) * d)
    return booked + rem * d * (xp - entry) / risk, "zeit" if tmax and n < len(cl) else "16:00", n - 1, mfe


def main() -> int:
    sel = json.loads((RES / "is_only_7p_selection.json").read_text(encoding="utf-8"))["winners"]
    diag, ex_rows = [], []
    for inst in ("SP500", "NASDAQ"):
        cfg = sel[inst]
        frames, sessions, bias = load(inst, "2026-09-30")
        frame = frames[cfg["range_bars"]]
        prep = prepare(frame, find_live_entries(frame, allowed_for(sessions, bias, cfg["dirs"], cfg["ribbon"]),
                                                cfg["stop"], cfg["rule"]))
        # Paritaet Basis gegen sim()
        ref = sim(prep, inst, cfg["stop"], cfg["target"], cfg["partial"])
        mine = [run_trade(t, inst, cfg["stop"], tp=cfg["target"])[0] for t in prep if t["hi"].size]
        print(f"{inst}: Paritaet {len(ref)} vs {len(mine)}, max |dR| = {np.max(np.abs(ref['r'].to_numpy() - np.array(mine))):.2e}", flush=True)
        times = pd.DatetimeIndex([t["t"] for t in prep if t["hi"].size]).tz_localize(None)
        trades = [t for t in prep if t["hi"].size]
        for ex_name, kw in EXITS.items():
            out = [run_trade(t, inst, cfg["stop"], **kw) for t in trades]
            df = pd.DataFrame(out, columns=["r", "grund", "bars", "mfe"], index=times)
            df["dir"] = [t["d"] for t in trades]
            for per, a, b in PERIODS:
                x = df[(df.index >= a) & (df.index < b)]
                loss = -x.r[x.r < 0].sum()
                ex_rows.append({"inst": inst, "exit": ex_name, "periode": per, "n": len(x), "avg_r": x.r.mean(),
                                "pf": x.r[x.r > 0].sum() / loss if loss > 0 else np.inf, "sum_r": x.r.sum()})
                if ex_name == "Basis (8R / 16:00)":
                    w, l = x.r[x.r > 0], x.r[x.r <= 0]
                    st = x[x.grund == "stop"]
                    diag.append({
                        "inst": inst, "periode": per, "trades": len(x), "trefferquote": (x.r > 0).mean(),
                        "ø_gewinn_R": w.mean(), "ø_verlust_R": l.mean(), "payoff": w.mean() / -l.mean() if len(l) else np.nan,
                        "anteil_stop": (x.grund == "stop").mean(), "anteil_ziel_8R": (x.grund == "ziel").mean(),
                        "anteil_16uhr": (x.grund == "16:00").mean(),
                        "median_min_bis_stop": st.bars.median() + 1 if len(st) else np.nan,
                        "stop_in_15min": (st.bars < 15).mean() if len(st) else np.nan,
                        "mfe_median": x.mfe.median(), "mfe>=1R": (x.mfe >= 1).mean(), "mfe>=2R": (x.mfe >= 2).mean(),
                        "mfe>=4R": (x.mfe >= 4).mean(),
                        "erst+1R_dann_stop": ((x.mfe >= 1) & (x.grund == "stop")).mean(),
                        "long_avg_r": x[x.dir == 1].r.mean(), "short_avg_r": x[x.dir == -1].r.mean(),
                        "n_long": int((x.dir == 1).sum()), "n_short": int((x.dir == -1).sum())})
        print(f"{inst} fertig", flush=True)
    D = pd.DataFrame(diag)
    E = pd.DataFrame(ex_rows)
    D.to_csv(RES / "tresor_kipp_anatomie.csv", index=False)
    E.to_csv(RES / "tresor_kipp_exits.csv", index=False)
    pd.set_option("display.width", 260)
    print(D.set_index(["inst", "periode"]).T.round(3).to_string())
    for inst in ("SP500", "NASDAQ"):
        print(f"\n{inst} – Ø R je Exit-Variante")
        print(E[E.inst == inst].pivot(index="exit", columns="periode", values="avg_r")[[p[0] for p in PERIODS]].round(3).to_string())
        print(E[E.inst == inst].pivot(index="exit", columns="periode", values="pf")[[p[0] for p in PERIODS]].round(2).to_string())
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
