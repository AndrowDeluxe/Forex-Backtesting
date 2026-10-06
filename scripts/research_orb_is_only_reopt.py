"""ORB: Neuoptimierung NUR auf In-Sample, danach einmal OOS, einmal Tresor.

Nutzerauftrag 2026-10-05: Die Live-ORB-Konfiguration wurde ab Stage 2 direkt
auf OOS-Zahlen ausgewaehlt (Stage 3 "Alle Zahlen OOS", Stage 4a "OOS-only-Scan",
Exit-Gitter "IS und OOS positiv", Storno-Entscheid 04.10.). Dieser Lauf baut
die Strategie so nach, als waere sie nur auf IS optimiert worden -- unter der
neuen Overfitting-Sperre (research_lock.py, knowledge/areas/overfitting-sperre.md).

SPLIT (registriert, unveraenderlich):
  IS     2016-07-28 .. 2022-12-31   optimieren
  OOS    2023-01-01 .. 2025-09-30   einmal testen
  Tresor 2025-10-01 .. 2026-09-30   einmal oeffnen

SUCHRAUM (nur Dimensionen, die in die Live-Konfiguration eingeflossen sind):
  Richtung long/short/beide x HTF-Ribbon kein/neutral/mit Trend x Wochentag
  keiner/Mo..Fr raus x Storno keins/Gegenseite/am SL x Stop 0,4..1,0 ATR x
  Ziel ohne/3/4/6/8R x Teilziel ohne/2/3R x Range 15/30 Min.
  Fest: Stop-Breakout-Einstieg, Ausstieg 16:00, kein Breakeven.

AUSWAHLREGEL (vor dem Lauf festgelegt, nur IS):
  1. Mindestbedingungen: >= 100 IS-Trades, PF > 1,3, beide IS-Haelften > 0
     (Haelften nach Trade-Anzahl).
  2. Score = t-Wert (Ø R / Std R x sqrt(n)), geglaettet: Median aus Zelle und
     direkten Stop-/Ziel-Nachbarn derselben Konfiguration (Plateau statt Spitze).
  3. Gewinner = hoechster geglaetteter Score unter den Zellen mit (1).
     Kein Kandidat -> Bein "laut IS nicht handelbar".
  4. Deflated Sharpe gegen die gezaehlten Versuche je Instrument.

Daten: M1-Ausfuehrung, M15-Range/ATR, gemessene Spreads + Slippage, ohne
Tick-Korrektur (fuer alle Kandidaten gleich).

  python scripts/research_orb_is_only_reopt.py --stage grid      # nur IS-Daten geladen
  python scripts/research_orb_is_only_reopt.py --stage evaluate  # freeze -> OOS -> Tresor
"""
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
from ny_open_orb.engine import build_frame, simulate  # noqa: E402
from research_lock import Lock, config_hash, deflated_sharpe  # noqa: E402
from research_orb_cancel_at_sl_and_hold import (  # noqa: E402
    ENTRY_SLIPPAGE_BPS, EXIT_SLIPPAGE_BPS, SPREAD_BPS, find_live_entries,
)
from research_orb_exit_grid_m1 import prepare, sim  # noqa: E402

STRATEGY = "ny_open_orb_is_reopt_20261005"
IS_START, IS_END, OOS_END, TRESOR_END = "2016-07-28", "2022-12-31", "2025-09-30", "2026-09-30"
INSTRUMENTS = ("SP500", "NASDAQ", "US30")
RES = ROOT / "ny_open_orb" / "results"

