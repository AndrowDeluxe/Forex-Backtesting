"""Oel als Filter fuer die IS-only-ORB (Nutzerauftrag 2026-10-12).

Vorgeschichte: research_orb_oel_vergleich.py (11.10.) -- Oel-Aktien-Korrelation
kippt im Tresor ins Negative, Tag-zu-Tag-Verhalten dreht marktweit zu
Fortsetzung, der Trendfilter "nur neutrale Tage" kippt bei den Indizes.

Basis (eingefroren, unveraendert): IS-only-7p-Gewinner
(is_only_7p_selection.json): SP500 beide/neutral, NASDAQ long/neutral, Stop
1,0 ATR, Ziel 8R, Exit 16:00. "Trend-Modus" = dieselbe Config mit
ribbon="mit_trend". Neutrale und Trend-Tage sind disjunkt (Ribbon 0 vs +-1),
deshalb werden beide Trade-Listen einmal simuliert; ein Filter waehlt nur
noch je Sitzung aus, welche Liste gilt.

Oel-Merkmale (alle vor 09:45 NY bekannt):
  K_w     rollende Korrelation Sitzungsrendite Oel <-> Index, w Tage, bis Vortag
  A_oel_w rollende Autokorrelation der Oel-Sitzungsrenditen, bis Vortag
  A_komb_w Mittel aus A_oel_w und der Index-Autokorrelation
  s_move  Oel-Rendite 09:00 -> 09:45 am selben Tag (Index-Range schliesst 09:45)
Regime: K < Schwelle (gegenlaeufig) bzw. A > Schwelle (Fortsetzung).
Aktion im Regime: skip (Tag aus), trend (Trend-Tage statt neutrale), alle
(neutrale + Trend-Tage). S-Filter: Trade nur, wenn Oel gleich-/gegenlaeufig
zur Ausbruchsrichtung lief (mit Mindestbewegung).

OPTION 1 -- Lock orb_oel_filter_is_20261012 (Overfitting-Sperre)
  8 vorab feste Varianten je Index: K20/K40 x {skip, trend}, A_oel60/A_komb60
  trend, S gleich/gegen. Auswahl nur auf IS (2016-07-28..2022-12-31):
  n >= 100, PF > 1,3, beide Haelften > 0, Oe R > Basis; davon hoechster t.
  OOS einmal, Tresor einmal (VORBELASTET: der Oel-Kipp 2026 ist bekannt),
  Forward ab 2026-10-12, Stichtag 2027-03-31.
OPTION 2 -- Lock orb_oel_filter_fit2026_20261012 (EXPLORATIV, KEIN BELEG)
  Breites Gitter, optimiert NUR auf 10/2025-09/2026 (n >= 50, hoechster t).
  Ausgewiesen: Deflated Sharpe ueber alle Versuche + dieselbe Regel auf
  2016-09/2025. Gewinner eingefroren, Forward ab 2026-10-12 (Nutzerentscheid).
  Split formal: "IS" = 10/2025-09/2026, "OOS" = 01.-11.10.2026 (leer, nur
  damit der Forward nach Lock-Regel geoeffnet werden darf).

  python scripts/research_orb_oel_filter.py --stage is-select
  python scripts/research_orb_oel_filter.py --stage is-open
  python scripts/research_orb_oel_filter.py --stage fit2026
  python scripts/research_orb_oel_filter.py --stage forward-evaluate   # ab 2027-03-31
"""
import argparse
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import challenge_portfolio.paper_bot as pb  # noqa: E402
from ny_open_orb import regime  # noqa: E402
from ny_open_orb.data import fetch_m1, fetch_m15  # noqa: E402
from ny_open_orb.engine import build_frame  # noqa: E402
from research_lock import Lock, deflated_sharpe  # noqa: E402
from research_orb_cancel_at_sl_and_hold import (  # noqa: E402
    ENTRY_SLIPPAGE_BPS, EXIT_SLIPPAGE_BPS, SPREAD_BPS, find_live_entries,
)
from research_orb_exit_grid_m1 import prepare, sim  # noqa: E402
from research_orb_is_only_reopt import IS_END, IS_START, OOS_END, TRESOR_END, allowed_for, metrics  # noqa: E402
from research_orb_oel_vergleich import session_points, set_clock  # noqa: E402

