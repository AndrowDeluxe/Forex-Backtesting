"""FK Instant Funding -- was bringen die noch nicht live geschalteten Beine?

Nutzerfrage 2026-10-04: "Welche offenen Beine haben wir noch zur Live-
Schaltung auf dem Instant Funding Konto und wie wuerden sie das Konto
beeinflussen?"

Offen = im Paper-Bot (fk_instant_funding/paper_bot.py), nicht in
FKInstantFunding-MT5-Bridge/config.py::LIVE_LEGS: trend_pullback (GOLD/SILVER/
PLATINUM/CHFJPY/USDJPY) und gold_silver. Bewusst NICHT betrachtet:
ctnl_continuation (2026-09-30 mangels Edge stillgelegt), orb_us30 (seit 04.10.
pausiert, ohne OOS-Edge).

FK-Stand, wie er ab Montag 05.10. live laeuft: ORB SP500 (Storno bei
Gegenbruch) + NASDAQ (Storno am geplanten SL, kein Teilziel), Gold ASB als
Stop-Order 1,5x, CLS, CTNL Reversal; alte Gewichte vom 29.08. (der Vorschlag
vom 03.10. ist nicht eingespielt). Kosten BeyondIQ (XAU 0,79 bps), Rest wie
research_live_legs.py ("iq" = derselbe Server).

Szenarien (alle mit Mindestlot, FK-Regeln: Trailing 5 %, Deckel 0,5 %/Trade):
  S1 heute live
  S2 heute + trend_pullback + gold_silver mit den Paper-Bot-Gewichten
  S3 Vorschlag 03.10. (ohne neue Beine)
  S4 neu optimiert MIT den neuen Beinen (Kriterium wie 03.10., + Walk-Forward)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import research_challenge_ek_gewichtung_mc_wf as M  # noqa: E402
import research_fk_gesamtportfolio_2026 as fk  # noqa: E402
import research_live_legs as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CACHE = REPO / "portfolio_construction" / "results" / "live_trades_fk_offene_beine_2019_2026.csv"
OUT = REPO / "knowledge" / "_data" / "fk_offene_beine.json"
pb = fk.pb
W = {l: pb.CAPITAL_WEIGHT[l] * pb.LEG_RISK_PCT[l] for l in pb.CAPITAL_WEIGHT}
HEUTE = {"gold_asb": W["gold_asb"], "cls_practical": W["cls_practical"], "ctnl_reversal": W["ctnl_reversal"],
         "orb_sp500": W["orb_sp500"], "orb_nasdaq": W["orb_nasdaq"], "trend_pullback": 0.0, "gold_silver": 0.0}
MIT_PAPER = dict(HEUTE, trend_pullback=W["trend_pullback"], gold_silver=W["gold_silver"])
VORSCHLAG_0310 = {"gold_asb": .0035, "cls_practical": .0045, "ctnl_reversal": .00056, "orb_sp500": .001,
                  "orb_nasdaq": .0005, "trend_pullback": 0.0, "gold_silver": 0.0}
FK_GRID = [0, .00025, .0005, .00075, .001, .00125, .0015, .002, .0025, .003, .0035, .004, .0045, .005]

M.ACCOUNTS["fk"] = {"broker": "iq", "equity": 100_000.0, "ccy": 1.0, "trail": 0.05, "daily": None, "target": None,
                    "pos_cap": pb.MAX_POSITION_LOSS_PCT, "open_cap": 0.05, "grid": FK_GRID, "crit": ("A",),
                    "current": HEUTE}


def trades(refresh: bool = False) -> pd.DataFrame:
    if CACHE.exists() and not refresh:
        return pd.read_csv(CACHE, parse_dates=["entry_time", "exit_time"])
    L._set_broker("iq")
    fk.XAU_BPS = 0.79
    o = fk.orb_trades()
    o = o[o["leg"] != "orb_us30"].assign(unit_usd=L.UNIT_USD["INDEX"]).drop(columns=["spread_bps"], errors="ignore")
    parts = [o, fk.gold_asb_trades("stoporder").assign(unit_usd=L.UNIT_USD["XAU"]),
             fk.cls_trades().assign(unit_usd=L.UNIT_USD["EURUSD"]),
             fk.ctnl_trades().assign(unit_usd=L.UNIT_USD["XAU"]),
             L.trend_pullback_trades("iq"), L.gold_silver_trades("iq")]
    t = pd.concat(parts, ignore_index=True).sort_values("entry_time").reset_index(drop=True)
    t.to_csv(CACHE, index=False)
    return t


def bewerte(book: M.Book, t: pd.DataFrame, w: dict, days) -> dict:
    a = M.ACCOUNTS["fk"]
    mc = M.path_metrics(book.daily(w)[M.paths_idx(len(days), 99)], a)
    return {"risiko_je_trade_pct": {k: round(v * 100, 4) for k, v in w.items()},
            "mc": mc, "ereignis_2019_2026": M.event_sim(t, w, "fk"), "ereignis_2026": M.event_sim(t, w, "fk", "2026-01-01")}


def main() -> None:
    t = trades(refresh="--refresh" in sys.argv)
    a = M.ACCOUNTS["fk"]
    t["minlot_frac"] = (t["stop_px"].astype(float) * t["unit_usd"].astype(float) / a["equity"]).fillna(0.0)
    days = pd.bdate_range(M.H0, M.END)
    book = M.Book(t, "fk", days)

    print("Beine (FK-Ausfuehrung, 2019-2026):")
    st = t.groupby("leg")["r"].agg(n="size", avg_r="mean", sum_r="sum")
    st["jahre_positiv"] = t.groupby(["leg", t["entry_time"].dt.year])["r"].sum().gt(0).groupby("leg").sum()
    print(st.round(3).to_string())
    print("\nØ R je Jahr:")
    print(t.pivot_table(index="leg", columns=t["entry_time"].dt.year, values="r", aggfunc="mean").round(2).to_string())

    # Korrelation der Tages-P&L mit dem heutigen Live-Portfolio
    base = book.daily(HEUTE)
    korr = {}
    for leg in ("trend_pullback", "gold_silver"):
        x = book.daily({leg: 0.001})
        m = (x != 0) | (base != 0)
        korr[leg] = float(np.corrcoef(x[m], base[m])[0, 1])
    print(f"\nKorrelation Tages-P&L mit dem heutigen FK-Portfolio: {korr}")

    res = {"beine": st.round(4).reset_index().to_dict(orient="records"), "korrelation_mit_heute": korr, "szenarien": {}}
    for name, w in (("S1_heute", HEUTE), ("S2_heute_plus_paper_gewichte", MIT_PAPER), ("S3_vorschlag_0310", VORSCHLAG_0310)):
        res["szenarien"][name] = bewerte(book, t, w, days)

    # S4: neu optimiert MIT den neuen Beinen, plus Walk-Forward
    wf = {}
    for y in M.OOS_YEARS:
        is_mask = days < pd.Timestamp(f"{y}-01-01")
        oos = (days >= pd.Timestamp(f"{y}-01-01")) & (days <= pd.Timestamp(f"{y}-12-31"))
        w, m = M.optimise(book, is_mask, "A", seed=y)
        wf[y] = {"gewichte": w, "oos_opt": M.realised(book, w, oos), "oos_heute": M.realised(book, HEUTE, oos),
                 "oos_vorschlag_0310": M.realised(book, VORSCHLAG_0310, oos)}
        print(f"WF {y}: {M.fmt(w)}\n    opt {wf[y]['oos_opt']} | heute {wf[y]['oos_heute']} | 03.10. {wf[y]['oos_vorschlag_0310']}")
    w4, _ = M.optimise(book, np.ones(len(days), bool), "A", seed=2026)
    res["szenarien"]["S4_neu_optimiert_mit_neuen_beinen"] = bewerte(book, t, w4, days)
    res["walk_forward"] = wf
    res["wf_summe"] = {k: {"summe_return_pct": sum(v[k]["return_pct"] for v in wf.values()),
                           "bruchjahre": sum(v[k]["breach"] for v in wf.values()),
                           "schlechtestes_maxdd_pct": min(v[k]["maxdd_pct"] for v in wf.values())}
                       for k in ("oos_opt", "oos_heute", "oos_vorschlag_0310")}
    print(f"\nWF-Summe: {res['wf_summe']}")
    for k, v in res["szenarien"].items():
        print(f"\n=== {k}\n  Risiko/Trade %: {v['risiko_je_trade_pct']}\n  MC: {v['mc']}"
              f"\n  2019-2026: {v['ereignis_2019_2026']}\n  2026: {v['ereignis_2026']}")
    OUT.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
    print(f"\nGeschrieben: {OUT}")


if __name__ == "__main__":
    main()
