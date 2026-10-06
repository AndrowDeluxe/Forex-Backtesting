"""Tagesend-Momentum/-Umkehr (Baltussen) erweitert: Zeitfenster, Einstiege, SL/TP/Haltezeit.

Nutzerauftrag 2026-10-07: "Erweitere den Baltussen-Test auf andere Zeitfenster,
Entry-Varianten und optimiere SL und TP sowie Haltezeit sauber im IS-Fenster."

SPLIT (Lock baltussen_extended_20261007): IS 2016-07-28..2022-12-31 | OOS
2023-01-01..2026-09-30 (einmal; Bericht 2023-24 / 2025-09/2026).
NICHT voll blind: Die Grundregel samt Gamma-Bedingungen wurde fuer 2023-26
am 06.10. schon ausgewertet (research_baltussen_late_momentum.py).

SUCHRAUM je Index (8 Punkte <= Richtwert 9):
  1 Einstiegszeit T   14:00 / 14:30 / 15:00 / 15:30 / 15:45 NY
  2 Signal            rod = Vortagesschluss->T (Baltussen) / intra = 09:30->T / hour = T-60->T
  3 Richtung          momentum (mit Signal) / umkehr (gegen Signal)
  4 Mindestbewegung   keine / |Signal| > 67-%-Quantil der letzten 60 Tage
  5 Gamma (Vortag)    keine / GEX<0 / GEX-Perzentil(252) < 20 % / > 80 %
  6 Stop              keiner / 0,1 / 0,2 / 0,4 x Tages-ATR(14, Vortage)
  7 Ziel              keins / 1R / 2R (nur mit Stop)
  8 Haltezeit         15 / 30 / 60 Min. / bis 16:00 (immer spaetestens 16:00)
Ausfuehrung: Einstieg zum Schlusskurs der Minute vor T, Stop/Ziel intrabar auf
M1 (beide in einer Minute -> Stop zuerst, konservativ), Kosten wie ORB
(Spread + Slippage je Seite).

AUSWAHLREGEL (nur IS): >= 100 Trades, PF (bps) > 1,3, beide IS-Haelften > 0,
Score = t-Wert der Netto-bps, geglaettet ueber Haltezeit-/Stop-Nachbarn (Median).
Deflated Sharpe gegen die Versuchsanzahl.
"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).resolve().parent))

import challenge_portfolio.paper_bot as pb  # noqa: E402
from ny_open_orb.data import fetch_m1  # noqa: E402
from research_lock import Lock, deflated_sharpe  # noqa: E402
from research_orb_cancel_at_sl_and_hold import ENTRY_SLIPPAGE_BPS, EXIT_SLIPPAGE_BPS, SPREAD_BPS  # noqa: E402

STRATEGY = "baltussen_extended_20261007"
IS_START, IS_END, OOS_END = "2016-07-28", "2022-12-31", "2026-09-30"
RES = ROOT / "ny_open_orb" / "results"
GEX_FILE = ROOT / "scripts" / "frozen_data" / "sqzme_dix_gex_20261006.csv"
TIMES = ["14:00", "14:30", "15:00", "15:30", "15:45"]
SIGNALS = ["rod", "intra", "hour"]
DIRS = ["momentum", "umkehr"]
MINMOVE = ["keine", "gross"]
GAMMA = ["keine", "gex_neg", "gex_tief", "gex_hoch"]
STOPS = [None, 0.1, 0.2, 0.4]
TARGETS = [None, 1.0, 2.0]
HOLDS = [15, 30, 60, None]
WIN_START = 12 * 60 + 30  # Minutenmatrix ab 12:30 (Signal "hour" bei T=14:00 braucht 12:59)


def build(inst: str, end: str):
    m1 = pb._retry(lambda: fetch_m1(inst, IS_START, end), attempts=3, delay_seconds=5, timeout_seconds=1800).copy()
    m1["date"] = m1.index.tz_localize(None).normalize()
    m1["hm"] = m1.index.hour * 60 + m1.index.minute
    rth = m1[(m1.hm >= 570) & (m1.hm < 960)]
    daily = rth.groupby("date").agg(o=("open", "first"), c=("close", "last"), h=("high", "max"), l=("low", "min"))
    daily["prev_c"] = daily["c"].shift(1)
    daily["atr"] = (daily["h"] - daily["l"]).rolling(14).mean().shift(1)
    win = rth[rth.hm >= WIN_START]
    mins = np.arange(WIN_START, 960)
    piv = {k: win.pivot_table(index="date", columns="hm", values=k).reindex(columns=mins) for k in ("high", "low", "close")}
    days = daily.dropna().index.intersection(piv["close"].dropna(thresh=180).index)
    H, L, C = (piv[k].loc[days].ffill(axis=1).to_numpy() for k in ("high", "low", "close"))
    d = daily.loc[days]
    g = pd.read_csv(GEX_FILE, parse_dates=["date"]).set_index("date")["gex"].sort_index()
    gp = g.rolling(252, min_periods=120).apply(lambda w: (w[:-1] < w[-1]).mean(), raw=True)
    feat = pd.DataFrame(index=days)
    feat["gex_prev"] = g.shift(1).reindex(days, method="ffill")
    feat["gex_p_prev"] = gp.shift(1).reindex(days, method="ffill")
    return days, H, L, C, d, feat


def simulate(days, H, L, C, d, feat, inst, T, sig, dirn, mm, gam, stop, tgt, hold):
    ti = int(T[:2]) * 60 + int(T[3:]) - WIN_START       # Spalte der Minute T (Einstieg = Schluss der Minute davor)
    px = C[:, ti - 1]
    base = {"rod": d["prev_c"].to_numpy(), "intra": d["o"].to_numpy(), "hour": C[:, ti - 61]}[sig]
    s = px / base - 1
    direction = np.sign(s) * (1 if dirn == "momentum" else -1)
    ok = direction != 0
    if mm == "gross":
        a = pd.Series(np.abs(s), index=days)
        ok &= (a > a.shift(1).rolling(60, min_periods=30).quantile(0.67)).to_numpy()
    if gam == "gex_neg":
        ok &= (feat["gex_prev"] < 0).to_numpy()
    elif gam == "gex_tief":
        ok &= (feat["gex_p_prev"] < 0.2).to_numpy()
    elif gam == "gex_hoch":
        ok &= (feat["gex_p_prev"] > 0.8).to_numpy()
    last = H.shape[1] - 1 if hold is None else min(H.shape[1] - 1, ti + hold - 1)
    hh, ll, cc = H[:, ti:last + 1], L[:, ti:last + 1], C[:, ti:last + 1]
    exit_px = cc[:, -1].copy()
    if stop is not None:
        dist = stop * d["atr"].to_numpy()
        sl = px - direction * dist
        hit_sl = np.where(direction[:, None] > 0, ll <= sl[:, None], hh >= sl[:, None])
        first_sl = np.where(hit_sl.any(1), hit_sl.argmax(1), 10**6)
        first_tp = np.full(len(px), 10**6)
        if tgt is not None:
            tp = px + direction * dist * tgt
            hit_tp = np.where(direction[:, None] > 0, hh >= tp[:, None], ll <= tp[:, None])
            first_tp = np.where(hit_tp.any(1), hit_tp.argmax(1), 10**6)
            exit_px = np.where(first_tp < first_sl, tp, exit_px)
        exit_px = np.where((first_sl <= first_tp) & (first_sl < 10**6), sl, exit_px)
    half = SPREAD_BPS[inst] / 2
    cost = 2 * half + ENTRY_SLIPPAGE_BPS + EXIT_SLIPPAGE_BPS
    gross = direction * (exit_px / px - 1) * 1e4
    net = gross - cost
    r = pd.Series(net[ok], index=days[ok])
    return r[~r.isna()]


def stats(r: pd.Series) -> dict:
    if len(r) < 2 or r.std(ddof=1) == 0:
        return {"n": len(r)}
    loss = -r[r < 0].sum()
    half = len(r) // 2
    yrs = max((r.index.max() - r.index.min()).days / 365.25, 0.25)
    return {"n": len(r), "per_year": len(r) / yrs, "bps": r.mean(), "std": r.std(ddof=1),
            "t": r.mean() / r.std(ddof=1) * np.sqrt(len(r)), "pf": r[r > 0].sum() / loss if loss > 0 else np.inf,
            "h1": r.iloc[:half].sum(), "h2": r.iloc[half:].sum(), "hit": (r > 0).mean(), "sum": r.sum(),
            "skew": float(r.skew()), "kurt": float(r.kurt() + 3)}


def combos():
    for T, sig, dirn, mm, gam, hold in itertools.product(TIMES, SIGNALS, DIRS, MINMOVE, GAMMA, HOLDS):
        for stop in STOPS:
            for tgt in (TARGETS if stop is not None else [None]):
                yield dict(T=T, sig=sig, dirn=dirn, mm=mm, gam=gam, stop=stop, tgt=tgt, hold=hold)


def main() -> int:
    lk = Lock(STRATEGY)
    lk.register_split(IS_START, IS_END, OOS_END)
    st = lk._load()
    rows = []
    grid_file = RES / "baltussen_ext_grid.csv"
    reuse = grid_file.exists() and st["trials"] > 0 and st["frozen"] is None
    for inst in (() if reuse else ("SP500", "NASDAQ")):
        days, H, L, C, d, feat = build(inst, IS_END)       # Sperre: nur IS geladen
        for cfg in combos():
            m = stats(simulate(days, H, L, C, d, feat, inst, **cfg))
            rows.append({"inst": inst, **cfg, **m})
        print(f"{inst}: IS-Gitter fertig ({sum(1 for _ in combos())} Varianten)", flush=True)
    grid = pd.read_csv(grid_file) if reuse else pd.DataFrame(rows)
    n_trials = sum(1 for _ in combos())
    if st["trials"] == 0:
        lk.log_trials(len(grid), note="2 Indizes x Baltussen-Erweiterung (8 Punkte)")
    if not reuse:
        grid.to_csv(grid_file, index=False)

    grid["eligible"] = (grid.n >= 100) & (grid.pf > 1.3) & (grid.h1 > 0) & (grid.h2 > 0)
    grid["stop_k"] = grid["stop"].fillna(0)
    grid["tgt_k"] = grid["tgt"].fillna(0)
    grid["hold_k"] = grid["hold"].fillna(999)
    keys = ["inst", "T", "sig", "dirn", "mm", "gam", "tgt_k"]
    look = grid.set_index(keys + ["stop_k", "hold_k"])["t"].to_dict()
    S = [0, 0.1, 0.2, 0.4]
    Hk = [15, 30, 60, 999]

    def smooth(r):
        si, hi = S.index(r.stop_k), Hk.index(r.hold_k)
        v = []
        for ds, dh in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
            a, b = si + ds, hi + dh
            if 0 <= a < 4 and 0 <= b < 4:
                x = look.get(tuple(r[keys]) + (S[a], Hk[b]))
                if x is not None and not pd.isna(x):
                    v.append(x)
        return float(np.median(v)) if v else np.nan

    winners, dsr = {}, {}
    for inst in ("SP500", "NASDAQ"):
        g = grid[grid.inst == inst]
        el = g[g.eligible].copy()
        print(f"\n{inst}: {len(el)} von {len(g)} Varianten erfuellen die Mindestbedingungen")
        if el.empty:
            winners[inst] = None
            continue
        el["t_smooth"] = el.apply(smooth, axis=1)
        el = el.sort_values("t_smooth", ascending=False)
        cols = ["T", "sig", "dirn", "mm", "gam", "stop", "tgt", "hold", "n", "bps", "pf", "t", "t_smooth", "hit"]
        print(el.head(12)[cols].round(3).to_string(index=False))
        print("Richtung Top 50:", el.head(50)["dirn"].value_counts().to_dict(), "| Gamma Top 50:",
              el.head(50)["gam"].value_counts().to_dict(), "| Zeit Top 50:", el.head(50)["T"].value_counts().to_dict())
        w = el.iloc[0]
        winners[inst] = {k: (None if (isinstance(w[k], float) and np.isnan(w[k])) else (w[k] if not isinstance(w[k], (np.floating, np.integer)) else float(w[k])))
                         for k in ["T", "sig", "dirn", "mm", "gam", "stop", "tgt", "hold"]}
        gg = g[g.n >= 30]
        dsr[inst] = deflated_sharpe(w["bps"] / w["std"], int(w["n"]), n_trials, w["skew"], w["kurt"], float((gg.bps / gg["std"]).var()))
        print(f"Deflated Sharpe {inst}: {dsr[inst]:.3f}")

    h = lk.freeze(winners)
    if "oos" not in lk._load()["unsealed"]:
        print("\nOOS geoeffnet:", lk.unseal("oos", h))
    rep = []
    for inst in ("SP500", "NASDAQ"):
        if not winners.get(inst):
            continue
        days, H, L, C, d, feat = build(inst, OOS_END)
        r = simulate(days, H, L, C, d, feat, inst, **winners[inst])
        r.to_csv(RES / f"baltussen_ext_trades_{inst}.csv")
        for per, a, b in (("IS 2016-2022", IS_START, "2023-01-01"), ("OOS 2023-2024", "2023-01-01", "2025-01-01"),
                          ("OOS 2025-09/2026", "2025-01-01", "2026-10-01")):
            m = stats(r[(r.index >= a) & (r.index < b)])
            rep.append({"inst": inst, "periode": per, **{k: m.get(k) for k in ("n", "per_year", "bps", "pf", "t", "hit", "sum")},
                        "dsr_is": dsr.get(inst)})
    rep = pd.DataFrame(rep)
    rep.to_csv(RES / "baltussen_ext_report.csv", index=False)
    (RES / "baltussen_ext_selection.json").write_text(json.dumps({"winners": winners, "dsr": dsr, "n_trials": n_trials},
                                                                 indent=2, default=str), encoding="utf-8")
    print("\n", json.dumps(winners, indent=1, default=str))
    print(rep.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