RES = ROOT / "ny_open_orb" / "results"
INSTRUMENTS = ("SP500", "NASDAQ")
SEL = json.loads((RES / "is_only_7p_selection.json").read_text(encoding="utf-8"))["winners"]
LOCK_IS, LOCK_FIT = "orb_oel_filter_is_20261012", "orb_oel_filter_fit2026_20261012"
FORWARD_START, EVAL_DATE = "2026-10-12", "2027-03-31"
FIT_START, FIT_END = "2025-10-01", "2026-09-30"
BACK_END = "2025-09-30"
MIN_OIL = 10.0

BASE = {"fam": "base", "w": None, "thr": None, "action": None, "s": None, "smin": 0.0}
OPTION1 = [
    {**BASE, "fam": "K", "w": 20, "thr": 0.0, "action": "skip"},
    {**BASE, "fam": "K", "w": 40, "thr": 0.0, "action": "skip"},
    {**BASE, "fam": "K", "w": 20, "thr": 0.0, "action": "trend"},
    {**BASE, "fam": "K", "w": 40, "thr": 0.0, "action": "trend"},
    {**BASE, "fam": "A_oel", "w": 60, "thr": 0.0, "action": "trend"},
    {**BASE, "fam": "A_komb", "w": 60, "thr": 0.0, "action": "trend"},
    {**BASE, "s": "gleich"},
    {**BASE, "s": "gegen"},
]
WINDOWS = {"K": (10, 20, 40, 60), "A_oel": (20, 40, 60, 120), "A_komb": (20, 40, 60, 120)}


def option2_grid() -> list[dict]:
    s_opts = [(None, 0.0)] + [(s, m) for s in ("gleich", "gegen") for m in (0.0, 0.001, 0.002)]
    out = [{**BASE, "s": s, "smin": m} for s, m in s_opts[1:]]
    for fam, ws in WINDOWS.items():
        for w, thr, act, (s, m) in itertools.product(ws, (-0.2, 0.0, 0.2), ("skip", "trend", "alle"), s_opts):
            out.append({"fam": fam, "w": w, "thr": thr, "action": act, "s": s, "smin": m})
    return out


def label(spec: dict) -> str:
    if spec["fam"] == "base":
        core = "Basis"
    else:
        op = "<" if spec["fam"] == "K" else ">"
        core = f"{spec['fam']}{spec['w']} {op} {spec['thr']:+.1f} -> {spec['action']}"
    if spec["s"]:
        core += f" | Oel {spec['s']}" + (f" >{spec['smin'] * 100:.1f}%" if spec["smin"] else "")
    return core


# ------------------------------------------------------------------ Daten
def _sim_mode(frame, sessions, bias, inst, ribbon) -> pd.DataFrame:
    cfg = SEL[inst]
    allowed = allowed_for(sessions, bias, cfg["dirs"], ribbon)
    prep = prepare(frame, find_live_entries(frame, allowed, cfg["stop"], cfg["rule"]))
    res = sim(prep, inst, cfg["stop"], cfg["target"], cfg["partial"])
    by_t = {t["t"]: t for t in prep}
    bps = (SPREAD_BPS[inst] + ENTRY_SLIPPAGE_BPS + EXIT_SLIPPAGE_BPS) / 10_000
    res["d"] = [by_t[t]["d"] for t in res["entry_time"]]
    res["cost"] = [by_t[t]["level"] * bps / (cfg["stop"] * by_t[t]["atr"]) for t in res["entry_time"]]
    res["session"] = pd.DatetimeIndex(res["entry_time"]).normalize()
    res["mode"] = ribbon
    return res[["entry_time", "session", "d", "r", "cost", "mode"]]


def oil_move_0900_0945(m1: pd.DataFrame) -> pd.Series:
    """Oel 08:59-Bar-Schluss (= 09:00) -> 09:44-Bar-Schluss (= 09:45). Nur Bars < 09:45."""
    mins = m1.index.hour * 60 + m1.index.minute
    day = m1.index.normalize()
    a = m1["close"][mins == 9 * 60 - 1].groupby(day[mins == 9 * 60 - 1]).last()
    b = m1["close"][mins == 9 * 60 + 44].groupby(day[mins == 9 * 60 + 44]).last()
    mv = (b / a - 1).dropna()
    return mv[(a.reindex(mv.index) >= MIN_OIL)]


