"""Challenge (TTP, IQ) und EK -- neue Gewichtung per Monte Carlo + Walk-Forward.

Plan 2026-10-04 (C:\\Users\\andre\\.claude\\plans\\hidden-spinning-possum.md),
Nutzerentscheide: Challenge BEIDE Kriterien, EK bisherige Regel, fehlende Beine
mit echter Ausfuehrung (research_live_legs.py), Gewicht 0 erlaubt.
Reine Auswertung -- nichts wird in Bridges/paper_bots eingespielt.

ENTSCHEIDUNGSVARIABLE: Risiko je Trade in % der Equity, je Bein (ORB je
Instrument). Umrechnung in die Bridge-Konfiguration erst im Bericht.

UNTERSCHIED ZUR FK-RECHNUNG (research_fk_gewichtung_mc_wf.py):
  * Mindestlot + Lot-Rundung IM Optimierer, nicht nur in der Gegenprobe: das
    reale Risiko eines Trades ist max(Ziel abgerundet auf Lot-Schritt, Mindestlot)
    gegen die Referenz-Equity des Kontos; reisst das Mindestlot den Positions-
    deckel, wird der Trade nicht gehandelt (wie core/sizing.py bzw. der 1-%-Deckel).
    Auf EK (~2.840 EUR) ist das der dominante Effekt.
  * Multiplikative Pfade (EK riskiert bis 3,5 %/Trade -- additiv waere falsch).
  * Kontoregeln: Trailing-Grenze, TTP-Tagesgrenze 3 % (Tagesverlust >= 3 % zaehlt
    als Bruch), Profit-Ziel fuer das Kriterium "Ziel vor Bruch".
  * Suche: koordinatenweise ueber ein Raster je Bein (Startpunkte: heute + halb),
    weil das Mindestlot die Zielfunktion nicht-linear macht.

Kriterien:
  A  (Challenge) max. Median-Jahresertrag unter P(Bruch im Jahr) <= 1 %
  B  (Challenge) max. P(Ziel vor Bruch innerhalb 252 Tagen)
  EK            max. Median-Jahresertrag unter P(MaxDD >= 40 % im Jahr) <= 10 %
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import research_live_legs as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

H0, END = L.H0, L.END
OOS_YEARS = list(range(2021, 2027))
N_PATHS, HORIZON, BLOCK = 2000, 252, 10
OUT = REPO / "knowledge" / "_data" / "challenge_ek_gewichtung_mc_wf.json"
USD_EUR = 0.855   # 1 USD in EUR (EURUSD ~1,17), fuer EKs Mindestlot

FUNDED_GRID = [0, .00025, .0005, .00075, .001, .00125, .0015, .002, .0025, .003, .004, .005, .006, .0075, .01]
EK_GRID = [0, .001, .002, .003, .004, .005, .0075, .01, .015, .02, .025, .03, .035, .04, .05]

# Heutige effektive Risiken je Trade (gelesen aus Bridge-Configs, siehe Plan):
#   Funded: capital_weight (TTP 1/6, IQ 1/3) x challenge_portfolio.LEG_RISK_PCT;
#   ctnl_reversal sized auf mind. 300k (CTNL_MIN_ACCOUNT_SIZE) -> 75 / 150 $ = 0,075 / 0,15 %.
#   EK: 1/8 x LEG_RISK_PCT (inkl. Hebel 1,2x), ctnl_reversal 0,019 % (real Mindestlot).
ACCOUNTS = {
    "ttp": {"broker": "ttp", "equity": 100_000.0, "ccy": 1.0, "trail": 0.07, "daily": 0.03, "target": 0.10,
            "pos_cap": 0.01, "open_cap": 0.035, "grid": FUNDED_GRID, "crit": ("A", "B"),
            "current": {"gold_asb": .02 / 6, "cls_practical": .01 / 6, "ctnl_reversal": .00075,
                        "trend_pullback": .005 / 6, "ou_modell": .01 / 6,
                        "orb_sp500": .01 / 18, "orb_us30": .01 / 18, "orb_nasdaq": .01 / 18}},
    "iq": {"broker": "iq", "equity": 100_000.0, "ccy": 1.0, "trail": 0.06, "daily": None, "target": 0.08,
           "pos_cap": 0.01, "open_cap": 0.03, "grid": FUNDED_GRID, "crit": ("A", "B"),
           "current": {"gold_asb": .02 / 3, "cls_practical": .01 / 3, "ctnl_reversal": .0015,
                       "trend_pullback": .005 / 3,
                       "orb_sp500": .01 / 9, "orb_us30": .01 / 9, "orb_nasdaq": .01 / 9}},
    "ek": {"broker": "tickmill", "equity": 2840.0, "ccy": USD_EUR, "trail": 0.45, "daily": None, "target": None,
           "dd_obj": 0.40, "p_obj": 0.10, "pos_cap": 0.05, "open_cap": 0.30, "grid": EK_GRID, "crit": ("EK",),
           "current": {"gold_asb": .0352, "btc_ema_cross": .0352, "gold_silver": .0352, "trend_pullback": .022,
                       "cls_practical": .0066, "ou_modell": .0037, "ctnl_reversal": .00019,
                       "orb_sp500": .0036, "orb_us30": .0036, "orb_nasdaq": .0036}},
}


# ------------------------------------------------------------ Daten
def load(acc: str) -> pd.DataFrame:
    a = ACCOUNTS[acc]
    t = L.build(a["broker"])
    t = t[t["leg"].isin(a["current"].keys())].copy()
    t = t.dropna(subset=["r", "exit_time"])
    t["minlot_frac"] = (t["stop_px"].astype(float) * t["unit_usd"].astype(float) * a["ccy"] / a["equity"]).fillna(0.0)
    return t.reset_index(drop=True)


class Book:
    """Trades eines Kontos auf ein Werktags-Raster abgebildet."""

    def __init__(self, t: pd.DataFrame, acc: str, days: pd.DatetimeIndex):
        self.acc, self.a = acc, ACCOUNTS[acc]
        self.legs = list(self.a["current"].keys())
        self.days = days
        day = t["exit_time"].dt.normalize()
        pos = days.searchsorted(day)
        keep = (pos < len(days)) & (day >= days[0]) & (day <= days[-1])
        t = t[keep]
        self.idx = {l: pos[keep][t["leg"].to_numpy() == l] for l in self.legs}
        self.R = {l: t.loc[t["leg"] == l, "r"].to_numpy(float) for l in self.legs}
        self.ml = {l: t.loc[t["leg"] == l, "minlot_frac"].to_numpy(float) for l in self.legs}

    def daily(self, w: dict) -> np.ndarray:
        out = np.zeros(len(self.days))
        cap = self.a["pos_cap"]
        for l in self.legs:
            target = min(w.get(l, 0.0), cap)
            if target <= 0 or len(self.R[l]) == 0:
                continue
            ml = self.ml[l]
            with np.errstate(divide="ignore", invalid="ignore"):
                lots = np.where(ml > 0, np.floor(target / ml + 1e-9), np.nan)
            risk = np.where(ml <= 0, target,                              # Rundung vernachlaessigbar
                            np.where(lots >= 1, lots * ml,               # abgerundet
                                     np.where(ml <= cap, ml, 0.0)))      # Anhebung oder Verwurf
            np.add.at(out, self.idx[l], risk * self.R[l])
        return out


# ------------------------------------------------------------ Monte Carlo
def paths_idx(n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(HORIZON / BLOCK))
    st = rng.integers(0, n - BLOCK, size=(N_PATHS, nb))
    return (st[:, :, None] + np.arange(BLOCK)).reshape(N_PATHS, -1)[:, :HORIZON]


def path_metrics(ret: np.ndarray, a: dict) -> dict:
    """ret (Pfade, Tage) -> Kennzahlen nach Kontoregeln."""
    eq = np.cumprod(1 + ret, axis=1)
    peak = np.maximum.accumulate(np.concatenate([np.ones((len(eq), 1)), eq], axis=1), axis=1)[:, 1:]
    dd = eq / peak - 1
    lim = a.get("dd_obj") or a["trail"]
    br = dd <= -lim
    if a.get("daily"):
        br |= ret <= -a["daily"]
    H = ret.shape[1]
    first_br = np.where(br.any(axis=1), br.argmax(axis=1), H)
    m = {"median_return": float(np.median(eq[:, -1] - 1)), "p_breach": float((first_br < H).mean()),
         "median_maxdd": float(np.median(dd.min(axis=1)))}
    if a.get("target"):
        hit = eq >= 1 + a["target"]
        first_hit = np.where(hit.any(axis=1), hit.argmax(axis=1), H)
        ok = first_hit < first_br
        m["p_target"] = float(ok.mean())
        m["median_days_target"] = float(np.median(first_hit[ok])) if ok.any() else None
    return m


def score(m: dict, crit: str, a: dict) -> float:
    if crit == "B":
        return m["p_target"]
    limit = a.get("p_obj", 0.01)
    if m["p_breach"] > limit:
        return -10 - (m["p_breach"] - limit) * 100       # unzulaessig: erst Bruchrisiko senken
    return m["median_return"]


def optimise(book: Book, day_mask: np.ndarray, crit: str, seed: int) -> tuple[dict, dict]:
    a, grid = book.a, book.a["grid"]
    sel = np.flatnonzero(day_mask)
    idx = sel[paths_idx(len(sel), seed)]

    def ev(w):
        m = path_metrics(book.daily(w)[idx], a)
        return score(m, crit, a), m

    def snap(x):
        return min(grid, key=lambda g: abs(g - x))

    best = None
    for start in ({l: snap(v) for l, v in a["current"].items()},
                  {l: snap(v / 2) for l, v in a["current"].items()}):
        w = dict(start)
        s, m = ev(w)
        for _ in range(80):
            cand = []
            for l in book.legs:
                i = grid.index(w[l])
                for j in {max(i - 1, 0), min(i + 1, len(grid) - 1), 0}:
                    if j != i:
                        w2 = dict(w); w2[l] = grid[j]; cand.append(w2)
            res = [(ev(c), c) for c in cand]
            (s2, m2), c2 = max(res, key=lambda x: x[0][0])
            if s2 <= s + 1e-9:
                break
            w, s, m = c2, s2, m2
        if best is None or s > best[0]:
            best = (s, w, m)
    return best[1], best[2]


def realised(book: Book, w: dict, day_mask: np.ndarray) -> dict:
    ret = book.daily(w)[day_mask][None, :]
    m = path_metrics(ret, book.a)
    eq = np.cumprod(1 + ret[0])
    return {"return_pct": float((eq[-1] - 1) * 100), "maxdd_pct": m["median_maxdd"] * 100,
            "breach": m["p_breach"] > 0, **({"target_hit": m["p_target"] > 0} if book.a.get("target") else {})}


# ------------------------------------------------------------ Ereignis-Simulation
def event_sim(t: pd.DataFrame, w: dict, acc: str, start: str | None = None) -> dict:
    """Trade fuer Trade mit Equity zum Entry, Mindestlot gegen die AKTUELLE Equity,
    Positions- und Offenrisiko-Deckel, Trailing-Bruch (Funded: Konto weg; EK:
    Kill-Switch), TTP-Tagesgrenze."""
    a = ACCOUNTS[acc]
    if start:
        t = t[t["entry_time"] >= pd.Timestamp(start)]
    ev = sorted([(r.entry_time, 1, i) for i, r in t.iterrows()] + [(r.exit_time, 0, i) for i, r in t.iterrows()],
                key=lambda x: (x[0], x[1]))
    eq0 = eq = a["equity"]
    peak, risk_of, open_r = eq, {}, {}
    day, day_start, dead, breach, target_day = None, eq, False, None, None
    maxdd = 0.0
    for ts, kind, i in ev:
        d = pd.Timestamp(ts).normalize()
        if d != day:
            if day is not None:
                peak = max(peak, eq)
                dd = eq / peak - 1
                maxdd = min(maxdd, dd)
                if dd <= -a["trail"] and breach is None:
                    breach, dead = str(day.date()), True
            day, day_start = d, eq
        x = t.loc[i]
        if kind == 1:
            if dead or (a.get("daily") and eq / day_start - 1 <= -a["daily"]):
                continue
            target = min(w.get(x["leg"], 0.0), a["pos_cap"]) * eq
            if target <= 0:
                continue
            ml = float(x["stop_px"]) * float(x["unit_usd"]) * a["ccy"]
            if ml > 0:
                lots = np.floor(target / ml + 1e-9)
                risk = lots * ml if lots >= 1 else (ml if ml <= a["pos_cap"] * eq else 0.0)
            else:
                risk = target
            if risk <= 0 or (sum(open_r.values()) + risk) / eq > a["open_cap"]:
                continue
            risk_of[i] = open_r[i] = risk
        elif i in risk_of:
            eq += risk_of[i] * float(x["r"])
            open_r.pop(i, None)
            if a.get("daily") and eq / day_start - 1 <= -a["daily"] and breach is None:
                breach, dead = f"{day.date()} (Tagesgrenze)", True
            if a.get("target") and target_day is None and eq >= eq0 * (1 + a["target"]):
                target_day = str(day.date())
    return {"return_pct": (eq / eq0 - 1) * 100, "maxdd_pct": maxdd * 100, "erster_bruch": breach,
            "ziel_erreicht": target_day, "trades": len(risk_of)}


def fmt(w: dict) -> str:
    return " ".join(f"{l.replace('orb_', '')}={v * 100:.3g}%" for l, v in w.items())


def main() -> None:
    days = pd.bdate_range(H0, END)
    result: dict = {}
    for acc in ("ttp", "iq", "ek"):
        a = ACCOUNTS[acc]
        t = load(acc)
        book = Book(t, acc, days)
        print(f"\n######## {acc.upper()} ({a['broker']}) -- {len(t)} Trades")
        print(t.groupby("leg").agg(n=("r", "size"), avg_r=("r", "mean"), sum_r=("r", "sum"),
                                   minlot_med=("minlot_frac", "median")).round(4).to_string())
        res = {"current": a["current"], "walk_forward": {}, "voll": {}}
        cur_full = path_metrics(book.daily(a["current"])[paths_idx(len(days), 99)], a)
        res["current_mc"] = cur_full
        print(f"  HEUTE MC: {cur_full}")
        for crit in a["crit"]:
            wf, sums = {}, {"opt": [], "heute": []}
            for y in OOS_YEARS:
                is_mask = days < pd.Timestamp(f"{y}-01-01")
                oos_mask = (days >= pd.Timestamp(f"{y}-01-01")) & (days <= pd.Timestamp(f"{y}-12-31"))
                w, m = optimise(book, is_mask, crit, seed=y)
                r_opt, r_cur = realised(book, w, oos_mask), realised(book, a["current"], oos_mask)
                wf[y] = {"gewichte": w, "is_mc": m, "oos_opt": r_opt, "oos_heute": r_cur}
                sums["opt"].append(r_opt); sums["heute"].append(r_cur)
                print(f"  [{crit}] {y}: {fmt(w)}\n        OOS opt {r_opt} | heute {r_cur}")
            res["walk_forward"][crit] = wf
            res.setdefault("wf_summary", {})[crit] = {
                k: {"summe_return_pct": sum(x["return_pct"] for x in v), "bruchjahre": sum(x["breach"] for x in v),
                    "schlechtestes_maxdd_pct": min(x["maxdd_pct"] for x in v),
                    **({"zieljahre": sum(x.get("target_hit", False) for x in v)} if a.get("target") else {})}
                for k, v in sums.items()}
            print(f"  [{crit}] WF-Summe: {res['wf_summary'][crit]}")
            w, m = optimise(book, np.ones(len(days), bool), crit, seed=2026)
            ctrl = path_metrics(book.daily(w)[paths_idx(len(days), 99)], a)
            evn = {"neu_2019": event_sim(t, w, acc), "heute_2019": event_sim(t, a["current"], acc),
                   "neu_2026": event_sim(t, w, acc, "2026-01-01"), "heute_2026": event_sim(t, a["current"], acc, "2026-01-01")}
            res["voll"][crit] = {"gewichte": w, "mc": ctrl, "ereignis_sim": evn}
            print(f"  [{crit}] VOLL: {fmt(w)}\n        MC neu {ctrl}")
            for k, v in evn.items():
                print(f"        Ereignis {k:11} {v}")
        result[acc] = res
        OUT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"\nGeschrieben: {OUT}")


if __name__ == "__main__":
    main()