DIRS = {"long": (1,), "short": (-1,), "beide": (1, -1)}
RIBBON = ("kein", "neutral", "mit_trend")
WEEKDAYS = (None, "Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
RULES = ("none", "opposite", "sl")
STOPS = [0.4, 0.5, 0.6, 0.8, 1.0]
TARGETS = [None, 3.0, 4.0, 6.0, 8.0]
PARTIALS = [None, 2.0, 3.0]
RANGES = (1, 2)   # range_bars: 15 / 30 Min.

LIVE = {   # Stand 04.10.2026 (Bridges)
    "SP500": dict(dirs="long", ribbon="neutral", weekday=None, rule="opposite", stop=0.6, target=6.0, partial=None, range_bars=1),
    "NASDAQ": dict(dirs="beide", ribbon="kein", weekday="Wednesday", rule="sl", stop=0.6, target=None, partial=None, range_bars=1),
    "US30": dict(dirs="long", ribbon="neutral", weekday=None, rule="opposite", stop=0.6, target=6.0, partial=None, range_bars=1),
}


def lock() -> Lock:
    lk = Lock(STRATEGY)
    lk.register_split(IS_START, IS_END, OOS_END, TRESOR_END)
    return lk


def load(instrument: str, end: str):
    m15 = pb._retry(lambda: fetch_m15(instrument, IS_START, end), attempts=3, delay_seconds=5, timeout_seconds=600)
    m1 = pb._retry(lambda: fetch_m1(instrument, IS_START, end), attempts=3, delay_seconds=5, timeout_seconds=1800)
    frames = {rb: build_frame(m15, m1, range_bars=rb) for rb in RANGES}
    sessions = pd.DatetimeIndex(frames[1]["session"].dropna().unique())
    bias = regime.ema_trend_bias(m15, sessions)
    return frames, sessions, bias


def allowed_for(sessions, bias, dirs: str, ribbon: str) -> dict:
    out = {}
    for s in sessions:
        b = bias.get(s, np.nan)
        ds = DIRS[dirs]
        if ribbon == "neutral":
            ds = ds if (not pd.isna(b) and float(b) == 0.0) else ()
        elif ribbon == "mit_trend":
            ds = tuple(d for d in ds if not pd.isna(b) and float(b) == d)
        out[s] = list(ds)
    return out


def metrics(r: pd.Series, cost_r: pd.Series | None = None) -> dict:
    if len(r) < 2:
        return {"n": len(r)}
    std = r.std(ddof=1)
    loss = -r[r < 0].sum()
    eq = r.cumsum().to_numpy()
    half = len(r) // 2
    years = (r.index.max() - r.index.min()).days / 365.25
    out = {"n": len(r), "per_year": len(r) / years if years > 0 else np.nan, "avg": r.mean(), "std": std,
           "t": r.mean() / std * np.sqrt(len(r)) if std > 0 else np.nan,
           "pf": r[r > 0].sum() / loss if loss > 0 else np.inf, "sum": r.sum(),
           "dd": (eq - np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]).min(),
           "h1": r.iloc[:half].sum(), "h2": r.iloc[half:].sum(), "win": (r > 0).mean(),
           "yrs_pos": int((r.groupby(r.index.year).sum() > 0).sum()), "yrs": r.index.year.nunique(),
           "skew": float(r.skew()), "kurt": float(r.kurt() + 3)}
    if cost_r is not None:
        out["cost_r"] = cost_r.mean()
        out["avg_cost_x2"] = (r - cost_r).mean()
    return out


def run_config(frames, sessions, bias, instrument, cfg) -> tuple[pd.Series, pd.Series]:
    """Trade-Reihe (R) + Kosten je Trade in R fuer eine Konfiguration."""
    frame = frames[cfg["range_bars"]]
    allowed = allowed_for(sessions, bias, cfg["dirs"], cfg["ribbon"])
    prep = prepare(frame, find_live_entries(frame, allowed, cfg["stop"], cfg["rule"]))
    res = sim(prep, instrument, cfg["stop"], cfg["target"], cfg["partial"])
    if res.empty:
        return pd.Series(dtype=float), pd.Series(dtype=float)
    idx = pd.DatetimeIndex(res["entry_time"])
    r = pd.Series(res["r"].to_numpy(), index=idx)
    by_t = {t["t"]: t for t in prep}
    cost_bps = (SPREAD_BPS[instrument] + ENTRY_SLIPPAGE_BPS + EXIT_SLIPPAGE_BPS) / 10_000
    cost = pd.Series([by_t[t]["level"] * cost_bps / (cfg["stop"] * by_t[t]["atr"]) for t in res["entry_time"]], index=idx)
    if cfg["weekday"]:
        keep = idx.day_name() != cfg["weekday"]
        r, cost = r[keep], cost[keep]
    return r.sort_index(), cost.sort_index()


