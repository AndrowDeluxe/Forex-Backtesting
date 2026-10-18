"""Kostenzerlegung fuer die eingefrorene Gold-ASB-IS-only-Konfiguration (kein neuer Versuch):
dieselbe Simulation mit bps=TTP und bps=0 -> cost_r je Trade. Ausgabe: trades_cost.csv."""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(r"C:\Users\andre\Forex-Backtesting")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import research_gold_asb_is_only_reopt as ro  # noqa: E402
from research_gold_asb_optimization import simulate  # noqa: E402

OUT = Path(sys.argv[1])
sel = json.loads((ro.RES / "is_reopt_selection.json").read_text(encoding="utf-8"))
w = sel["winner"]
days, m5 = ro.load_days()
days = days[days.index < pd.Timestamp(ro.TRESOR_END, tz=days.index.tz) + pd.Timedelta(days=1)]
t = ro.run_sim(days, m5, w["stop"], w["cancel"], w["exit"])
t = t[ro.mask(t, w)]
g = simulate(days.reset_index(drop=True), m5, cancel=w["cancel"], stop_frac=w["stop"],
             exit_time=ro.EXITS[w["exit"]], bps=0.0).set_index("window_end")
out = pd.DataFrame({"time": pd.DatetimeIndex(t["window_end"]), "dir": t["dir"].to_numpy(), "r": t["R"].to_numpy(),
                    "r_gross": g["R"].reindex(t["window_end"]).to_numpy(), "why": t["why"].to_numpy()})
out["cost_r"] = out["r_gross"] - out["r"]
out.to_csv(OUT, index=False)
print(len(out), out["r"].sum().round(2), out["cost_r"].mean().round(4), out["r_gross"].isna().sum())
