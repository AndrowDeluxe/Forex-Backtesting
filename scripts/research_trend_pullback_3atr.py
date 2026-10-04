"""trend_pullback: Backtest-Zahlen fuer den Umbau (Stop 3,0 ATR + FK-Ausfuehrungsweg)
auf EK und Funded -- Nutzerauftrag 2026-10-04 ("gib mir zu Trend Pullback die
veraenderten Backtest-Zahlen, bevor wir das umbauen und live schalten").

Live-Semantik wie research_trend_gs_ausfuehrung.py (M15, Intrabar-SL, Gates).
Vergleich je Konto:
  EK heute     2,0 ATR, Broker-TP 2R, kein R-Detektor, Lag ~2 Min.
  EK neu 2,0   2,0 ATR, Ziel per Scan, R-Detektor 0,50R
  EK neu 3,0   3,0 ATR, Ziel per Scan, R-Detektor 0,50R
  Funded 2,0 / 3,0 (TTP-Kosten, inkl. Platin, Lag 20 Min., Scan-Exit)
Maerkte: EK GOLD/SILVER/CHFJPY/USDJPY, Funded zusaetzlich PLATINUM.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_trend_gs_ausfuehrung as A  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

OUT = REPO / "knowledge" / "_data" / "trend_pullback_3atr.json"
KOSTEN = {"EK": {"GOLD": 0.38}, "Funded": {"GOLD": 2.08}}   # Rest: Engine-Defaults (nicht gemessen)


def run(t, bars, konto, mode, lag, gate, cost_mult=1.0):
    A.BPS.update(KOSTEN[konto])
    m = ["GOLD", "SILVER", "CHFJPY", "USDJPY"] + (["PLATINUM"] if konto == "Funded" else [])
    sub = t[(t["leg"] == "trend_pullback") & t["market"].isin(m)]
    df = A.replay(sub, bars, lag_min=lag, mode=mode, tp_r=2.0, gate_r=gate, max_age=300, cost_mult=cost_mult)
    f = df[df["status"] == "gefuellt"]
    s = A.stats(df)
    s["je_jahr"] = f.groupby(f["entry_time"].dt.year)["r"].mean().round(3).to_dict()
    s["je_markt"] = f.groupby("market")["r"].agg(["count", "mean"]).round(3).to_dict(orient="index")
    s["jahre_positiv"] = f"{int((f.groupby(f['entry_time'].dt.year)['r'].mean() > 0).sum())}/{f['entry_time'].dt.year.nunique()}"
    return s


def main() -> None:
    import mt5_trend_pullback.pipeline as TP
    bars = A.m15_bars()
    TP.ATR_STOP_MULT = 2.0
    t2 = A.engine_trades()
    TP.ATR_STOP_MULT = 3.0
    t3 = A.engine_trades()
    res = {
        "EK_heute_2ATR_brokerTP": run(t2, bars, "EK", "broker", 5, 9.0),
        "EK_neu_2ATR_scan": run(t2, bars, "EK", "scan", 5, 0.5),
        "EK_neu_3ATR_scan": run(t3, bars, "EK", "scan", 5, 0.5),
        "EK_neu_3ATR_scan_kosten_x2": run(t3, bars, "EK", "scan", 5, 0.5, 2.0),
        "Funded_2ATR_scan": run(t2, bars, "Funded", "scan", 20, 0.5),
        "Funded_3ATR_scan": run(t3, bars, "Funded", "scan", 20, 0.5),
        "Funded_3ATR_scan_kosten_x2": run(t3, bars, "Funded", "scan", 20, 0.5, 2.0),
    }
    for k, v in res.items():
        print(f"\n{k}: n={v['n']} ØR={v['avg_r']:+.3f} PF={v['pf']} ΣR={v['sum_r']:+.1f} MaxDD={v['maxdd_r']}R "
              f"IS={v['is']:+.3f} OOS={v['oos']:+.3f} Jahre+ {v['jahre_positiv']}")
        print(f"   je Jahr {v['je_jahr']}")
        print(f"   je Markt { {m: (x['count'], x['mean']) for m, x in v['je_markt'].items()} }")
    OUT.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
    print(f"\nGeschrieben: {OUT}")


if __name__ == "__main__":
    main()
