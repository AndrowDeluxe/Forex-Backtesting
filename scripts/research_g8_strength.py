"""Phase 1 Schritt 4: G8-Staerke-Nachbau als Strategie, volle Overfitting-Sperre.

Split (registriert 2026-10-10 vor jedem Lauf; FRED hat keine Luecken, daher
laengere Historie als die Dukascopy-Grenze 2010-11 aus dem Plan):
  IS 2000-01-03 .. 2017-12-29, OOS .. 2025-10-02, Tresor .. 2026-10-02.
Varianten (vorab, 4 Versuche): top/bottom k in {1, 2, 3} woechentlich,
k = 2 taeglich. Auswahl NUR nach IS-Sharpe.

    python -m scripts.research_g8_strength --stage is      # nur IS-Zahlen, waehlt + friert ein
    python -m scripts.research_g8_strength --stage oos     # einmalig
    python -m scripts.research_g8_strength --stage tresor  # einmalig, nach OOS
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fusion_lab.g8.backtest import daily_returns, stats  # noqa: E402
from fusion_lab.g8.data import log_values, usd_value_panel  # noqa: E402
from research_lock import Lock, deflated_sharpe  # noqa: E402

STRATEGY = "g8_strength"
VARIANTS = {"k1_weekly": (1, "weekly"), "k2_weekly": (2, "weekly"), "k3_weekly": (3, "weekly"),
            "k2_daily": (2, "daily")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["is", "oos", "tresor"], required=True)
    stage = ap.parse_args(argv).stage

    lk = Lock(STRATEGY)
    lk.register_split("2000-01-03", "2017-12-29", "2025-10-02", "2026-10-02")
    logv = log_values(usd_value_panel("fred"))
    logv = logv[logv.index <= "2026-10-02"]

    if stage == "is":
        if lk._load()["frozen"] is None and lk.trials == 0:
            lk.log_trials(len(VARIANTS), "k1/k2/k3 woechentlich, k2 taeglich -- vorab festgelegt")
        res = {}
        for name, (k, reb) in VARIANTS.items():
            r = lk.is_only(daily_returns(logv, k, reb))
            res[name] = stats(r)
            print(f"IS {name}: {res[name]}")
        best = max(res, key=lambda n: res[n]["sharpe"] or -9)
        r = lk.is_only(daily_returns(logv, *VARIANTS[best]))
        dsr = deflated_sharpe(float(r.mean() / r.std()), len(r), lk.trials)
        h = lk.freeze({"variant": best, "k": VARIANTS[best][0], "rebalance": VARIANTS[best][1],
                       "norm": "xs", "horizons": [5, 21, 63], "cost_bps_per_unit": 1.25})
        print(f"\nGewinner (IS-Sharpe): {best}  Deflated Sharpe (taeglich, {lk.trials} Versuche): {dsr:.3f}")
        print(f"eingefroren: {h[:12]}")
        return 0

    cfg = lk._load()["frozen"]
    if cfg is None:
        raise SystemExit("erst --stage is")
    k, reb = cfg["config"]["k"], cfg["config"]["rebalance"]
    lk.unseal(stage, cfg["hash"])
    r = lk.stage_slice(daily_returns(logv, k, reb), stage)
    print(f"{stage.upper()} {cfg['config']['variant']}: {stats(r)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