# ---------------------------------------------------------------------------
def stage_grid() -> int:
    lk = lock()
    rows, n_trials = [], {}
    for instrument in INSTRUMENTS:
        frames, sessions, bias = load(instrument, IS_END)   # Sperre: nur IS geladen
        frames = {k: lk.is_only(v) for k, v in frames.items()}

        if instrument == "SP500":   # Paritaet sim() vs engine.simulate() (wie exit_grid_m1)
            cfg = LIVE["SP500"]
            ent = find_live_entries(frames[1], allowed_for(sessions, bias, "long", "neutral"), 0.6, "opposite")
            ref = simulate(frames[1], ent, spread_bps=SPREAD_BPS[instrument], entry_slippage_bps=ENTRY_SLIPPAGE_BPS,
                           slippage_bps=EXIT_SLIPPAGE_BPS, entry_fill_mode="level", stop_mode="atr",
                           stop_atr_mult=0.6, target_mode="r_multiple", target_r_mult=6.0)
            mine = sim(prepare(frames[1], ent), instrument, 0.6, 6.0, None)
            diff = np.abs(ref["r_multiple"].to_numpy() - mine["r"].to_numpy()).max() if len(ref) == len(mine) else np.inf
            print(f"Paritaet sim/simulate: {len(ref)} vs {len(mine)}, max |dR| = {diff:.2e}", flush=True)
            if not diff < 1e-9:
                print("ABBRUCH: Simulator weicht ab"); return 1

        count = 0
        for rb, dirs, rib, rule, stop in itertools.product(RANGES, DIRS, RIBBON, RULES, STOPS):
            frame = frames[rb]
            allowed = allowed_for(sessions, bias, dirs, rib)
            prep = prepare(frame, find_live_entries(frame, allowed, stop, rule))
            for target, partial in itertools.product(TARGETS, PARTIALS):
                if partial is not None and target is not None and partial >= target:
                    continue
                res = sim(prep, instrument, stop, target, partial)
                for wd in WEEKDAYS:
                    count += 1
                    if res.empty:
                        continue
                    idx = pd.DatetimeIndex(res["entry_time"])
                    r = pd.Series(res["r"].to_numpy(), index=idx).sort_index()
                    if wd:
                        r = r[r.index.day_name() != wd]
                    m = metrics(r)
                    rows.append({"instrument": instrument, "range_bars": rb, "dirs": dirs, "ribbon": rib, "rule": rule,
                                 "stop": stop, "target": target, "partial": partial, "weekday": wd,
                                 **{k: m.get(k) for k in ("n", "avg", "std", "t", "pf", "sum", "dd", "h1", "h2", "win")}})
            print(f"  {instrument} rb={rb} {dirs} {rib} {rule} {stop}: fertig", flush=True)
        n_trials[instrument] = count
        lk.log_trials(count, note=f"{instrument}: IS-Gitter")
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "is_only_grid.csv", index=False)

    # --- Auswahl --------------------------------------------------------------
    grid["eligible"] = (grid.n >= 100) & (grid.pf > 1.3) & (grid.h1 > 0) & (grid.h2 > 0)
    key_cols = ["instrument", "range_bars", "dirs", "ribbon", "rule", "partial", "weekday"]
    grid["partial_k"] = grid.partial.fillna(-1)
    grid["weekday_k"] = grid.weekday.fillna("-")
    grid["target_k"] = grid.target.fillna(-1)
    t_lookup = grid.set_index(["instrument", "range_bars", "dirs", "ribbon", "rule", "partial_k", "weekday_k",
                               "stop", "target_k"])["t"].to_dict()
    tk = [-1] + [t for t in TARGETS if t is not None]

    def smooth(row):
        si, ti = STOPS.index(row.stop), tk.index(row.target_k)
        vals = []
        for ds, dt in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
            a, b = si + ds, ti + dt
            if 0 <= a < len(STOPS) and 0 <= b < len(tk):
                v = t_lookup.get((row.instrument, row.range_bars, row.dirs, row.ribbon, row.rule, row.partial_k,
                                  row.weekday_k, STOPS[a], tk[b]))
                if v is not None and not pd.isna(v):
                    vals.append(v)
        return float(np.median(vals)) if vals else np.nan

    el = grid[grid.eligible].copy()
    el["t_smooth"] = el.apply(smooth, axis=1)
    winners, sr_var = {}, {}
    for instrument in INSTRUMENTS:
        g = el[el.instrument == instrument].sort_values("t_smooth", ascending=False)
        allg = grid[(grid.instrument == instrument) & (grid.n >= 30)]
        sr_var[instrument] = float((allg["avg"] / allg["std"]).var())
        print(f"\n{instrument}: {len(g)} von {len(grid[grid.instrument == instrument])} Zellen erfuellen die "
              f"Mindestbedingungen")
        if g.empty:
            winners[instrument] = None
            continue
        w = g.iloc[0]
        winners[instrument] = {"dirs": w.dirs, "ribbon": w.ribbon, "weekday": None if w.weekday_k == "-" else w.weekday,
                               "rule": w.rule, "stop": float(w.stop),
                               "target": None if w.target_k == -1 else float(w.target),
                               "partial": None if w.partial_k == -1 else float(w.partial), "range_bars": int(w.range_bars)}
        print(g.head(8)[["range_bars", "dirs", "ribbon", "rule", "stop", "target", "partial", "weekday", "n", "avg",
                         "pf", "t", "t_smooth"]].to_string(index=False))
    out = {"winners": winners, "n_trials": n_trials, "sr_var_trials": sr_var}
    (RES / "is_only_selection.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print("\nAuswahl gespeichert -> is_only_selection.json (noch NICHT eingefroren)")
    return 0


def stage_evaluate() -> int:
    lk = lock()
    sel = json.loads((RES / "is_only_selection.json").read_text(encoding="utf-8"))
    winners = sel["winners"]
    h = lk.freeze(winners)
    print("eingefroren:", h)
    st = json.loads(lk.path.read_text(encoding="utf-8"))
    oos = lk.unseal("oos", h) if "oos" not in st["unsealed"] else None
    tre = lk.unseal("tresor", h) if "tresor" not in st["unsealed"] else None
    print("OOS geoeffnet:", oos, "| Tresor geoeffnet:", tre)

    rows, trades = [], []
    # Nutzerentscheid 2026-10-06: nur Beine mit eingefrorenem Gewinner (US30 vor dem Freeze entfernt)
    for instrument in [i for i in INSTRUMENTS if winners.get(i)]:
        frames, sessions, bias = load(instrument, TRESOR_END)
        for label, cfg in (("IS-only", winners[instrument]), ("Live", LIVE[instrument])):
            if cfg is None:
                continue
            r, cost = run_config(frames, sessions, bias, instrument, cfg)
            trades.append(pd.DataFrame({"instrument": instrument, "variant": label, "time": r.index, "r": r.values,
                                        "cost_r": cost.values}))
            parts = {"IS": (lk.is_only(r), lk.is_only(cost)), "OOS": (lk.stage_slice(r, "oos"), lk.stage_slice(cost, "oos")),
                     "Tresor": (lk.stage_slice(r, "tresor"), lk.stage_slice(cost, "tresor")), "Gesamt": (r, cost)}
            for part, (rr, cc) in parts.items():
                m = metrics(rr, cc)
                rows.append({"instrument": instrument, "variant": label, "part": part, **m})
            m_is = metrics(lk.is_only(r))
            if label == "IS-only" and m_is.get("n", 0) > 2:
                dsr = deflated_sharpe(m_is["avg"] / m_is["std"], m_is["n"], sel["n_trials"][instrument],
                                      m_is["skew"], m_is["kurt"], sel["sr_var_trials"][instrument])
                rows.append({"instrument": instrument, "variant": label, "part": "DSR", "n": m_is["n"], "avg": dsr})
    rep = pd.DataFrame(rows)
    rep.to_csv(RES / "is_only_report.csv", index=False)
    pd.concat(trades).to_csv(RES / "is_only_trades.csv", index=False)
    pd.set_option("display.width", 250)
    print(rep.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    stage = sys.argv[sys.argv.index("--stage") + 1] if "--stage" in sys.argv else "grid"
    sys.exit(stage_grid() if stage == "grid" else stage_evaluate())
