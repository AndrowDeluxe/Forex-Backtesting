"""CTNL-Reversal Live-Set (Ribbon + Spike >= 0,75 ATR, Lag-Replay) mit/ohne Makro-Sperre, 2016-heute,
1 % Risiko je Trade auf das Konto (taeglich verzinst). 15.11.2026, Nutzerauftrag.

Kosten: 2,01 bps Round-Trip (TTP gemessen inkl. Spread, Slippage, Kommission; teuerster Broker),
Einstieg 1 M15-Bar spaeter, R-Detektor 0,50 R. Swap: --swap-bps je Nacht (NY 17:00, Mittwoch 3x),
Annahme 1,5 bps (nicht gemessen).
Kill-Switch (--killswitch): wie gold_smc_htf_ltf/ctnl_kill_switch._dd_gehandelt -- Schatten-Trades Cont+Rev
aus der Scan-Konfiguration (8 bps), nur Ribbon-konform (beide) + Spike (Rev), 90-Tage-Fenster, 100k-Konto mit FK-Risiken 0,5 %/0,15 %, aktiv bei
DD <= -6,6 %, aufgehoben ab -3,3 %. Eingabe results/ctnl_ks_shadow.pkl.

Eingabe: fusion_lab/data/gold_confirm/results/ctnl_live_set.pkl (research_ctnl_confirm_wf.trades)
Aufruf:  python scripts/research_ctnl_macro_live.py [--equity 99650]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "ou_paper_backtest")]
from gold_smc_htf_ltf import macro_gate  # noqa: E402
from gold_smc_htf_ltf.spike_gate import SPIKE_MIN_ATR  # noqa: E402
from monte_carlo import run_monte_carlo  # noqa: E402

OUT = ROOT / "fusion_lab" / "data" / "gold_confirm" / "results"
PER = {"IS 2016-19": ("2016-01-01", "2019-12-31"), "OOS 2020-05/26": ("2020-01-01", "2026-05-10"),
       "Tresor 05-10/26": ("2026-05-11", "2026-11-10"), "Gesamt": ("2016-01-01", "2026-11-10")}


def load() -> pd.DataFrame:
    d = pd.read_pickle(OUT / "ctnl_live_set.pkl")
    d = d[d["spike"] >= SPIKE_MIN_ATR].copy()
    s = pd.read_parquet(macro_gate.FRAME, columns=["MACRO"])["MACRO"].dropna() * 100
    day = d["et"].dt.normalize()
    pos = s.index.searchsorted(pd.DatetimeIndex(day), side="left") - 1
    d["macro"] = np.where(pos >= 0, s.values[np.clip(pos, 0, None)], np.nan)
    gegen = ((d.direction > 0) & (d.macro <= macro_gate.SHORT_MAX)) | ((d.direction < 0) & (d.macro >= macro_gate.LONG_MIN))
    d["gesperrt"] = gegen
    return d.reset_index(drop=True)


def swap_r(d: pd.DataFrame, bps: float) -> pd.Series:
    """Swap in R: bps je Rollover (NY 17:00) x Einstiegskurs / Risiko-Distanz; Mittwoch zaehlt dreifach."""
    if bps <= 0:
        return pd.Series(0.0, index=d.index)
    et = d["et"].dt.tz_localize("UTC").dt.tz_convert("America/New_York")
    xt = d["xt"].dt.tz_localize("UTC").dt.tz_convert("America/New_York")
    nights = []
    for a, b in zip(et, xt):
        rolls = pd.date_range(a.normalize() + pd.Timedelta(hours=17), b, freq="D")
        rolls = rolls[(rolls > a) & (rolls.dayofweek < 5)]
        nights.append(sum(3 if x.dayofweek == 2 else 1 for x in rolls))
    price = d["entry_live"] if "entry_live" in d else d["entry_backtest"]
    return pd.Series(np.array(nights) * bps / 1e4 * price.values / d["effective_risk"].values, index=d.index)


def kill_switch_mask(d: pd.DataFrame, shadow_path: Path) -> pd.Series:
    """True = Trade waere wegen aktivem CTNL-Kill-Switch NICHT eroeffnet worden."""
    from gold_smc_htf_ltf.live_signal import CTNL_KILL_SWITCH_DD_THRESHOLD as THR, FK_RISK_CONT, FK_RISK_REV
    sh = pd.read_pickle(shadow_path)
    sh = sh[sh["gehandelt"]]  # live seit 30.09.: nur der gehandelte Satz (Ribbon beide Beine, Spike auf Rev)
    for c in ("entry_time", "exit_time"):
        t = pd.to_datetime(sh[c], utc=True)
        sh[c] = t.dt.tz_localize(None)
    sh["risk"] = np.where(sh["leg"] == "cont", FK_RISK_CONT, FK_RISK_REV)
    sh = sh.dropna(subset=["r"]).sort_values("exit_time")
    en, ex, rr = sh["entry_time"].values, sh["exit_time"].values, (sh["r"] * sh["risk"]).values
    grid = pd.DatetimeIndex(sorted(set(pd.date_range(d.et.min().normalize(), d.et.max(), freq="D")) | set(d.et)))
    active, state = {}, False
    for t in grid:
        tv = np.datetime64(t)
        w = (en >= np.datetime64(t - pd.Timedelta(days=90))) & (ex <= tv)
        if w.any():
            eq = np.cumprod(1 + rr[w])
            dd = float((eq / np.maximum.accumulate(np.maximum(eq, 1.0)) - 1).min())
            dd = min(dd, 0.0)
        else:
            dd = 0.0
        if not state and dd <= THR:
            state = True
        elif state and dd >= THR * 0.5:
            state = False
        active[t] = state
    return d["et"].map(active).fillna(False).astype(bool)


def tstat(r):
    return float(r.mean() / r.std(ddof=1) * np.sqrt(len(r))) if len(r) > 2 else float("nan")


def perm_p(r_all: pd.Series, keep: pd.Series, n=10000, seed=5) -> float:
    k = int((~keep).sum())
    if k < 3:
        return float("nan")
    obs = r_all[keep].mean()
    rng = np.random.default_rng(seed)
    sims = np.array([np.delete(r_all.values, rng.choice(len(r_all), k, replace=False)).mean() for _ in range(n)])
    return float((sims >= obs).mean())


def backtest(d: pd.DataFrame, risk: float, equity0: float) -> dict:
    """Taegliche Verzinsung: Tages-PnL = Summe(R x risk) der an dem Tag geschlossenen Trades, auf das
    Tageseroeffnungs-Equity. Ueberlappende Trades nutzen dasselbe Equity (wie live)."""
    r = d.set_index("xt")["r"]
    daily = (r * risk).groupby(r.index.normalize()).sum()
    idx = pd.bdate_range(d["et"].min().normalize(), d["xt"].max().normalize())
    daily = daily.reindex(idx, fill_value=0.0)
    eq = equity0 * (1 + daily).cumprod()
    dd = eq / eq.cummax() - 1
    yrs = len(idx) / 252
    cagr = (eq.iloc[-1] / equity0) ** (1 / yrs) - 1
    sharpe = daily.mean() / daily.std() * np.sqrt(252)
    neg = daily[daily < 0]
    sortino = daily.mean() / np.sqrt((neg ** 2).sum() / len(daily)) * np.sqrt(252)
    under = dd < 0
    runs = (under != under.shift()).cumsum()
    longest = int(under.groupby(runs).sum().max())
    monthly = (1 + daily).resample("ME").prod() - 1
    yearly = (1 + daily).resample("YE").prod() - 1
    wins, losses = d.r[d.r > 0], d.r[d.r <= 0]
    mc = run_monte_carlo(daily, initial_equity=equity0, block_size=20, n_sims=2000, seed=42)
    s = mc["summary"] if isinstance(mc, dict) and "summary" in mc else mc
    mdd = np.abs(np.asarray(s["max_drawdown_pct"]))
    return {
        "trades": len(d), "trades_pro_jahr": round(len(d) / yrs, 1), "long_%": round((d.direction > 0).mean() * 100),
        "trefferquote_%": round((d.r > 0).mean() * 100, 1), "avg_R": round(d.r.mean(), 3),
        "avg_gewinn_R": round(wins.mean(), 2), "avg_verlust_R": round(losses.mean(), 2),
        "profit_factor": round(wins.sum() / -losses.sum(), 2), "summe_R": round(d.r.sum(), 1),
        "t_wert": round(tstat(d.r), 2),
        "endkapital": round(eq.iloc[-1], 0), "rendite_gesamt_%": round((eq.iloc[-1] / equity0 - 1) * 100, 1),
        "CAGR_%": round(cagr * 100, 2), "sharpe": round(sharpe, 2), "sortino": round(sortino, 2),
        "max_DD_%": round(dd.min() * 100, 2), "calmar": round(cagr / -dd.min(), 2),
        "laengste_DD_tage": longest, "schlechtester_monat_%": round(monthly.min() * 100, 2),
        "bester_monat_%": round(monthly.max() * 100, 2), "monate_positiv_%": round((monthly > 0).mean() * 100),
        "jahre_positiv": f"{int((yearly > 0).sum())}/{len(yearly)}",
        "MC_DD_median_%": round(float(np.median(mdd)), 2), "MC_DD_95_%": round(float(np.percentile(mdd, 95)), 2),
        "MC_P(DD>10%)": round(float((mdd > 10).mean()), 3),
        "_yearly": (yearly * 100).round(2), "_eq": eq,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--equity", type=float, default=99_650.0)
    ap.add_argument("--risk", type=float, default=0.01)
    ap.add_argument("--swap-bps", type=float, default=1.5)
    ap.add_argument("--killswitch", action="store_true")
    a = ap.parse_args()
    d = load()
    d["r_brutto_swap"] = d["r"]
    d["swap_R"] = swap_r(d, a.swap_bps)
    print(f"Live-Set: {len(d)} Trades {d.et.min():%Y-%m-%d} .. {d.et.max():%Y-%m-%d}, ohne MACRO-Wert: "
          f"{d.macro.isna().sum()}; Swap {a.swap_bps} bps/Nacht = Ø {d.swap_R.mean():.3f} R je Trade")
    d["ks"] = kill_switch_mask(d, OUT / "ctnl_ks_shadow.pkl") if a.killswitch else False
    if a.killswitch:
        k = d[d.ks]
        print(f"Kill-Switch sperrt {len(k)} Trades (Ø {k.r.mean():+.2f} R, Summe {k.r.sum():+.1f} R), "
              f"davon {int(k.gesperrt.sum())} auch makro-gesperrt")
        print(k.groupby(k.et.dt.year).r.agg(["count", "sum"]).round(1).T.to_string())
    print("\n1) Sperre auf dem Live-Set (gesperrte gegen behaltene Trades, vor Swap)")
    rows = []
    for name, (a_, b_) in PER.items():
        x = d[(d.et >= a_) & (d.et <= b_ + " 23:59")]
        for side, nm in ((0, "beide"), (1, "long"), (-1, "short")):
            y = x if side == 0 else x[x.direction == side]
            g, k = y[y.gesperrt], y[~y.gesperrt]
            rows.append({"periode": name, "seite": nm, "n": len(y), "R_basis": round(y.r.mean(), 3),
                         "n_gesperrt": len(g), "R_gesperrt": round(g.r.mean(), 3) if len(g) else None,
                         "R_behalten": round(k.r.mean(), 3), "p_zufall": round(perm_p(y.r, ~y.gesperrt), 4)})
    t1 = pd.DataFrame(rows)
    print(t1.to_string(index=False))
    t1.to_csv(OUT / "ctnl_live_macro_veto.csv", index=False)
    net = d.assign(r=d["r"] - d["swap_R"])
    print(f"\n2) Backtest 2016-heute, {a.risk:.0%} Risiko je Trade, Startkapital {a.equity:,.0f}, "
          f"Kosten 2,01 bps + Swap {a.swap_bps} bps/Nacht")
    var = {"Basis (Ribbon+Spike)": pd.Series(True, index=net.index), "mit Makro-Sperre": ~net.gesperrt}
    if a.killswitch:
        var = {"Basis": pd.Series(True, index=net.index), "+ Kill-Switch": ~net.ks,
               "+ Makro-Sperre": ~net.gesperrt, "+ Kill-Switch + Makro (LIVE)": ~net.ks & ~net.gesperrt}
    res = {k: backtest(net[m], a.risk, a.equity) for k, m in var.items()}
    tab = pd.DataFrame({k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")} for k, v in res.items()})
    print(tab.to_string())
    yr = pd.DataFrame({k: v["_yearly"] for k, v in res.items()})
    yr.index = yr.index.year
    print("\nJahresrendite %:\n", yr.to_string())
    suf = "_ks" if a.killswitch else ""
    tab.to_csv(OUT / f"ctnl_live_backtest_1pct{suf}.csv")
    yr.to_csv(OUT / f"ctnl_live_backtest_1pct{suf}_jahre.csv")


if __name__ == "__main__":
    main()