def load(end: str) -> dict:
    set_clock("index")
    oil_m1 = pb._retry(lambda: fetch_m1("OIL", IS_START, end), attempts=3, delay_seconds=5, timeout_seconds=3600)
    po = session_points(oil_m1, "index")
    po = po[po[["open", "close"]].min(axis=1) >= MIN_OIL]
    r_o = po["close"] / po["open"] - 1
    s_move = oil_move_0900_0945(oil_m1)
    out = {}
    for inst in INSTRUMENTS:
        m15 = pb._retry(lambda: fetch_m15(inst, IS_START, end), attempts=3, delay_seconds=5, timeout_seconds=600)
        m1 = pb._retry(lambda: fetch_m1(inst, IS_START, end), attempts=3, delay_seconds=5, timeout_seconds=1800)
        frame = build_frame(m15, m1, range_bars=SEL[inst]["range_bars"])
        sessions = pd.DatetimeIndex(frame["session"].dropna().unique())
        bias = regime.ema_trend_bias(m15, sessions)
        trades = pd.concat([_sim_mode(frame, sessions, bias, inst, rb) for rb in ("neutral", "mit_trend")], ignore_index=True)
        pi = session_points(m1, "index")
        r_i = pi["close"] / pi["open"] - 1
        d = pd.concat([r_o, r_i], axis=1, keys=["o", "i"]).dropna()
        f = pd.DataFrame(index=d.index)
        for w in WINDOWS["K"]:
            f[f"K_{w}"] = d["o"].rolling(w).corr(d["i"]).shift(1)
        for w in WINDOWS["A_oel"]:
            ao = d["o"].rolling(w).corr(d["o"].shift(1)).shift(1)
            ai = d["i"].rolling(w).corr(d["i"].shift(1)).shift(1)
            f[f"A_oel_{w}"], f[f"A_komb_{w}"] = ao, (ao + ai) / 2
        f["s_move"] = s_move.reindex(f.index)
        _assert_no_lookahead(d, f)
        out[inst] = {"trades": trades, "feats": f}
    return out


def _assert_no_lookahead(d: pd.DataFrame, f: pd.DataFrame) -> None:
    """K_20 am Tag t muss aus den 20 Tagen VOR t kommen."""
    t = len(d) // 2
    exp = d["o"].iloc[t - 20:t].corr(d["i"].iloc[t - 20:t])
    assert abs(f["K_20"].iloc[t] - exp) < 1e-9, "Lookahead in K_20"


# ------------------------------------------------------------------ Filter
def apply(data: dict, spec: dict) -> tuple[pd.Series, pd.Series]:
    tr, f = data["trades"], data["feats"]
    neu, trd = tr[tr["mode"] == "neutral"], tr[tr["mode"] == "mit_trend"]
    if spec["fam"] == "base":
        sel = neu
    else:
        x = f[f"{spec['fam']}_{spec['w']}"]
        reg = (x < spec["thr"]) if spec["fam"] == "K" else (x > spec["thr"])
        reg_days = set(reg[reg.fillna(False)].index)
        in_reg_n = neu["session"].isin(reg_days)
        in_reg_t = trd["session"].isin(reg_days)
        if spec["action"] == "skip":
            sel = neu[~in_reg_n]
        elif spec["action"] == "trend":
            sel = pd.concat([neu[~in_reg_n], trd[in_reg_t]])
        else:  # alle
            sel = pd.concat([neu, trd[in_reg_t]])
    if spec["s"]:
        mv = sel["session"].map(f["s_move"])
        x = sel["d"] * mv
        keep = (x > spec["smin"]) if spec["s"] == "gleich" else (x < -spec["smin"])
        sel = sel[keep.fillna(False)]
    sel = sel.sort_values("entry_time")
    idx = pd.DatetimeIndex(sel["entry_time"])
    return pd.Series(sel["r"].to_numpy(), index=idx), pd.Series(sel["cost"].to_numpy(), index=idx)


def window(r: pd.Series, a: str, b: str) -> pd.Series:
    t = r.index.tz_localize(None) if r.index.tz is not None else r.index
    return r[(t >= pd.Timestamp(a)) & (t < pd.Timestamp(b) + pd.Timedelta(days=1))]


def sr_stats(r: pd.Series) -> tuple[float, float, float]:
    return r.mean() / r.std(ddof=1), float(r.skew()), float(r.kurt() + 3)


