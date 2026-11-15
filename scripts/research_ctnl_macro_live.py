"""CTNL-Reversal Live-Set (Ribbon + Spike >= 0,75 ATR, Lag-Replay) mit/ohne Makro-Sperre, 2016-heute,
1 % Risiko je Trade auf das Konto (taeglich verzinst). 15.11.2026, Nutzerauftrag.

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
    a = ap.parse_args()
    d = load()
    print(f"Live-Set: {len(d)} Trades {d.et.min():%Y-%m-%d} .. {d.et.max():%Y-%m-%d}, ohne MACRO-Wert: {d.macro.isna().sum()}")
    print("\n1) Sperre auf dem Live-Set (gesperrte gegen behaltene Trades)")
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
    print(f"\n2) Backtest 2016-heute, {a.risk:.0%} Risiko je Trade, Startkapital {a.equity:,.0f}")
    res = {"Basis (Ribbon+Spike)": backtest(d, a.risk, a.equity),
           "mit Makro-Sperre": backtest(d[~d.gesperrt], a.risk, a.equity)}
    tab = pd.DataFrame({k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")} for k, v in res.items()})
    print(tab.to_string())
    yr = pd.DataFrame({k: v["_yearly"] for k, v in res.items()})
    yr.index = yr.index.year
    print("\nJahresrendite %:\n", yr.to_string())
    tab.to_csv(OUT / "ctnl_live_backtest_1pct.csv")
    yr.to_csv(OUT / "ctnl_live_backtest_1pct_jahre.csv")


if __name__ == "__main__":
    main()
