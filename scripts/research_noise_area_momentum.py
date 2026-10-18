"""Zarattini/Aziz/Barbon "Beat the Market" (SFI N°24-97) nach dem 8-Phasen-Prozess.

Nutzerauftrag 2026-10-11: "Teste das Paper nach unserem Standardprozess".
Engine: noise_area_momentum/engine.py (Regeln 1:1, siehe Docstring dort).

Aufruf:  python scripts/research_noise_area_momentum.py phase4
         (weitere Phasen folgen als eigene Unterbefehle; Phase 4/5 geben NUR IS aus)

Lock zarattini_noise_area_20261011
SPLIT: IS 2016-07-28..2022-12-31 | OOS ..2025-09-30 | Tresor ..2026-09-30
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).resolve().parent))

from noise_area_momentum.engine import build_grid, metrics, run, yearly  # noqa: E402
from ny_open_orb.data import fetch_m1  # noqa: E402
from research_lock import Lock  # noqa: E402
from research_orb_cancel_at_sl_and_hold import ENTRY_SLIPPAGE_BPS, EXIT_SLIPPAGE_BPS, SPREAD_BPS  # noqa: E402

STRATEGY = "zarattini_noise_area_20261011"
IS_START, IS_END, OOS_END, TRESOR_END = "2016-07-28", "2022-12-31", "2025-09-30", "2026-09-30"
INSTRUMENTS = ("SP500", "NASDAQ")
OUT = ROOT / "noise_area_momentum" / "results"
COST_RT = {i: SPREAD_BPS[i] + ENTRY_SLIPPAGE_BPS + EXIT_SLIPPAGE_BPS for i in INSTRUMENTS}

# Paper-Tabelle Q24 (dyn. Sizing, SPY, netto): Jahresrenditen im IS-Fenster, zum Kalibrieren
PAPER_YEARLY = {2016: -12.8, 2017: -6.9, 2018: 61.1, 2019: 6.9, 2020: 26.8, 2021: 34.8, 2022: 24.4}

PAPER_VARIANTS = {
    "A Basis (Gegenband, 1x)": dict(stop="opp", sizing="1x"),
    "B Band+VWAP (1x)": dict(stop="vwap", sizing="1x"),
    "C Band+VWAP (dyn. Sizing)": dict(stop="vwap", sizing="dyn"),
}

_grids: dict = {}


def grid(inst: str) -> dict:
    if inst not in _grids:
        _grids[inst] = build_grid(fetch_m1(inst, IS_START, TRESOR_END))
    return _grids[inst]


def lock() -> Lock:
    lk = Lock(STRATEGY)
    lk.register_split(IS_START, IS_END, OOS_END, TRESOR_END)
    return lk


def phase4() -> None:
    lk = lock()
    if lk.trials == 0:
        lk.log_trials(len(PAPER_VARIANTS), note="Phase 4: Paper-Regel 1:1, drei Paper-Varianten (Tab. 1-3)")
    OUT.mkdir(parents=True, exist_ok=True)
    rows, years = [], {}
    for inst in INSTRUMENTS:
        g = grid(inst)
        for name, kw in PAPER_VARIANTS.items():
            for cost_name, cost in (("brutto", 0.0), ("netto", COST_RT[inst])):
                df = lk.is_only(run(g, cost_rt_bps=cost, **kw))
                rows.append({"inst": inst, "variante": name, "kosten": cost_name, **metrics(df)})
                if cost_name == "netto":
                    years[(inst, name)] = yearly(df)
                    if name.startswith("B"):
                        d = df[df["valid"]]
                        rows.append({"inst": inst, "variante": name + " nur long", "kosten": "brutto",
                                     "bps_tag": d["long_gross"].mean() * 1e4})
                        rows.append({"inst": inst, "variante": name + " nur short", "kosten": "brutto",
                                     "bps_tag": d["short_gross"].mean() * 1e4})
    rep = pd.DataFrame(rows)
    rep.to_csv(OUT / "phase4_is.csv", index=False)
    yr = pd.DataFrame(years)
    yr.columns = [f"{a} | {b[:2]}" for a, b in yr.columns]
    yr["Paper SPY (C)"] = pd.Series(PAPER_YEARLY)
    yr.to_csv(OUT / "phase4_is_years.csv")
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(f"Kosten je Rundturn (bps): {COST_RT}")
    print(rep.round(3).to_string(index=False))
    print("\nJahresrenditen netto % (IS):\n", yr.round(1).to_string())
    for inst in INSTRUMENTS:
        col = f"{inst} | C "
        print(f"Korrelation Jahre {inst}-C vs. Paper:", round(yr[col].corr(yr["Paper SPY (C)"]), 2))


# Phase 5: vorab festgelegtes Raster (8 Punkte je Index, Richtwert <= 9), Auswahl NUR auf IS,
# Kriterium: Netto-Sharpe bei 1x. Stop fest "vwap" (Paper-Hauptvariante).
#   vm 1.0 / 1.5      Paper Fig. 9: Sharpe-Optimum bei 1,5; weniger Trades = weniger Kosten
#   lookback 14 / 90  Paper Q6: 90 Tage bestes Sharpe
#   gate none / gex   Paper 4.5 (Gamma-Mechanismus, dort per RSI-Proxy) -> hier echtes SPX-GEX:
#                     handeln nur, wenn GEX(Vortag) unter seinem 252-Tage-Median liegt
# Nicht getestet (begruendet): Kalman/ADX/EMA200 (p5_1-p5_3) -- die Noise Area ist selbst der
# Trend-/Regime-Filter; Paper Q21 zeigt, dass ein SMA-Richtungsfilter Ertrag kostet.
GEX_FILE = ROOT / "scripts" / "frozen_data" / "sqzme_dix_gex_20261006.csv"
GRID5 = [dict(vm=vm, lookback=lb, gate=gt) for vm in (1.0, 1.5) for lb in (14, 90) for gt in ("none", "gex")]


def gex_gate(dates: pd.DatetimeIndex) -> np.ndarray:
    gex = pd.read_csv(GEX_FILE, parse_dates=["date"]).set_index("date")["gex"].sort_index()
    prev = gex.shift(1)
    med = prev.rolling(252, min_periods=120).median()
    ok = (prev < med).reindex(dates, method="ffill")
    return ok.fillna(False).to_numpy(dtype=bool)


def run_cfg(inst: str, cfg: dict, **kw):
    g = grid(inst)
    gate = gex_gate(g["dates"]) if cfg.get("gate") == "gex" else None
    return run(g, vm=cfg["vm"], lookback=cfg["lookback"], stop="vwap", gate=gate, **kw)


def phase5() -> None:
    lk = lock()
    if lk.trials == len(PAPER_VARIANTS):  # nur beim ersten Lauf zaehlen
        lk.log_trials(len(GRID5) * len(INSTRUMENTS), note="Phase 5: vm x lookback x GEX-Gate, je Index getrennt gewaehlt")
    rows = []
    for inst in INSTRUMENTS:
        for cfg in GRID5:
            df = lk.is_only(run_cfg(inst, cfg, cost_rt_bps=COST_RT[inst]))
            m = metrics(df)
            dyn = metrics(lk.is_only(run_cfg(inst, cfg, cost_rt_bps=COST_RT[inst], sizing="dyn")))
            rows.append({"inst": inst, **cfg, **{k: m[k] for k in ("sharpe", "t", "cagr_%", "mdd_%", "trades_tag",
                                                                      "brutto_bps_trade_1x")},
                         "sharpe_dyn": dyn["sharpe"], "cagr_dyn_%": dyn["cagr_%"], "mdd_dyn_%": dyn["mdd_%"]})
    rep = pd.DataFrame(rows)
    rep.to_csv(OUT / "phase5_is.csv", index=False)
    pd.set_option("display.width", 250)
    print(rep.round(3).to_string(index=False))
    win = rep.loc[rep.groupby("inst")["sharpe"].idxmax()]
    print("\nIS-Gewinner je Index:\n", win.round(3).to_string(index=False))


# IS-Gewinner aus Phase 5 (Kriterium Netto-Sharpe 1x); Sizing wie Paper-Endvariante = dyn
WINNERS = {"SP500": dict(vm=1.0, lookback=14, gate="none"), "NASDAQ": dict(vm=1.0, lookback=90, gate="none")}


def block_bootstrap(r: np.ndarray, n_sims: int = 2000, block: int = 20, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = len(r)
    out = []
    for _ in range(n_sims):
        starts = rng.integers(0, n - block, size=n // block + 1)
        s = np.concatenate([r[a:a + block] for a in starts])[:n]
        eq = np.cumprod(1 + s)
        out.append((s.mean() / s.std(ddof=1) * np.sqrt(252), (eq[-1] ** (252 / n) - 1) * 100,
                    ((eq / np.maximum.accumulate(eq)) - 1).min() * -100))
    return pd.DataFrame(out, columns=["sharpe", "cagr_%", "mdd_%"])


def phase6() -> None:
    """Robustheit NUR auf IS (vor dem Einfrieren)."""
    from noise_area_momentum.engine import entry_stop_distance_bps
    lk = lock()
    pd.set_option("display.width", 250)
    rows, mc_rows, lag_rows = [], [], []
    for inst in INSTRUMENTS:
        cfg, cost = WINNERS[inst], COST_RT[inst]
        # p6_6 Ausfuehrungs-Lag (Bars = Minuten nach HH:00/HH:30)
        for lag in (0, 1, 2, 5, 10):
            for sz in ("1x", "dyn"):
                m = metrics(lk.is_only(run_cfg(inst, cfg, cost_rt_bps=cost, lag_bars=lag, sizing=sz)))
                lag_rows.append({"inst": inst, "lag_min": lag, "sizing": sz, "sharpe": m["sharpe"], "t": m["t"],
                                 "cagr_%": m["cagr_%"], "bps_trade_brutto": m["brutto_bps_trade_1x"]})
        # p6_3 Kosten bis Breakeven (1x)
        for c in (0, 0.5, 1.0, cost, 2.0, 3.0, 4.0, 5.0):
            m = metrics(lk.is_only(run_cfg(inst, cfg, cost_rt_bps=c)))
            rows.append({"inst": inst, "kosten_rt_bps": c, "sharpe": m["sharpe"], "cagr_%": m["cagr_%"]})
        # p6_2 Monte Carlo (Block-Bootstrap der Tagesrenditen, dyn)
        d = lk.is_only(run_cfg(inst, cfg, cost_rt_bps=cost, sizing="dyn"))
        mc = block_bootstrap(d.loc[d["valid"], "ret_net"].to_numpy())
        mc_rows.append({"inst": inst, **{f"{k}_p5": mc[k].quantile(0.05) for k in mc},
                        **{f"{k}_p50": mc[k].median() for k in mc}, **{f"{k}_p95": mc[k].quantile(0.95) for k in mc},
                        "P(sharpe<0)": (mc["sharpe"] < 0).mean()})
        # p6_7 Hebelverteilung (dyn)
        lev = d.loc[d["valid"], "lev"]
        print(f"{inst} Hebel dyn: Median {lev.median():.2f}, p90 {lev.quantile(.9):.2f}, Anteil am Deckel 4x "
              f"{(lev >= 3.999).mean():.1%}")
        # p6_8 Stopabstand gegen Kosten
        g = grid(inst)
        dist = entry_stop_distance_bps(g, vm=cfg["vm"], lookback=cfg["lookback"])
        isd = pd.Series(1, index=g["dates"]); isd = lk.is_only(isd)
        print(f"{inst} Stopabstand beim Einstieg (bps, alle Jahre): Median {np.median(dist):.1f}, "
              f"Anteil < 3x Rundturn-Kosten ({3 * cost:.1f} bps): {(dist < 3 * cost).mean():.1%}")
    print("\np6_6 Ausfuehrungs-Lag (IS):\n", pd.DataFrame(lag_rows).round(3).to_string(index=False))
    print("\np6_3 Kosten-Sweep (IS, 1x):\n", pd.DataFrame(rows).round(3).to_string(index=False))
    print("\np6_2 Block-Bootstrap (IS, dyn, 2000 Laeufe, Block 20 Tage):\n",
          pd.DataFrame(mc_rows).round(3).T.to_string())
    pd.DataFrame(lag_rows).to_csv(OUT / "phase6_lag_is.csv", index=False)
    pd.DataFrame(rows).to_csv(OUT / "phase6_kosten_is.csv", index=False)
    pd.DataFrame(mc_rows).to_csv(OUT / "phase6_mc_is.csv", index=False)


def unseal() -> None:
    """p6_9 einfrieren + Deflated Sharpe, p6_10 OOS und Tresor je genau einmal."""
    from research_lock import deflated_sharpe
    lk = lock()
    frozen = {"regel": "Zarattini Noise Area, Stop max(Band,VWAP), Entscheid HH:00/HH:30 10:00-15:30, Exit 16:00",
              "configs": WINNERS, "kosten_rt_bps": COST_RT, "sizing": "1x und dyn (2 %-Ziel, Deckel 4x)"}
    h = lk.freeze(frozen)
    st = lk._load()
    n_trials = st["trials"]
    print(f"Eingefroren {h[:12]}, Versuche gesamt: {n_trials}")
    full = {inst: {sz: run_cfg(inst, WINNERS[inst], cost_rt_bps=COST_RT[inst], sizing=sz) for sz in ("1x", "dyn")}
            for inst in INSTRUMENTS}
    lag5 = {inst: run_cfg(inst, WINNERS[inst], cost_rt_bps=COST_RT[inst], lag_bars=5) for inst in INSTRUMENTS}
    for inst in INSTRUMENTS:
        r = lk.is_only(full[inst]["1x"]).query("valid")["ret_net"]
        sr = r.mean() / r.std(ddof=1)
        dsr = deflated_sharpe(sr, len(r), n_trials, skew=float(r.skew()), kurt=float(r.kurt() + 3))
        print(f"{inst}: IS Sharpe/Tag {sr:.4f} (ann. {sr * np.sqrt(252):.2f}), Deflated Sharpe {dsr:.3f}")
    if "oos" not in st["unsealed"]:
        lk.unseal("oos", h)
    if "tresor" not in lk._load()["unsealed"]:
        lk.unseal("tresor", h)
    rows, yrs = [], {}
    for inst in INSTRUMENTS:
        for sz in ("1x", "dyn"):
            df = full[inst][sz]
            for per, sl in (("IS", lk.is_only(df)), ("OOS 2023-01..2025-09", lk.stage_slice(df, "oos")),
                            ("Tresor 2025-10..2026-09", lk.stage_slice(df, "tresor")),
                            ("nach Publikation 2024-05-10..", df[df.index >= "2024-05-10"])):
                rows.append({"inst": inst, "sizing": sz, "periode": per, **metrics(sl)})
            yrs[(inst, sz)] = yearly(df)
        for per, sl in (("OOS", lk.stage_slice(lag5[inst], "oos")), ("Tresor", lk.stage_slice(lag5[inst], "tresor"))):
            rows.append({"inst": inst, "sizing": "1x lag5", "periode": per, **metrics(sl)})
        for per, sl in (("OOS", lk.stage_slice(full[inst]["1x"], "oos")),
                        ("Tresor", lk.stage_slice(full[inst]["1x"], "tresor"))):
            d = sl[sl["valid"]]
            rows.append({"inst": inst, "sizing": "1x long/short brutto bps/Tag", "periode": per,
                         "bps_tag": d["long_gross"].mean() * 1e4, "hit_tag": d["short_gross"].mean() * 1e4})
    rep = pd.DataFrame(rows)
    rep.to_csv(OUT / "unseal_oos_tresor.csv", index=False)
    yr = pd.DataFrame(yrs); yr.columns = [f"{a} {b}" for a, b in yr.columns]
    yr.to_csv(OUT / "unseal_years.csv")
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(rep.round(3).to_string(index=False))
    print("\n(Zeile long/short: bps_tag = long brutto, hit_tag-Spalte = short brutto)")
    print("\nJahresrenditen netto %:\n", yr.round(1).to_string())


def trade_list(inst: str) -> pd.DataFrame:
    """Trade-Liste der eingefrorenen Config (beschreibend, fuer die Tresor-Diagnose 12.10.)."""
    from noise_area_momentum.engine import DECISIONS, _sigma, _vwap
    g, cfg = grid(inst), WINNERS[inst]
    o, c = g["open"], g["close"]
    sig = _sigma(g, cfg["lookback"])
    prev_close = np.r_[np.nan, c[:-1, -1]]
    o0 = o[:, 0]
    top, bot = np.fmax(o0, prev_close), np.fmin(o0, prev_close)
    vw = _vwap(g)
    m = DECISIONS
    p, v = c[:, m - 1], vw[:, m - 1]
    ub = top[:, None] * (1 + cfg["vm"] * sig[:, m - 1])
    lb = bot[:, None] * (1 - cfg["vm"] * sig[:, m - 1])
    pos = np.where((p > ub) & (p > v), 1, np.where((p < lb) & (p < v), -1, 0))
    x = np.column_stack([o[:, m], c[:, -1]])
    rv = pd.Series(c[:, -1], index=g["dates"]).pct_change().rolling(14).std().shift(1).to_numpy()
    rng = (np.nanmax(g["high"], axis=1) - np.nanmin(g["low"], axis=1)) / o0
    rows = []
    for d in range(len(p)):
        if np.isnan(ub[d]).any() or np.isnan(prev_close[d]):
            continue
        j, first = 0, True
        while j < len(m):
            side = pos[d, j]
            if side == 0:
                j += 1
                continue
            k = j + 1
            while k < len(m) and pos[d, k] == side:
                k += 1
            reason = "16:00" if k == len(m) else ("flip" if pos[d, k] == -side else "stop")
            band = ub[d, j] if side > 0 else lb[d, j]
            rows.append({"date": g["dates"][d], "dec": int(m[j]), "side": int(side), "first": first,
                         "gross_bps": side * (x[d, k] / x[d, j] - 1) * 1e4,
                         "hold_close_bps": side * (x[d, -1] / x[d, j] - 1) * 1e4,
                         "halbstunden": k - j, "exit": reason,
                         "ueber_band_bps": side * (p[d, j] / band - 1) * 1e4,
                         "sigma_bps": sig[d, m[j] - 1] * 1e4,
                         "gap_bps": (o0[d] / prev_close[d] - 1) * 1e4,
                         "mit_gap": bool(np.sign(o0[d] / prev_close[d] - 1) == side),
                         "rv14_%": rv[d] * 100, "tagesrange_bps": rng[d] * 1e4})
            first = False
            j = k
    t = pd.DataFrame(rows).set_index("date")
    gex = pd.read_csv(GEX_FILE, parse_dates=["date"]).set_index("date")["gex"].sort_index().shift(1)
    t["gex_mrd"] = gex.reindex(t.index, method="ffill").to_numpy() / 1e9
    return t


def _periode(ix):
    return np.where(ix < pd.Timestamp("2023-01-01"), "1 IS 16-22",
                    np.where(ix < pd.Timestamp("2025-10-01"), "2 OOS 23-09/25", "3 Tresor 10/25-09/26"))


def _tab(t, by, val="gross_bps"):
    a = t.groupby(["periode", by], observed=True)[val].agg(["mean", "count"])
    return a["mean"].round(2).unstack(0).join(a["count"].unstack(0), rsuffix=" n")


def diagnose() -> None:
    """Was kippt den Tresor? Rein beschreibend auf bereits geoeffneten Daten (OOS/Tresor seit 11.10. offen)."""
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    for inst in INSTRUMENTS:
        t = trade_list(inst)
        t["periode"] = _periode(t.index)
        t.to_csv(OUT / f"diagnose_trades_{inst}.csv")
        print(f"\n################ {inst} (brutto bps je Trade, 1x) ################")
        print("Gesamt:\n", t.groupby("periode")[["gross_bps", "hold_close_bps", "halbstunden"]].mean().round(2)
              .join(t.groupby("periode").size().rename("n")).to_string())
        print("\nRichtung:\n", _tab(t, "side").to_string())
        print("\nErster Trade des Tages vs. Folgetrades:\n", _tab(t, "first").to_string())
        print("\nAusstiegsart:\n", _tab(t, "exit").to_string())
        print("\nEinstiegszeit (Minuten nach 09:30):\n", _tab(t, "dec").to_string())
        print("\nSignal ohne Stop (Ausbruch -> bis 16:00 halten), je Einstiegszeit:\n",
              _tab(t, "dec", "hold_close_bps").to_string())
        print("\nIn Gap-Richtung vs. gegen Gap:\n", _tab(t, "mit_gap").to_string())
        t["gex_klasse"] = pd.cut(t["gex_mrd"], [-1e9, 0, 3, 6, 1e9], labels=["<0", "0-3", "3-6", ">6"])
        print("\nSPX-GEX Vortag (Mrd. $):\n", _tab(t, "gex_klasse").to_string())
        t["rv_klasse"] = pd.cut(t["rv14_%"], [0, 0.7, 1.0, 1.5, 99], labels=["<0,7", "0,7-1", "1-1,5", ">1,5"])
        print("\nRealisierte Vola 14 Tage (% je Tag):\n", _tab(t, "rv_klasse").to_string())
        tr = t[t["periode"].str.startswith("3")]
        mon = tr.groupby(tr.index.to_period("M")).agg(n=("gross_bps", "size"), sum_bps=("gross_bps", "sum"),
                                                     mean=("gross_bps", "mean"), anteil_long=("side", lambda s: (s > 0).mean()))
        print("\nTresor je Monat:\n", mon.round(2).to_string())
        print("\nStrukturgroessen je Periode (Median):\n",
              t.groupby("periode")[["sigma_bps", "ueber_band_bps", "tagesrange_bps", "gex_mrd", "rv14_%"]]
              .median().round(2).to_string())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    {"phase4": phase4, "phase5": phase5, "phase6": phase6, "unseal": unseal,
     "diagnose": diagnose}[sys.argv[1]]()