# ------------------------------------------------------------------ Stufen
def lock_is() -> Lock:
    lk = Lock(LOCK_IS)
    lk.register_split(IS_START, IS_END, OOS_END, TRESOR_END)
    lk.register_forward(FORWARD_START, EVAL_DATE, 10**6)   # nur der Stichtag oeffnet
    return lk


def lock_fit() -> Lock:
    lk = Lock(LOCK_FIT)
    lk.register_split(FIT_START, FIT_END, "2026-10-11")
    lk.register_forward(FORWARD_START, EVAL_DATE, 10**6)
    return lk


def stage_is_select() -> int:
    lk = lock_is()
    if lk.trials == 0:
        lk.log_trials(len(OPTION1) * len(INSTRUMENTS), note="8 vorab feste Oel-Filter je Index (SP500, NASDAQ), nur IS")
    data = load(IS_END)   # Daten nur bis IS-Ende laden
    rows, winners, dsr = [], {}, {}
    for inst in INSTRUMENTS:
        base_r, base_c = apply(data[inst], BASE)
        base_m = metrics(lk.is_only(base_r), lk.is_only(base_c))
        rows.append({"instrument": inst, "variante": "Basis", **base_m})
        cand, srs = [], []
        for spec in OPTION1:
            r, c = apply(data[inst], spec)
            m = metrics(lk.is_only(r), lk.is_only(c))
            ok = m["n"] >= 100 and m.get("pf", 0) > 1.3 and m["h1"] > 0 and m["h2"] > 0 and m["avg"] > base_m["avg"]
            rows.append({"instrument": inst, "variante": label(spec), "erfuellt": ok, **m})
            srs.append(sr_stats(lk.is_only(r))[0])
            if ok:
                cand.append((m["t"], spec, lk.is_only(r)))
        if cand:
            t, spec, r = max(cand, key=lambda z: z[0])
            sr, sk, ku = sr_stats(r)
            winners[inst] = spec
            dsr[inst] = deflated_sharpe(sr, len(r), len(OPTION1), sk, ku, sr_var_trials=float(np.var(srs, ddof=1)))
        else:
            winners[inst] = None
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "oel_filter_is_grid.csv", index=False)
    out = {"winners": winners, "labels": {i: label(s) if s else None for i, s in winners.items()},
           "deflated_sharpe_is": dsr, "n_trials_je_index": len(OPTION1)}
    if any(winners.values()):
        out["hash"] = lk.freeze({"basis": "is_only_7p_selection.json", "winners": winners})
    (RES / "oel_filter_is_selection.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    pd.set_option("display.width", 200)
    print(grid[["instrument", "variante", "erfuellt", "n", "pf", "avg", "t", "sum", "h1", "h2"]].round(3).to_string(index=False))
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def _periods_table(data, specs: dict, periods) -> pd.DataFrame:
    rows = []
    for inst in INSTRUMENTS:
        for name, spec in specs[inst].items():
            if spec is None:
                continue
            r, c = apply(data[inst], spec)
            for per, a, b in periods:
                rows.append({"instrument": inst, "variante": name, "regel": label(spec), "periode": per,
                             **metrics(window(r, a, b), window(c, a, b))})
    return pd.DataFrame(rows)


def stage_is_open() -> int:
    lk = lock_is()
    sel = json.loads((RES / "oel_filter_is_selection.json").read_text(encoding="utf-8"))
    if "hash" not in sel:
        print("kein Kandidat in IS -- nichts zu oeffnen")
        return 0
    h = sel["hash"]
    state = lk._load()
    for stage in ("oos", "tresor"):
        if stage not in state["unsealed"]:
            lk.unseal(stage, h)
    data = load(TRESOR_END)
    specs = {i: {"Basis": BASE, "Oel-Filter (IS)": sel["winners"][i]} for i in INSTRUMENTS}
    periods = [("IS", IS_START, IS_END), ("OOS", "2023-01-01", OOS_END), ("Tresor (vorbelastet)", "2025-10-01", TRESOR_END)]
    tab = _periods_table(data, specs, periods)
    tab.to_csv(RES / "oel_filter_is_open.csv", index=False)
    pd.set_option("display.width", 200)
    print(tab[["instrument", "variante", "regel", "periode", "n", "pf", "avg", "t", "sum", "avg_cost_x2"]].round(3).to_string(index=False))
    return 0


def stage_fit2026() -> int:
    lk = lock_fit()
    grid_specs = option2_grid()
    if lk.trials == 0:
        lk.log_trials(len(grid_specs) * len(INSTRUMENTS), note="EXPLORATIV: Oel-Filtergitter, optimiert nur auf 10/2025-09/2026")
    data = load(TRESOR_END)
    rows, winners, dsr = [], {}, {}
    for inst in INSTRUMENTS:
        cand, srs = [], []
        for spec in [BASE] + grid_specs:
            r, c = apply(data[inst], spec)
            rf, cf = window(r, FIT_START, FIT_END), window(c, FIT_START, FIT_END)
            rb, cb = window(r, IS_START, BACK_END), window(c, IS_START, BACK_END)
            mf, mb = metrics(rf, cf), metrics(rb, cb)
            rows.append({"instrument": inst, "regel": label(spec),
                         **{f"fit_{k}": v for k, v in mf.items()}, **{f"rueck_{k}": v for k, v in mb.items()}})
            if spec is BASE or mf.get("n", 0) < 50:
                continue
            srs.append(sr_stats(rf)[0])
            cand.append((mf["t"], spec, rf))
        t, spec, rf = max(cand, key=lambda z: z[0])
        sr, sk, ku = sr_stats(rf)
        winners[inst] = spec
        dsr[inst] = deflated_sharpe(sr, len(rf), len(grid_specs), sk, ku, sr_var_trials=float(np.var(srs, ddof=1)))
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "oel_filter_fit2026_grid.csv", index=False)
    h = lk.freeze({"basis": "is_only_7p_selection.json", "winners": winners, "hinweis": "an 2026 angepasst, kein Beleg"})
    if "oos" not in lk._load()["unsealed"]:
        lk.unseal("oos", h)   # leeres Fenster 01.-11.10.; noetig, damit der Forward geoeffnet werden darf
    out = {"winners": winners, "labels": {i: label(s) for i, s in winners.items()}, "deflated_sharpe_fit": dsr,
           "n_trials_je_index": len(grid_specs), "hash": h, "hinweis": "EXPLORATIV -- an 2026 angepasst, kein Beleg"}
    (RES / "oel_filter_fit2026_selection.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    specs = {i: {"Basis": BASE, "2026-Fit": winners[i]} for i in INSTRUMENTS}
    periods = [("2016-22", IS_START, IS_END), ("2023-09/25", "2023-01-01", OOS_END), ("2026-Fit 10/25-09/26", FIT_START, FIT_END)]
    tab = _periods_table(data, specs, periods)
    tab.to_csv(RES / "oel_filter_fit2026_perioden.csv", index=False)
    pd.set_option("display.width", 220)
    for inst in INSTRUMENTS:
        g = grid[grid.instrument == inst].sort_values("fit_t", ascending=False)
        print(f"\n--- {inst}: Top 10 im 2026-Fit (n >= 50) ---")
        print(g[g.fit_n >= 50].head(10)[["regel", "fit_n", "fit_pf", "fit_avg", "fit_t", "fit_sum", "rueck_n", "rueck_pf", "rueck_avg", "rueck_sum"]].round(3).to_string(index=False))
    print("\n" + tab[["instrument", "variante", "regel", "periode", "n", "pf", "avg", "t", "sum"]].round(3).to_string(index=False))
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def stage_forward_evaluate() -> int:
    end = pd.Timestamp.today().strftime("%Y-%m-%d")
    sels = {}
    for lk, fn, key in ((lock_is(), "oel_filter_is_selection.json", "Oel-Filter (IS)"),
                        (lock_fit(), "oel_filter_fit2026_selection.json", "2026-Fit")):
        sel = json.loads((RES / fn).read_text(encoding="utf-8"))
        if "hash" not in sel:
            continue
        lk.unseal("forward", sel["hash"])   # bricht vor dem Stichtag ab
        sels[key] = sel["winners"]
    data = load(end)
    specs = {i: {"Basis": BASE, **{k: w[i] for k, w in sels.items()}} for i in INSTRUMENTS}
    tab = _periods_table(data, specs, [("Forward", FORWARD_START, end)])
    tab.to_csv(RES / f"oel_filter_forward_{end}.csv", index=False)
    print(tab.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["is-select", "is-open", "fit2026", "forward-evaluate"])
    st = ap.parse_args().stage
    raise SystemExit({"is-select": stage_is_select, "is-open": stage_is_open, "fit2026": stage_fit2026,
                      "forward-evaluate": stage_forward_evaluate}[st]())
