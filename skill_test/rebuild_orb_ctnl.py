"""ORB + CTNL mit aktuellem Code neu simulieren (NASDAQ-Storno am SL, SP500/US30 'opposite',
CTNL nach _bar_length-Fix). Eigene Dateien, die alten live_trades_* bleiben unberuehrt.
Aufruf: python skill_test/rebuild_orb_ctnl.py ttp|tickmill"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]
import research_live_legs as rl  # noqa: E402

b = sys.argv[1]
rl._chunked_dukascopy_fetch()
rl.END = (pd.Timestamp.today().normalize() - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
rl.fk.END = rl.END
rl._set_broker(b)
o = rl.fk.orb_trades().drop(columns=["spread_bps"], errors="ignore").assign(unit_usd=rl.UNIT_USD["INDEX"])
c = rl.fk.ctnl_trades().assign(unit_usd=rl.UNIT_USD["XAU"])
t = pd.concat([o, c], ignore_index=True).sort_values("entry_time")
out = ROOT / "skill_test" / "results" / f"orb_ctnl_{b}_storno.csv"
t.to_csv(out, index=False)
print(out, t.groupby("leg")["r"].agg(["count", "mean", "sum"]).round(3).to_string(), t.entry_time.max())
