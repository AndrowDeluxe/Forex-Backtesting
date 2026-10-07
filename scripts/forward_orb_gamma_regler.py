"""Forward-Test: Live-ORB mit und ohne Gamma-Risikoregler (vorab registriert).

Nutzerentscheid 2026-10-07: "Nimm das mit in den Forward-Test, am Ende des
Jahres schauen wir dann und vergleichen."

VORAB FESTGELEGT (eingefroren, Lock orb_live_gamma_forward_20261007):
  Strategien: ORB-Live-Konfiguration Stand 04.10.2026 fuer SP500 und NASDAQ
              (research_orb_is_only_reopt.LIVE), unveraendert.
  Variante A: ohne Regler (1 % vom Kontostand je Trade)
  Variante B: Gamma-Regler -- an Tagen, an denen das SPX-GEX vom Vortag im
              unteren (Q1) oder oberen (Q5) Fuenftel seiner letzten 252
              Handelstage liegt, halbes Risiko (0,5 %); sonst 1 %.
  Gamma-Quelle: SqueezeMetrics DIX.csv (bei der Auswertung frisch laden).
  Konto: je Variante 100k ab Forward-Start, Tages-Sizing wie bisher.
  Vergleich: Σ R (gewichtet), PF, Endstand, MaxDD je Variante und Index.
  Forward-Start 2026-10-05; Auswertung fruehestens 2026-12-31 (Lock-Regel).
  Grundlage: Gamma -> Tagesrange blind bestaetigt (research_gamma_rules_blind.py),
  Regler 2025-26 beschreibend: MaxDD ueberall kleiner, NASDAQ live weniger Ertrag.

  python scripts/forward_orb_gamma_regler.py --stage register   # jetzt
  python scripts/forward_orb_gamma_regler.py --stage evaluate   # ab 31.12.2026
"""
import sys
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).resolve().parent))

from research_lock import Lock  # noqa: E402

STRATEGY = "orb_live_gamma_forward_20261007"
FORWARD_START, EVAL_DATE = "2026-10-05", "2026-12-31"
RES = ROOT / "ny_open_orb" / "results"
CONFIG = {
    "strategien": "ORB-Live-Konfiguration Stand 04.10.2026 (research_orb_is_only_reopt.LIVE), SP500 + NASDAQ",
    "A": "ohne Regler, 1 % vom Kontostand je Trade",
    "B": "SPX-GEX Vortag im 252-Tage-Perzentil < 20 % oder > 80 % -> 0,5 %, sonst 1 %",
    "gamma_quelle": "https://squeezemetrics.com/monitor/static/DIX.csv",
    "konto": "100k je Variante ab 2026-10-05, Tages-Sizing",
}


def lock() -> Lock:
    lk = Lock(STRATEGY)
    # IS/OOS hier nur formal (Historie bereits gesehen); der eigentliche Test ist der Forward.
    lk.register_split("2016-07-28", "2025-09-30", "2026-09-30")
    lk.register_forward(FORWARD_START, EVAL_DATE, 10**6)   # nur der Stichtag oeffnet
    return lk


def stage_register() -> int:
    lk = lock()
    h = lk.freeze(CONFIG)
    if "oos" not in lk._load()["unsealed"]:
        lk.unseal("oos", h)        # Historie bis 09/2026 ist ohnehin gesehen
    print("registriert, Hash", h, "| Auswertung fruehestens", EVAL_DATE)
    return 0


def stage_evaluate() -> int:
    from research_orb_is_only_reopt import LIVE, load, run_config
    lk = lock()
    h = lk.freeze(CONFIG)
    lk.unseal("forward", h)        # bricht vor dem Stichtag ab
    raw = urllib.request.urlopen(urllib.request.Request(CONFIG["gamma_quelle"], headers={"User-Agent": "Mozilla/5.0"})).read()
    gfile = ROOT / "scripts" / "frozen_data" / f"sqzme_dix_gex_{pd.Timestamp.today():%Y%m%d}.csv"
    gfile.write_bytes(raw)
    g = pd.read_csv(gfile, parse_dates=["date"]).set_index("date")["gex"].sort_index()
    p = g.rolling(252, min_periods=120).apply(lambda w: (w[:-1] < w[-1]).mean(), raw=True).shift(1)
    rows = []
    end = pd.Timestamp.today().strftime("%Y-%m-%d")
    for inst in ("SP500", "NASDAQ"):
        frames, sessions, bias = load(inst, end)
        r, _ = run_config(frames, sessions, bias, inst, LIVE[inst])
        r.index = pd.DatetimeIndex(r.index).tz_localize(None)
        r = r[r.index >= FORWARD_START]
        pp = p.reindex(r.index.normalize(), method="ffill").to_numpy()
        for var, w in (("A ohne", np.ones(len(r))), ("B Gamma-Regler", np.where((pp < .2) | (pp > .8), .5, 1.0))):
            df = pd.DataFrame({"r": r.values, "w": w}, index=r.index)
            eq, path = 100_000.0, [100_000.0]
            for _, gday in df.groupby(df.index.normalize()):
                eq += float((gday.r * gday.w).sum()) * 0.01 * eq
                path.append(eq)
            path = np.array(path)
            eff = df.r * df.w
            loss = -eff[eff < 0].sum()
            rows.append({"inst": inst, "variante": var, "trades": len(df), "sum_r_gewichtet": eff.sum(),
                         "pf": eff[eff > 0].sum() / loss if loss > 0 else np.inf, "konto": eq,
                         "maxdd_pct": (path / np.maximum.accumulate(path) - 1).min() * 100})
    out = pd.DataFrame(rows)
    out.to_csv(RES / "forward_orb_gamma_regler.csv", index=False)
    print(out.round(2).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    stage = sys.argv[sys.argv.index("--stage") + 1]
    sys.exit(stage_register() if stage == "register" else stage_evaluate())
