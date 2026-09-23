"""CTNL: wo kommen die Entries eigentlich her? (Deskriptiv, 2026-09-23)

Nutzerfrage: "schaue wo die Entries herkommen". Die bisherige Optimierung hat
die MTF-Kaskaden-PARAMETER gesweept (h4_confirm_bars, h1_valid_bars,
require_ema_reject, siehe Befund 9b) -- aber nie, WO die Signale im Tag, in
der Woche und in der Richtung liegen und ob einzelne Eimer nur Ballast sind.

Genau das macht dieses Skript. Es optimiert NICHTS: es teilt die bestehende
Trade-Liste (gesperrte Config, gemessene Kosten, Lag 1, R-Detektor) nach
Merkmalen auf, die zum Einstiegszeitpunkt feststehen, und weist je Eimer
Trades / Ø R / PF aus.

WARUM DAS KEINE OPTIMIERUNG IST, AUCH WENN ES SO AUSSIEHT
Ein Eimer mit schlechtem Ø R ist eine BEOBACHTUNG, keine Handlungsempfehlung.
Wer daraus einen Filter macht, hat auf der Gesamthistorie gefittet -- und
genau das hat der Walk-Forward in Befund 9b bei den Signal-Parametern als
Ueberanpassung entlarvt. Auffaellige Eimer gehoeren deshalb in denselben
Anker-Walk-Forward wie jeder andere Kandidat, bevor sie irgendetwas aendern.
Dieses Skript liefert die Kandidaten, nicht das Urteil.
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

from gold_smc_htf_ltf.live_signal import CONT_KWARGS, REV_KWARGS  # noqa: E402
from research_ctnl_execution_costs import _utc_naive, load_bars  # noqa: E402
from research_ctnl_optimization import MEASURED_BPS, leg_trades, to_live  # noqa: E402

# Gold-Handelssessions in UTC. Grenzen bewusst grob und konventionell gewaehlt
# (nicht aus den Daten abgeleitet) -- eine aus der Performance gezogene
# Sessiongrenze waere bereits ein Fit.
SESSIONS = [
    ("Asien", 0, 7),
    ("London", 7, 12),
    ("London/NY-Overlap", 12, 16),
    ("NY", 16, 21),
    ("Spaet/Rollover", 21, 24),
]


def stats(r: pd.Series) -> dict:
    r = pd.Series(r).dropna()
    if r.empty:
        return {"trades": 0, "avg_r": float("nan"), "summe_r": 0.0,
                "profit_factor": float("nan"), "trefferquote": float("nan")}
    w, l = r[r > 0], r[r <= 0]
    return {"trades": int(len(r)), "avg_r": float(r.mean()), "summe_r": float(r.sum()),
            "trefferquote": float((r > 0).mean()),
            "profit_factor": float(w.sum() / abs(l.sum())) if len(l) and l.sum() != 0 else float("nan")}


def table(groups: list[tuple[str, pd.Series]], titel: str) -> dict:
    print(f"\n  {titel}")
    print(f"    {'Eimer':>20} {'Trades':>7} {'Anteil':>7} {'ØR':>8} {'ΣR':>9} {'PF':>6} {'Treffer':>8}")
    gesamt = sum(len(r) for _, r in groups) or 1
    out = {}
    for name, r in groups:
        s = stats(r)
        out[name] = s
        if s["trades"] == 0:
            print(f"    {name:>20} {0:>7} {'':>7} {'—':>8}")
            continue
        print(f"    {name:>20} {s['trades']:>7} {s['trades']/gesamt:>6.1%} {s['avg_r']:>+8.3f} "
              f"{s['summe_r']:>+9.1f} {s['profit_factor']:>6.2f} {s['trefferquote']:>7.1%}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default="2016-01-01")
    ap.add_argument("--end", default=pd.Timestamp.utcnow().strftime("%Y-%m-%d"))
    ap.add_argument("--out", type=Path,
                    default=REPO_DIR / "knowledge" / "_data" / "ctnl_entry_origin.json")
    args = ap.parse_args()

    print(f"Lade Gold-Bars {args.start} .. {args.end} ...")
    bars = load_bars(args.start, args.end)
    bar_src = {"ctnl_continuation": bars["m5"], "ctnl_reversal": bars["m15"]}
    kwargs = {"ctnl_reversal": REV_KWARGS, "ctnl_continuation": CONT_KWARGS}
    base_tp = {"ctnl_reversal": 5.0, "ctnl_continuation": None}

    result: dict = {"kosten_bps": MEASURED_BPS, "beine": {}}

    for leg in ("ctnl_reversal", "ctnl_continuation"):
        tr = leg_trades(bars, leg, tp_r=base_tp[leg], sig_kwargs=kwargs[leg])
        rep = to_live(tr, bar_src[leg])
        t = _utc_naive(rep["entry_time"])
        rep = rep.assign(stunde=t.dt.hour, wochentag=t.dt.dayofweek, monat=t.dt.month)

        print(f"\n{'='*84}\n{leg}: {len(rep)} handelbare Trades (gesperrte Config, Lag 1, R-Detektor)\n{'='*84}")
        res = {}

        # 1) Richtung -- die Grundfrage: verdient das Bein auf beiden Seiten?
        res["richtung"] = table(
            [("long", rep[rep["direction"] == 1]["r"]),
             ("short", rep[rep["direction"] == -1]["r"])],
            "Nach Richtung")

        # 2) Session
        res["session"] = table(
            [(name, rep[(rep["stunde"] >= a) & (rep["stunde"] < b)]["r"]) for name, a, b in SESSIONS],
            "Nach Session (UTC)")

        # 3) Stunde -- feiner, zeigt ob eine Session an einer einzelnen Stunde haengt
        res["stunde"] = table(
            [(f"{h:02d}:00", rep[rep["stunde"] == h]["r"]) for h in sorted(rep["stunde"].unique())],
            "Nach Einstiegsstunde (UTC)")

        # 4) Wochentag
        namen = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
        res["wochentag"] = table(
            [(namen[d], rep[rep["wochentag"] == d]["r"]) for d in sorted(rep["wochentag"].unique())],
            "Nach Wochentag")

        # 5) Stopdistanz -- wie gross ist das Risiko, das die Kaskade aufmacht?
        q = pd.qcut(rep["planned_risk"], 4, labels=["Q1 eng", "Q2", "Q3", "Q4 weit"], duplicates="drop")
        res["stopdistanz"] = table(
            [(str(lbl), rep[q == lbl]["r"]) for lbl in q.cat.categories],
            "Nach geplanter Stopdistanz (Quartile)")
        print(f"    Stopdistanz in Kurspunkten: p25 {rep['planned_risk'].quantile(.25):.1f} | "
              f"Median {rep['planned_risk'].median():.1f} | p75 {rep['planned_risk'].quantile(.75):.1f}")

        result["beine"][leg] = res

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"\nGeschrieben: {args.out}")


if __name__ == "__main__":
    main()
