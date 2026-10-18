"""Challenge-Gewichtung: K60 (NASDAQ) + ORB-Oel (SP500/NASDAQ) fuer TTP und IQ -- MC + Walk-Forward.

Nutzerauftrag 2026-10-16: "Passe das Risiko auf Challenges an. Optimiere Trade, Gewichtung und Risiko.
Danach lassen wir den Forward-Test erstmal laufen." Plan wild-discovering-wave (freigegeben 16.10.).
Methode wie scripts/research_fk_gewichtung_mc_wf.py (03.10.).

STRUKTUR je Challenge (81): K60 aus/SL 1 sigma/ohne Stop (Exit 15:55) x ORB SP500 aus/O1/O2 x
  ORB NASDAQ aus/O1/O2 x max. Trades pro Tag 1/2/3 (nach Einstiegszeit, spaetere fallen weg).
RISIKO je Trade je aktivem Bein: 0,25 / 0,5 / 0,75 / 1,0 % (IQ-Positionslimit 1 % eingehalten).
ZIEL: hoechster Median-Ertrag nach 252 Tagen unter P(Bruch) <= 5 %. Bruch TTP: Tagestief < -3 %
  oder Tief < Hoechststand - 7 %; IQ: Tief < Hoechststand - 6 %. Ein Bruch beendet den Pfad.
MC: Block-Bootstrap der Tagesvektoren (P&L + Intraday-Tief je Bein), Bloecke 10 Tage, gemeinsam,
  2000 Pfade, additiv (wie FK). WALK-FORWARD verankert: IS 2016-07..Y-1 -> Wahl -> OOS-Jahr Y.
Intraday-Tief ORB: Basis = Verlust des Verlierers (Gewinner 0); konservativ: jeder ORB-Trade -1R.
VORBELASTET: K60-Regel nach Sicht auf alle Perioden gewaehlt; O2 an 10/25-09/26 angepasst ->
  zusaetzlich die beste Wahl OHNE O2. Ergebnis nur fuer den Forward (kein Bot, keine Bridge).
LOCK challenge_k60_orb_oel_gewichtung_20261016, Forward 2026-10-19 .. 2027-03-31.

  python scripts/research_challenge_k60_orb_gewichtung.py optimise
  python scripts/research_challenge_k60_orb_gewichtung.py check
  python scripts/research_challenge_k60_orb_gewichtung.py register
  python scripts/research_challenge_k60_orb_gewichtung.py evaluate      # ab 2027-03-31
"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).resolve().parent))

from research_lock import Lock  # noqa: E402
from research_noise_area_k60_sltp import PERIODS, entries  # noqa: E402
from research_noise_area_k60_ttp import COST, EXITS, trades  # noqa: E402
from research_orb_oel_filter import RES, apply, load  # noqa: E402

STRATEGY = "challenge_k60_orb_oel_gewichtung_20261016"
FORWARD_START, EVAL_DATE = "2026-10-19", "2027-03-31"
OUT = ROOT / "noise_area_momentum" / "results"
CACHE = OUT / "challenge_gewichtung_trades.pkl"
CHALLENGES = {"TTP": {"daily": 0.03, "dd": 0.07, "target": 0.10}, "IQ": {"daily": None, "dd": 0.06, "target": 0.08}}
RISKS = [0.25, 0.5, 0.75, 1.0]
K60_OPTS, ORB_OPTS, CAPS = ["aus", "sl1", "ohne_stop"], ["aus", "O1", "O2"], [1, 2, 3]
N_PATHS, HORIZON, BLOCK, P_MAX = 2000, 252, 10, 0.05
WF_YEARS = list(range(2021, 2027))
DATA_START, DATA_END = "2016-07-28", "2026-09-30"


# ------------------------------------------------------------------ Trade-Tabellen
def build_trades(refresh: bool = False) -> tuple[dict, pd.DatetimeIndex]:
    """Je Bein-Variante: date, minute (nach 09:30), pnl/low/cost je 1 % Risiko."""
    if CACHE.exists() and not refresh:
        obj = pd.read_pickle(CACHE)
        return obj["legs"], obj["days"]
    t, g = entries()
    legs = {}
    for name, sl in (("k60_sl1", 1.0), ("k60_ohne_stop", None)):
        tr = trades(t, g, EXITS["15:55"], sl_sigma=sl)
        legs[name] = pd.DataFrame({"date": tr.index, "minute": tr["bar"].to_numpy(),
                                   "pnl": (tr["lev"] * tr["ret"]).to_numpy(), "low": (tr["lev"] * tr["mae"]).to_numpy(),
                                   "cost": (tr["lev"] * COST).to_numpy()})
    data = load(DATA_END)
    sels = {"O1": json.loads((RES / "oel_filter_is_selection.json").read_text(encoding="utf-8"))["winners"],
            "O2": json.loads((RES / "oel_filter_fit2026_selection.json").read_text(encoding="utf-8"))["winners"]}
    for opt, sel in sels.items():
        for inst in ("SP500", "NASDAQ"):
            r, c = apply(data[inst], sel[inst])
            et = r.index.tz_convert("America/New_York") if r.index.tz is not None else r.index
            legs[f"orb_{inst}_{opt}"] = pd.DataFrame({
                "date": et.tz_localize(None).normalize(), "minute": (et.hour * 60 + et.minute - 570).to_numpy(),
                "pnl": r.to_numpy() * 0.01, "low": np.minimum(r.to_numpy(), 0) * 0.01,
                "low_kons": np.minimum(np.minimum(r.to_numpy(), 0), -1.0) * 0.01, "cost": c.to_numpy() * 0.01})
    days = g["dates"]
    pd.to_pickle({"legs": legs, "days": days}, CACHE)
    return legs, days


def structures():
    for k, s, n, cap in itertools.product(K60_OPTS, ORB_OPTS, ORB_OPTS, CAPS):
        active = ([f"k60_{k}"] if k != "aus" else []) + ([f"orb_SP500_{s}"] if s != "aus" else []) \
            + ([f"orb_NASDAQ_{n}"] if n != "aus" else [])
        if active:
            yield {"k60": k, "sp500": s, "nasdaq": n, "cap": cap}, active


def daily_after_cap(legs: dict, active: list, cap: int, days: pd.DatetimeIndex, kons: bool = False,
                    cost_mult: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    """(P, L): Tage x Beine, je 1 % Risiko, nach Tagesdeckel."""
    rows = []
    for i, leg in enumerate(active):
        x = legs[leg]
        low = x["low_kons"] if (kons and "low_kons" in x) else x["low"]
        rows.append(pd.DataFrame({"date": x["date"], "minute": x["minute"], "leg": i,
                                  "pnl": x["pnl"] - (cost_mult - 1) * x["cost"], "low": low}))
    t = pd.concat(rows).sort_values(["date", "minute", "leg"])
    t = t[t.groupby("date").cumcount() < cap]
    pos = pd.Index(days).get_indexer(t["date"])
    t = t[pos >= 0]; pos = pos[pos >= 0]
    P, L = np.zeros((len(days), len(active))), np.zeros((len(days), len(active)))
    np.add.at(P, (pos, t["leg"].to_numpy()), t["pnl"].to_numpy())
    np.add.at(L, (pos, t["leg"].to_numpy()), t["low"].to_numpy())
    return P, L


# ------------------------------------------------------------------ Monte Carlo
def boot_index(n_days: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    nb = HORIZON // BLOCK + 1
    starts = rng.integers(0, n_days - BLOCK, size=(N_PATHS, nb))
    return (starts[:, :, None] + np.arange(BLOCK)).reshape(N_PATHS, -1)[:, :HORIZON]


def mc_eval(Pb: np.ndarray, Lb: np.ndarray, w: np.ndarray, rule: dict) -> dict:
    """Pb/Lb: Pfade x Tage x Beine (je 1 %), w: Risiko in % je Bein."""
    daily = Pb @ w
    low = Lb @ w
    cum = np.cumsum(daily, axis=1)
    prev = np.concatenate([np.zeros((cum.shape[0], 1)), cum[:, :-1]], axis=1)
    peak_prev = np.maximum.accumulate(np.maximum(prev, 0), axis=1)
    trough = prev + np.minimum(low, 0)
    br = trough < peak_prev - rule["dd"]
    if rule["daily"]:
        br |= low < -rule["daily"]
    first_br = np.where(br.any(1), br.argmax(1), HORIZON)
    hit = cum >= rule["target"]
    first_hit = np.where(hit.any(1), hit.argmax(1), HORIZON)
    end = np.where(first_br < HORIZON, cum[np.arange(len(cum)), np.minimum(first_br, HORIZON - 1)], cum[:, -1])
    return {"median_%": float(np.median(end)) * 100, "p_bruch": float((first_br < HORIZON).mean()),
            "p_ziel": float((first_hit < first_br).mean()),
            "median_tage_ziel": float(np.median(first_hit[first_hit < first_br])) if (first_hit < first_br).any() else np.nan}


def optimise_window(legs, days, mask, rule, seed=7, kons=False, allow_o2=True):
    idx_days = np.where(mask)[0]
    B = boot_index(len(idx_days), seed)
    best, rows = None, []
    for st, active in structures():
        if not allow_o2 and "O2" in (st["sp500"], st["nasdaq"]):
            continue
        P, L = daily_after_cap(legs, active, st["cap"], days, kons=kons)
        P, L = P[idx_days][B], L[idx_days][B]
        for ws in itertools.product(RISKS, repeat=len(active)):
            w = np.array(ws)                  # Risiko in %: P ist je 1 % Risiko -> 0,25 % = Faktor 0,25
            m = mc_eval(P, L, w, rule)
            row = {**st, **{f"r_{a}": r for a, r in zip(active, ws)}, **m}
            rows.append(row)
            if m["p_bruch"] <= P_MAX and (best is None or m["median_%"] > best["median_%"]):
                best = row
    return best, pd.DataFrame(rows)


def _w_of(row: dict, active: list) -> np.ndarray:
    return np.array([row.get(f"r_{a}", 0.0) for a in active])


def _active(st: dict) -> list:
    return ([f"k60_{st['k60']}"] if st["k60"] != "aus" else []) + \
        ([f"orb_SP500_{st['sp500']}"] if st["sp500"] != "aus" else []) + \
        ([f"orb_NASDAQ_{st['nasdaq']}"] if st["nasdaq"] != "aus" else [])


def lock() -> Lock:
    lk = Lock(STRATEGY)
    lk.register_split(DATA_START, "2025-09-30", DATA_END)
    return lk


def label(row) -> str:
    st = {k: row[k] for k in ("k60", "sp500", "nasdaq", "cap")}
    parts = [f"{a.replace('orb_', 'ORB ').replace('k60_', 'K60 ')} {row[f'r_{a}']:.2f}%" for a in _active(st)]
    return " + ".join(parts) + f" | max {int(row['cap'])}/Tag"


def stage_optimise() -> None:
    lk = lock()
    n_per = sum(len(RISKS) ** len(a) for _, a in structures())
    if lk.trials == 0:
        lk.log_trials(n_per * len(CHALLENGES), note="Struktur x Risiko je Challenge (TTP, IQ), MC P(Bruch)<=5 %")
    legs, days = build_trades()
    full = (days >= DATA_START) & (days <= DATA_END)
    result = {}
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    for ch, rule in CHALLENGES.items():
        best, grid = optimise_window(legs, days, full, rule)
        grid.to_csv(OUT / f"challenge_gewichtung_grid_{ch}.csv", index=False)
        best_no2, _ = optimise_window(legs, days, full, rule, allow_o2=False)
        best_k, _ = optimise_window(legs, days, full, rule, kons=True)
        ok = grid[grid.p_bruch <= P_MAX].sort_values("median_%", ascending=False)
        print(f"\n===== {ch}: {len(ok)} von {len(grid)} mit P(Bruch) <= 5 % =====")
        print("Top 10:")
        for _, r in ok.head(10).iterrows():
            print(f"  {label(r):70s} median {r['median_%']:6.2f} %  P(Bruch) {r.p_bruch:5.3f}  "
                  f"P(Ziel) {r.p_ziel:5.3f}  Tage bis Ziel {r.median_tage_ziel}")
        print("Gewinner:", label(best))
        print("ohne O2: ", label(best_no2), f"median {best_no2['median_%']:.2f} %, P(Ziel) {best_no2['p_ziel']:.3f}")
        print("konservatives ORB-Tief (-1R):", label(best_k), f"median {best_k['median_%']:.2f} %")
        # Walk-Forward
        wf = []
        for y in WF_YEARS:
            b, _ = optimise_window(legs, days, (days >= DATA_START) & (days < f"{y}-01-01"), rule, seed=y)
            yy = (days >= f"{y}-01-01") & (days <= f"{y}-12-31")
            if b is None:
                wf.append({"jahr": y, "wahl": "keine zulaessige"}); continue
            st = {k: b[k] for k in ("k60", "sp500", "nasdaq", "cap")}
            P, L = daily_after_cap(legs, _active(st), int(st["cap"]), days)
            d = P[yy] @ _w_of(b, _active(st)); lo = L[yy] @ _w_of(b, _active(st))
            cum = np.cumsum(d); prev = np.r_[0, cum[:-1]]
            dd = (prev + np.minimum(lo, 0) - np.maximum.accumulate(np.maximum(prev, 0))).min()
            wf.append({"jahr": y, "wahl": label(b), "ertrag_%": cum[-1] * 100, "maxdd_%": dd * 100,
                       "schlechtester_tag_%": lo.min() * 100})
        print("\nWalk-Forward (IS 2016-07..Y-1 -> OOS-Jahr Y):")
        print(pd.DataFrame(wf).round(2).to_string(index=False))
        pd.DataFrame(wf).to_csv(OUT / f"challenge_gewichtung_wf_{ch}.csv", index=False)
        result[ch] = {"gewinner": {k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in best.items()},
                      "ohne_o2": {k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in best_no2.items()},
                      "konservativ": label(best_k)}
    (OUT / "challenge_gewichtung_wahl.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")


# ------------------------------------------------------------------ Ereignis-Simulation
def event_sim(legs, days, row, rule, a, b, cost_mult=1.0) -> dict:
    st = {k: row[k] for k in ("k60", "sp500", "nasdaq", "cap")}
    act = _active(st)
    P, L = daily_after_cap(legs, act, int(st["cap"]), days, cost_mult=cost_mult)
    w = _w_of(row, act)
    m = (days >= a) & (days <= b)
    eq, peak, out_eq, breach, lows = 100_000.0, 100_000.0, [], None, []
    for i in np.where(m)[0]:
        prev = eq
        low = prev * (1 + min(L[i] @ w, 0))
        eq = prev * (1 + P[i] @ w)
        if breach is None and (low < peak * (1 - rule["dd"]) or (rule["daily"] and low < prev * (1 - rule["daily"]))):
            breach = days[i].strftime("%Y-%m-%d")
        lows.append(low / peak - 1)
        peak = max(peak, eq)
        out_eq.append(eq)
    e = pd.Series(out_eq, index=days[m])
    hit = e.index[e >= 100_000 * (1 + rule["target"])]
    return {"Endstand": round(e.iloc[-1]), "Rendite %": (e.iloc[-1] / 1e5 - 1) * 100,
            "MaxDD intraday %": min(lows) * 100, "erster Bruch": breach or "nie",
            "Ziel erreicht": hit[0].strftime("%Y-%m-%d") if len(hit) else "nein"}


def pass_rate(legs, days, row, rule, start="2016-07-28") -> dict:
    st = {k: row[k] for k in ("k60", "sp500", "nasdaq", "cap")}
    act = _active(st)
    P, L = daily_after_cap(legs, act, int(st["cap"]), days)
    w = _w_of(row, act)
    idx = np.where(days >= start)[0]
    res = []
    for s in idx[: len(idx) - HORIZON: 5]:
        d, lo = P[s:s + HORIZON] @ w, L[s:s + HORIZON] @ w
        cum = np.cumsum(d); prev = np.r_[0, cum[:-1]]
        br = prev + np.minimum(lo, 0) < np.maximum.accumulate(np.maximum(prev, 0)) - rule["dd"]
        if rule["daily"]:
            br |= lo < -rule["daily"]
        fb = br.argmax() if br.any() else HORIZON
        fh = (cum >= rule["target"]).argmax() if (cum >= rule["target"]).any() else HORIZON
        res.append("ok" if fh < fb else ("bruch" if fb < HORIZON else "offen"))
    s = pd.Series(res)
    return {"Starts": len(s), "bestanden %": (s == "ok").mean() * 100, "gebrochen %": (s == "bruch").mean() * 100}


def stage_check() -> None:
    legs, days = build_trades()
    wahl = json.loads((OUT / "challenge_gewichtung_wahl.json").read_text(encoding="utf-8"))
    pd.set_option("display.width", 250)
    for ch, rule in CHALLENGES.items():
        for tag in ("gewinner", "ohne_o2"):
            row = wahl[ch][tag]
            print(f"\n===== {ch} / {tag}: {label(row)} =====")
            out = {}
            for per, a, b in PERIODS:
                out[per] = event_sim(legs, days, row, rule, a, b)
                out[per + " Kosten x2"] = event_sim(legs, days, row, rule, a, b, cost_mult=2.0)
            print(pd.DataFrame(out).to_string())
            print("Bestehensquote alle Starts:", pass_rate(legs, days, row, rule),
                  "| ab 2023:", pass_rate(legs, days, row, rule, "2023-01-01"))


def stage_register() -> None:
    lk = lock()
    wahl = json.loads((OUT / "challenge_gewichtung_wahl.json").read_text(encoding="utf-8"))
    cfg = {ch: {"gewinner": label(wahl[ch]["gewinner"]), "ohne_o2": label(wahl[ch]["ohne_o2"]),
                "raw": wahl[ch]} for ch in CHALLENGES}
    h = lk.freeze(cfg)
    if "oos" not in lk._load()["unsealed"]:
        lk.unseal("oos", h)        # formal; Historie vollstaendig gesehen
    if lk._load().get("forward") is None:
        lk.register_forward(FORWARD_START, EVAL_DATE, 10**6)
    print("eingefroren", h[:12], "| Forward", FORWARD_START, "->", EVAL_DATE)
    for ch in CHALLENGES:
        print(ch, "Gewinner:", cfg[ch]["gewinner"], "| ohne O2:", cfg[ch]["ohne_o2"])


def stage_evaluate() -> None:
    lk = lock()
    lk.unseal("forward", lk._load()["frozen"]["hash"])
    print("Forward offen. Trade-Tabellen mit Daten bis", EVAL_DATE, "neu bauen (DATA_END anheben, "
          "build_trades(refresh=True)) und event_sim() ab", FORWARD_START, "fuer die eingefrorenen Wahlen rechnen.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    {"optimise": stage_optimise, "check": stage_check, "register": stage_register,
     "evaluate": stage_evaluate}[sys.argv[1]]()
