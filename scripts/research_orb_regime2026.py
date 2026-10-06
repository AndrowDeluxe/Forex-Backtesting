"""ORB im neuen Regime: IS = der Bruch (10/2025-03/2026), 9 Punkte je Index.

Nutzerauftrag 2026-10-06 (Plan: ~/.claude/plans/sprightly-bubbling-karp.md):
ORB unabhaengig von der Mentor-PDF neu aufbauen, IS = der Zeitraum des Bruchs,
mit den Moeglichkeiten aus der Research und dem N-ten Ausbruch.

SPLIT (Lock ny_open_orb_regime2026_20261006, unveraenderlich):
  IS      2025-10-01 .. 2026-03-31
  OOS     2026-04-01 .. 2026-06-30
  Tresor  2026-07-01 .. 2026-09-30   VORBELASTET (Diagnose kennt 2026)
  Forward ab 2026-10-05 = echter blinder Test; oeffnen bei >= 100 Trades je
          Index oder am 31.03.2027.

SUCHRAUM je Index (9 optimierte Punkte = Richtwert-Grenze):
  1 Einstiegsart  first / nth_same 2 / nth_same 3 / after_fail / fade / retest
  2 Richtung      long / short / beide
  3 Trendfilter   kein / Ribbon neutral / Ribbon mit Trend   (Diagnose 06.10.)
  4 Eroeffnung    kein / grosser Gap / grosses Eroeffnungsvolumen (Gao 2018,
                  Zarattini 2024); "gross" = ueber dem 67-%-Quantil der
                  vorangegangenen 60 Sessions (nur Vergangenheit)
  5 Stop          0,6 / 0,8 / 1,0 / 1,5 x M15-ATR
  6 Ziel          1R (Ladia: 1:1) / 2R / 4R / ohne (Exit 16:00)
  7 Range         15 / 30 Min.
  8 Spaetester Einstieg  11:00 / 12:30 / 16:00 (Ladia: Edge frueh)
  9 Vola-Regime   kein / VIX-Vortag >= 20 / < 20 -- Ersatz fuer das
                  Dealer-Gamma-Regime (Dim/Eraker/Vilkov, Adams et al.,
                  SpotGamma), weil GEX-Historie fehlt
  Fest: kein Teilziel, kein Breakeven, Kosten wie bisher.

AUSWAHLREGEL (vor dem Lauf festgelegt, nur IS):
  1. >= 50 IS-Trades, PF > 1,3, beide IS-Haelften > 0
  2. Score = t-Wert, geglaettet ueber Stop-/Ziel-Nachbarn (Median)
  3. Gewinner = hoechster Score; Deflated Sharpe gegen die Versuchsanzahl
  CHECKPOINT: Gewinner gesammelt dem Nutzer vorlegen -- erst nach OK
  `--stage oos`.

  python scripts/research_orb_regime2026.py --stage grid
  python scripts/research_orb_regime2026.py --stage oos      # nach Nutzer-OK
  python scripts/research_orb_regime2026.py --stage tresor   # vorbelastet
"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import challenge_portfolio.paper_bot as pb  # noqa: E402
from ny_open_orb.data import fetch_vix_daily  # noqa: E402
from ny_open_orb.entries_nth import find_entries_nth  # noqa: E402
from research_lock import Lock, deflated_sharpe  # noqa: E402
from research_orb_cancel_at_sl_and_hold import ENTRY_SLIPPAGE_BPS, EXIT_SLIPPAGE_BPS, SPREAD_BPS  # noqa: E402
from research_orb_exit_grid_m1 import prepare, sim  # noqa: E402
from research_orb_is_only_7p import account, acc_stats  # noqa: E402
from research_orb_is_only_reopt import LIVE, allowed_for, load, metrics, run_config  # noqa: E402

STRATEGY = "ny_open_orb_regime2026_20261006"
IS_START, IS_END, OOS_END, TRESOR_END = "2025-10-01", "2026-03-31", "2026-06-30", "2026-09-30"
INSTRUMENTS = ("SP500", "NASDAQ")
RES = Path(__file__).resolve().parents[1] / "ny_open_orb" / "results"

MODES = [("first", 1), ("nth_same", 2), ("nth_same", 3), ("after_fail", 1), ("fade", 1), ("retest", 1)]
DIRS = ("long", "short", "beide")
RIBBON = ("kein", "neutral", "mit_trend")
OPEN_F = ("kein", "gap_gross", "vol_gross")
STOPS = [0.6, 0.8, 1.0, 1.5]
TARGETS = [1.0, 2.0, 4.0, None]
RANGES = (1, 2)
CUTOFFS = ("11:00", "12:30", "16:00")
VIX_F = ("kein", "vix_hoch", "vix_tief")
VIX_LEVEL = 20.0


def lock() -> Lock:
    lk = Lock(STRATEGY)
    lk.register_split(IS_START, IS_END, OOS_END, TRESOR_END)
    lk.register_forward("2026-10-05", "2027-03-31", 100)
    return lk


def session_features(frame: pd.DataFrame, vix: pd.Series) -> pd.DataFrame:
    """Je Session: Gap/ATR, Eroeffnungsvolumen-Verhaeltnis, VIX Vortag -- und
    die Flags "gross" aus dem 67-%-Quantil der vorangegangenen 60 Sessions."""
    f = frame.copy()
    f["date"] = f.index.tz_localize(None).normalize()
    mins = f.index.hour * 60 + f.index.minute
    rth = f[(mins >= 570) & (mins < 960)]
    g = rth.groupby("date")
    op = g["open"].first()
    cl = g["close"].last()
    first15 = rth[(rth.index.hour * 60 + rth.index.minute) < 585].groupby("date")["volume"].sum()
    atr = f.groupby("date")["atr"].first()
    feat = pd.DataFrame({"open": op, "close": cl, "vol15": first15, "atr": atr})
    feat["gap_atr"] = (feat["open"] - feat["close"].shift(1)).abs() / feat["atr"]
    feat["vol_ratio"] = feat["vol15"] / feat["vol15"].shift(1).rolling(20, min_periods=10).mean()
    for col, flag in (("gap_atr", "gap_gross"), ("vol_ratio", "vol_gross")):
        thr = feat[col].shift(1).rolling(60, min_periods=30).quantile(0.67)
        feat[flag] = feat[col] > thr
    v = vix.copy()
    v.index = pd.DatetimeIndex(v.index).tz_localize(None) if getattr(v.index, "tz", None) else pd.DatetimeIndex(v.index)
    feat["vix_prev"] = v.reindex(feat.index, method="ffill").shift(1)
    return feat


def _naive(ts) -> pd.Timestamp:
    ts = pd.Timestamp(ts)
    return (ts.tz_localize(None) if ts.tz is not None else ts).normalize()


def day_mask(feat: pd.DataFrame, open_f: str, vix_f: str) -> set:
    m = pd.Series(True, index=feat.index)
    if open_f != "kein":
        m &= feat[open_f].fillna(False)
    if vix_f == "vix_hoch":
        m &= feat["vix_prev"] >= VIX_LEVEL
    elif vix_f == "vix_tief":
        m &= feat["vix_prev"] < VIX_LEVEL
    return set(feat.index[m.fillna(False).astype(bool)])


def series_for(frames, sessions, bias, feat, inst, cfg):
    """Trade-Reihe (R) und Kosten (R) einer Konfiguration, alle Daten im Frame."""
    frame = frames[cfg["range_bars"]]
    allowed = allowed_for(sessions, bias, cfg["dirs"], cfg["ribbon"])
    ok_days = day_mask(feat, cfg["open_f"], cfg["vix_f"])
    allowed = {s: (d if _naive(s) in ok_days else []) for s, d in allowed.items()}
    ent = find_entries_nth(frame, allowed, cfg["mode"], n=cfg["n"], cutoff=cfg["cutoff"])
    prep = prepare(frame, ent)
    res = sim(prep, inst, cfg["stop"], cfg["target"], None)
    if res.empty:
        return pd.Series(dtype=float), pd.Series(dtype=float)
    idx = pd.DatetimeIndex(res["entry_time"])
    by_t = {p["t"]: p for p in prep}
    cost_bps = (SPREAD_BPS[inst] + ENTRY_SLIPPAGE_BPS + EXIT_SLIPPAGE_BPS) / 10_000
    r = pd.Series(res["r"].to_numpy(), index=idx).sort_index()
    c = pd.Series([by_t[t]["level"] * cost_bps / (cfg["stop"] * by_t[t]["atr"]) for t in res["entry_time"]],
                  index=idx).sort_index()
    return r, c


def load_all(inst, end):
    frames, sessions, bias = load(inst, end)
    vix = pb._retry(lambda: fetch_vix_daily("2016-07-28", end), attempts=3, delay_seconds=5, timeout_seconds=300)
    feat = session_features(frames[1], vix)
    return frames, sessions, bias, feat


# ---------------------------------------------------------------------------
def stage_grid() -> int:
    lk = lock()
    st = json.loads(lk.path.read_text(encoding="utf-8"))
    rows, n_trials, sr_var = [], {}, {}
    for inst in INSTRUMENTS:
        frames, sessions, bias, feat = load_all(inst, IS_END)       # Sperre: nur bis IS-Ende geladen
        is_frames = {k: lk.is_only(v) for k, v in frames.items()}   # Einstiege nur im IS suchen
        masks = {(o, v): day_mask(feat, o, v) for o in OPEN_F for v in VIX_F}
        cost_bps = (SPREAD_BPS[inst] + ENTRY_SLIPPAGE_BPS + EXIT_SLIPPAGE_BPS) / 10_000
        count = 0
        for (mode, n), rb, dirs, rib, cutoff in itertools.product(MODES, RANGES, DIRS, RIBBON, CUTOFFS):
            frame = is_frames[rb]
            allowed = allowed_for(sessions, bias, dirs, rib)
            ent = find_entries_nth(frame, allowed, mode, n=n, cutoff=cutoff)
            prep = prepare(frame, ent)
            day_of = pd.DatetimeIndex([p["t"] for p in prep]).tz_localize(None).normalize() if prep else pd.DatetimeIndex([])
            for stop, target in itertools.product(STOPS, TARGETS):
                res = sim(prep, inst, stop, target, None)
                for o, v in itertools.product(OPEN_F, VIX_F):
                    count += 1
                    if res.empty:
                        continue
                    keep_t = {p["t"] for p, d in zip(prep, day_of) if d in masks[(o, v)]}
                    sub = res[res["entry_time"].isin(keep_t)]
                    if len(sub) < 2:
                        continue
                    r = pd.Series(sub["r"].to_numpy(), index=pd.DatetimeIndex(sub["entry_time"])).sort_index()
                    m = metrics(r)
                    rows.append({"inst": inst, "mode": mode, "n_brk": n, "range_bars": rb, "dirs": dirs, "ribbon": rib,
                                 "cutoff": cutoff, "stop": stop, "target": target, "open_f": o, "vix_f": v,
                                 **{k: m.get(k) for k in ("n", "avg", "std", "t", "pf", "sum", "dd", "h1", "h2", "win")}})
            print(f"  {inst} {mode}{n} rb{rb} {dirs} {rib} {cutoff}: fertig", flush=True)
        n_trials[inst] = count
        if st["trials"] == 0:            # bei Wiederholung nicht doppelt zaehlen
            lk.log_trials(count, note=f"{inst}: Regime-2026-Gitter (9 Punkte)")
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "regime2026_grid.csv", index=False)

    grid["eligible"] = (grid.n >= 50) & (grid.pf > 1.3) & (grid.h1 > 0) & (grid.h2 > 0)
    grid["target_k"] = grid.target.fillna(-1)
    keys = ["inst", "mode", "n_brk", "range_bars", "dirs", "ribbon", "cutoff", "open_f", "vix_f", "stop", "target_k"]
    t_lookup = grid.set_index(keys)["t"].to_dict()
    tk = sorted([t for t in TARGETS if t is not None]) + [-1]

    def smooth(row):
        si, ti = STOPS.index(row.stop), tk.index(row.target_k)
        vals = []
        for ds, dt in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
            a, b = si + ds, ti + dt
            if 0 <= a < len(STOPS) and 0 <= b < len(tk):
                v = t_lookup.get((row.inst, row["mode"], row.n_brk, row.range_bars, row.dirs, row.ribbon, row.cutoff,
                                  row.open_f, row.vix_f, STOPS[a], tk[b]))
                if v is not None and not pd.isna(v):
                    vals.append(v)
        return float(np.median(vals)) if vals else np.nan

    winners = {}
    for inst in INSTRUMENTS:
        g = grid[grid.inst == inst]
        gg = g[g.n >= 20]
        sr_var[inst] = float((gg["avg"] / gg["std"]).var())
        el = g[g.eligible].copy()
        print(f"\n{inst}: {len(el)} von {n_trials[inst]} Varianten erfuellen die Mindestbedingungen")
        if el.empty:
            winners[inst] = None
            continue
        el["t_smooth"] = el.apply(smooth, axis=1)
        el = el.sort_values("t_smooth", ascending=False)
        cols = ["mode", "n_brk", "range_bars", "dirs", "ribbon", "cutoff", "open_f", "vix_f", "stop", "target", "n", "avg",
                "pf", "t", "t_smooth", "win"]
        print(el.head(12)[cols].round(3).to_string(index=False))
        w = el.iloc[0]
        winners[inst] = {"mode": w["mode"], "n": int(w.n_brk), "range_bars": int(w.range_bars), "dirs": w.dirs,
                         "ribbon": w.ribbon, "weekday": None, "cutoff": w.cutoff, "open_f": w.open_f, "vix_f": w.vix_f,
                         "stop": float(w.stop), "target": None if w.target_k == -1 else float(w.target)}
        dsr = deflated_sharpe(w["avg"] / w["std"], int(w.n), n_trials[inst], 0.0, 3.0, sr_var[inst])
        winners[inst]["_is"] = {"n": int(w.n), "pf": float(w.pf), "avg": float(w["avg"]), "t": float(w.t),
                                "win": float(w.win), "dsr_skew0": dsr}
        # Haeufigkeit je Modus unter den 50 besten
        print("Modus-Verteilung Top 50:", el.head(50)["mode"].value_counts().to_dict())
    (RES / "regime2026_selection.json").write_text(json.dumps({"winners": winners, "n_trials": n_trials,
                                                               "sr_var_trials": sr_var}, indent=2, default=str),
                                                   encoding="utf-8")
    print("\nCHECKPOINT: Auswahl gespeichert, NICHT eingefroren -> erst Nutzer-OK, dann --stage oos")
    return 0


def evaluate(stage: str) -> int:
    lk = lock()
    sel = json.loads((RES / "regime2026_selection.json").read_text(encoding="utf-8"))
    winners = {k: ({kk: vv for kk, vv in v.items() if not kk.startswith("_")} if v else None)
               for k, v in sel["winners"].items()}
    h = lk.freeze(winners)
    st = json.loads(lk.path.read_text(encoding="utf-8"))
    if stage not in st["unsealed"]:
        print(f"{stage} geoeffnet:", lk.unseal(stage, h))
    end = OOS_END if stage == "oos" else TRESOR_END
    parts = ["IS", "OOS"] + (["Tresor"] if stage == "tresor" else [])
    sl = {"IS": lk.is_only, "OOS": lambda x: lk.stage_slice(x, "oos"), "Tresor": lambda x: lk.stage_slice(x, "tresor")}
    rows, trades = [], []
    for inst in INSTRUMENTS:
        if not winners.get(inst):
            continue
        frames, sessions, bias, feat = load_all(inst, end)
        r, c = series_for(frames, sessions, bias, feat, inst, winners[inst])
        lr, lc = run_config(frames, sessions, bias, inst, LIVE[inst])
        for label, rr, cc in (("neu", r, c), ("live", lr, lc)):
            rr = rr[rr.index >= pd.Timestamp(IS_START, tz=rr.index.tz)]
            cc = cc.reindex(rr.index)
            trades.append(pd.DataFrame({"inst": inst, "variant": label, "time": rr.index, "r": rr.values,
                                        "cost_r": cc.values}))
            for p in parts:
                rows.append({"inst": inst, "variant": label, "part": p, **metrics(sl[p](rr), sl[p](cc))})
    rep = pd.DataFrame(rows)
    tr = pd.concat(trades)
    rep.to_csv(RES / f"regime2026_report_{stage}.csv", index=False)
    tr.to_csv(RES / f"regime2026_trades_{stage}.csv", index=False)
    pd.set_option("display.width", 250)
    print(rep.round(3).to_string(index=False))
    t = tr[tr.variant == "neu"].copy()
    t["time"] = pd.to_datetime(t["time"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    t = t.set_index("time").sort_index()
    acc_rows = []
    for name, lo, hi in (("OOS 04-06/2026", "2026-04-01", "2026-06-30"), ("Tresor 07-09/2026", "2026-07-01", "2026-09-30")):
        if name.startswith("Tresor") and stage != "tresor":
            continue
        sub = t[(t.index >= lo) & (t.index < pd.Timestamp(hi) + pd.Timedelta(days=1))]
        if len(sub):
            acc_rows.append({"zeitraum": name, **acc_stats(account(sub))})
    if acc_rows:
        acc = pd.DataFrame(acc_rows)
        acc.to_csv(RES / f"regime2026_account_{stage}.csv", index=False)
        print("\n100k-Konto, 1 % vom Kontostand:\n", acc.round(4).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    stage = sys.argv[sys.argv.index("--stage") + 1]
    sys.exit(stage_grid() if stage == "grid" else evaluate(stage))
