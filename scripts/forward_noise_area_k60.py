"""Forward-Test: NASDAQ Noise-Area K2 + Oel-Index-Korrelation (60 Tage) < 0.

Nutzerentscheid 2026-10-14 ("Das passt, nutze die Regel fuer den Forward-Test"), nach dem
Oel-Faktor-Screening in research_noise_area_oel_fit2026.py: einziger Faktor, der in 2016-22,
2023-09/25 und 10/25-09/26 traegt. NICHT nach der Auswahlregel des Rasters gewaehlt, sondern
nach Sicht auf alle Perioden -> IS/OOS/Tresor sind VORBELASTET, nur der Forward zaehlt.

REGEL (eingefroren, Lock noise_area_oel_k60_forward_20261014):
  NASDAQ, Noise Area VM 1,0 / Lookback 90 (Paper-Config 11.10.), Momentum, beide Richtungen,
  nur der erste Ausbruch des Tages (Entscheid 10:00-15:30 zur vollen/halben Stunde),
  kein Stop, Ausstieg 16:00. Nur an Tagen, an denen die Korrelation der Tagesrenditen
  Oel (WTI) <-> NASDAQ ueber 60 Tage bis zum Vortag < 0 ist. Kosten 1,29 bps je Rundturn.
  Konto: 100k, Sizing 1x (100 % Notional) und dyn (Paper: min(4, 2 % / Tagesvola 14 T.)).
Forward ab 2026-10-15, Stichtag 2027-03-31.

  python scripts/forward_noise_area_k60.py register
  python scripts/forward_noise_area_k60.py backtest     # IS/OOS/Tresor auf 100k (vorbelastet)
  python scripts/forward_noise_area_k60.py evaluate     # ab 2027-03-31
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).resolve().parent))

from noise_area_momentum.engine import build_grid, run_general  # noqa: E402
from ny_open_orb.data import fetch_m1  # noqa: E402
from research_lock import Lock  # noqa: E402
from research_noise_area_momentum import COST_RT, IS_END, IS_START, OOS_END, TRESOR_END, grid  # noqa: E402
from research_noise_area_oel import oil_grid  # noqa: E402
from research_noise_area_oel_fit2026 import bases, features, masks  # noqa: E402

STRATEGY = "noise_area_oel_k60_forward_20261014"
INST = "NASDAQ"
FORWARD_START, EVAL_DATE = "2026-10-15", "2027-03-31"
OUT = ROOT / "noise_area_momentum" / "results"
CONFIG = {"inst": INST, "basis": "k2 (mom, beide, nur 1. Trade, Exit 16:00)", "vm": 1.0, "lookback": 90,
          "oel_filter": "Korr(Oel, NASDAQ, 60 Tage bis Vortag) < 0", "kosten_rt_bps": COST_RT[INST],
          "konto": "100k, Sizing 1x und dyn"}
PERIODS = [("IS 2016-07..2022", IS_START, IS_END), ("OOS 2023..09/2025", "2023-01-01", OOS_END),
           ("Tresor 10/2025..09/2026", "2025-10-01", TRESOR_END)]
START_EQ = 100_000.0


def lock() -> Lock:
    lk = Lock(STRATEGY)
    lk.register_split(IS_START, IS_END, OOS_END, TRESOR_END)
    return lk


SIZINGS = {"1x": dict(sizing="1x"), "dyn": dict(sizing="dyn"),
           "1% Risiko": dict(sizing="dyn", vol_target=0.01)}   # 1 Tagessigma (14 T.) = 1 % Konto, Hebel <= 4


def run_rule(g: dict, oil: dict, sizing: str) -> pd.DataFrame:
    lo, so = masks(features(g, oil), k=(60, 0.0))
    return run_general(g, cost_rt_bps=COST_RT[INST], long_ok=lo, short_ok=so, **SIZINGS[sizing], **bases(INST)["k2"])


def account(df: pd.DataFrame, a: str, b: str) -> tuple[dict, pd.DataFrame]:
    d = df[(df.index >= a) & (df.index <= b) & df["valid"]]
    eq = START_EQ * (1 + d["ret_net"]).cumprod()
    pnl = eq.diff().fillna(eq.iloc[0] - START_EQ)
    tr = d["trades"] > 0
    wins, losses = pnl[tr & (pnl > 0)], pnl[tr & (pnl < 0)]
    dd = eq / eq.cummax() - 1
    yrs = len(d) / 252
    r = d["ret_net"]
    out = {"Trades": int(tr.sum()), "Endstand": eq.iloc[-1], "Rendite_%": (eq.iloc[-1] / START_EQ - 1) * 100,
           "CAGR_%": ((eq.iloc[-1] / START_EQ) ** (1 / yrs) - 1) * 100, "MaxDD_%": dd.min() * 100,
           "MaxDD_EUR": (eq - eq.cummax()).min(), "Trefferquote_%": len(wins) / max(tr.sum(), 1) * 100,
           "PF": wins.sum() / -losses.sum() if len(losses) else np.inf,
           "Oe_Trade_EUR": pnl[tr].mean(), "Oe_Gewinner_EUR": wins.mean(), "Oe_Verlierer_EUR": losses.mean(),
           "bester_Tag_EUR": pnl.max(), "schlechtester_Tag_EUR": pnl.min(),
           "Sharpe": r.mean() / r.std(ddof=1) * np.sqrt(252), "Oe_Hebel": d.loc[tr, "lev"].mean(),
           "Oe_Verlierer_%Konto": r[tr & (r < 0)].mean() * 100, "schlimmster_Trade_%Konto": r[tr].min() * 100,
           "Tage_mit_Filter_offen_%": None}
    trades = pd.DataFrame({"pnl_eur": pnl[tr], "ret_%": r[tr] * 100, "hebel": d.loc[tr, "lev"],
                           "equity": eq[tr]})
    return out, trades


def stage_register() -> None:
    lk = lock()
    h = lk.freeze(CONFIG)
    for st in ("oos", "tresor"):                 # formal; Historie ist vollstaendig gesehen
        if st not in lk._load()["unsealed"]:
            lk.unseal(st, h)
    if lk._load().get("forward") is None:
        lk.register_forward(FORWARD_START, EVAL_DATE, 10**6)
    print("registriert", h[:12], "| Forward ab", FORWARD_START, "| Stichtag", EVAL_DATE)


def stage_backtest() -> None:
    g, oil = grid(INST), oil_grid("index")
    feats = features(g, oil)
    open_days = pd.Series(np.nan_to_num(feats["k60"], nan=9) < 0, index=g["dates"])
    rows, years, alltr = [], {}, []
    for sz in SIZINGS:
        df = run_rule(g, oil, sz)
        for per, a, b in PERIODS:
            m, tr = account(df, a, b)
            m["Tage_mit_Filter_offen_%"] = open_days[(open_days.index >= a) & (open_days.index <= b)].mean() * 100
            rows.append({"Sizing": sz, "Periode": per, **m})
            alltr.append(tr.assign(sizing=sz, periode=per))
            d = df[(df.index >= a) & (df.index <= b) & df["valid"]]
            yr = (1 + d["ret_net"]).groupby(d.index.year).prod() - 1
            years[(sz, per)] = yr * 100
    rep = pd.DataFrame(rows)
    rep.to_csv(OUT / "k60_forward_backtest_100k.csv", index=False)
    pd.concat(alltr).to_csv(OUT / "k60_forward_backtest_trades.csv")
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(rep.set_index(["Sizing", "Periode"]).T.round(2).to_string())
    print("\nJahresrenditen % (jede Periode startet bei 100k):")
    print(pd.DataFrame(years).round(1).to_string())


def stage_evaluate() -> None:
    lk = lock()
    lk.unseal("forward", lk._load()["frozen"]["hash"])
    g = build_grid(fetch_m1(INST, IS_START, EVAL_DATE, force_refresh=True))
    oil = oil_grid("index", end=EVAL_DATE, refresh=True)
    for sz in SIZINGS:
        m, _ = account(run_rule(g, oil, sz), FORWARD_START, EVAL_DATE)
        print(sz, {k: round(v, 2) if isinstance(v, float) else v for k, v in m.items()})


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    {"register": stage_register, "backtest": stage_backtest, "evaluate": stage_evaluate}[sys.argv[1]]()
