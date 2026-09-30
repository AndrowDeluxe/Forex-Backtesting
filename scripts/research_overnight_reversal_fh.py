"""Overnight-Reversal in der ersten halben Stunde (US-Indizes) -- Nachbau.

Paper: Iwanaga/Sakemoto, "Does overnight return predict the first half-hour
return for U.S. market indices?" (SSRN 5807282, 5. August 2026). SPY 1-Min
(LSEG), 1996-2024. Kernbefund: R_FH = a + b*R_ON, b = -9.19 (t=-5.16,
R^2 3.8 %); Strategie eta = +R_FH wenn R_ON<0, sonst -R_FH (Gl. 6):
SPY 7.76 % p.a., SR 1.51 brutto, 4.83 % / SR 0.94 mit Bid-Ask.
ABER bereits im Paper: 2010-2024 nur b=-5.99, t=-1.90 (Tab. 4d).

Dieses Skript = Phase 3/4 des Standardprozesses: Definitionen 1:1 aus
Gl. (1), (2), (6), auf unseren Dukascopy-Index-CFDs (SP500/NASDAQ/US30, M5,
America/New_York). Zuerst die Pflichtfrage aus dem EU-Open-Fall: lebt der
Effekt in UNSEREN Jahren noch, jahresweise, ohne das beste Jahr?

Preisdefinitionen (NY-Ortszeit, M5):
  P_c(t-1) = Close der 15:55-Bar des VORHERIGEN Handelstags (= Kurs 16:00)
  P_o(t)   = Open der 09:30-Bar
  P_fh(t)  = Close der 09:55-Bar (= Kurs 10:00)
  P_loh    = Close 14:55, P_lh = Close 15:25, P_c = Close 15:55
Tage ohne die jeweilige Bar (Feiertage, Halbtage) fallen raus -- kein
Vorwaerts-Fuellen. "Vorheriger Handelstag" = vorherige Zeile der Tabelle
der Tage MIT 09:30-Bar; hat dieser Tag keine 15:55-Bar (Halbtag), NaN.

Einheiten: Renditen in bps; b wird wie im Paper als "bps FH je % ON"
ausgewiesen (Paper-b -9.19 == -0.0919 in reinen Einheiten).

REIN LESEND. Kein Order-Pfad, keine Config-Aenderung.

Aufruf: python scripts/research_overnight_reversal_fh.py [--out <json>]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from ny_open_orb.data import fetch_m5  # noqa: E402
from scripts.research_eu_open_window import newey_west_t  # noqa: E402

NY = "America/New_York"
INSTRUMENTS = ("SP500", "NASDAQ", "US30")
START, END = "2016-07-28", "2026-09-29"
PAPER_END = pd.Timestamp("2024-12-31")
TD = 252
COSTS_BPS = (0.0, 0.5, 1.0, 1.5)


def load(instr: str) -> pd.DataFrame:
    df = fetch_m5(instr, START, END)
    idx = df.index
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    df = df.copy()
    df.index = idx.tz_convert(NY)
    df.columns = [c.lower() for c in df.columns]
    return df.sort_index()


def at(df: pd.DataFrame, hhmm: str, col: str) -> pd.Series:
    sel = df.between_time(hhmm, hhmm)
    s = sel[col].copy()
    s.index = sel.index.tz_localize(None).normalize()
    return s[~s.index.duplicated(keep="first")]


def build_days(df: pd.DataFrame) -> pd.DataFrame:
    o = at(df, "09:30", "open")
    d = pd.DataFrame({"p_o": o})
    d["p_o_lag"] = at(df, "09:35", "open").reindex(d.index)  # Entry eine M5-Bar spaeter
    d["p_fh"] = at(df, "09:55", "close").reindex(d.index)
    d["p_loh"] = at(df, "14:55", "close").reindex(d.index)
    d["p_lh"] = at(df, "15:25", "close").reindex(d.index)
    d["p_c"] = at(df, "15:55", "close").reindex(d.index)
    d = d[d.index.dayofweek < 5]
    d["p_c_prev"] = d["p_c"].shift(1)
    bps = 1e4
    d["r_on"] = (d["p_o"] / d["p_c_prev"] - 1) * bps
    d["r_fh"] = (d["p_fh"] / d["p_o"] - 1) * bps
    d["r_fh_lag"] = (d["p_fh"] / d["p_o_lag"] - 1) * bps
    d["r_m"] = (d["p_loh"] / d["p_fh"] - 1) * bps
    d["r_lh"] = (d["p_c"] / d["p_lh"] - 1) * bps
    # Plausibilitaets-Kappe: |R_ON| > 10 % = Datenfehler, nicht Markt
    d = d[(d["r_on"].abs() < 1000) | d["r_on"].isna()]
    return d


def ols(y: np.ndarray, x: np.ndarray, lags: int = 5) -> dict:
    """OLS y = a + b x mit Newey-West-t fuer b. b in 'bps je % ON'."""
    m = ~(np.isnan(y) | np.isnan(x))
    y, x = y[m], x[m]
    n = len(y)
    if n < 30:
        return {"n": n}
    X = np.column_stack([np.ones(n), x])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ beta
    XtX_inv = np.linalg.inv(X.T @ X)
    S = (X * e[:, None]).T @ (X * e[:, None]) / n
    for L in range(1, lags + 1):
        w = 1 - L / (lags + 1)
        G = (X[L:] * e[L:, None]).T @ (X[:-L] * e[:-L, None]) / n
        S += w * (G + G.T)
    V = n * XtX_inv @ S @ XtX_inv
    r2 = 1 - (e @ e) / ((y - y.mean()) @ (y - y.mean()))
    return {"n": n, "b_bps_per_pct": round(beta[1], 2),
            "t": round(beta[1] / np.sqrt(V[1, 1]), 2), "r2_pct": round(r2 * 100, 2)}


def strat(d: pd.DataFrame, col: str = "r_fh", cost: float = 0.0) -> pd.Series:
    """Gl. (6): long wenn R_ON<0, sonst short; netto 'cost' bps Round-Trip."""
    x = d.dropna(subset=["r_on", col])
    sign = np.where(x["r_on"] < 0, 1.0, -1.0)
    return pd.Series(sign * x[col] - cost, index=x.index)


def perf(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 20:
        return {"n": int(len(r))}
    ann = r.mean() * TD / 100  # bps -> % p.a.
    sd = r.std(ddof=1) * np.sqrt(TD) / 100
    eq = r.cumsum() / 100
    return {"n": int(len(r)), "bps_per_trade": round(r.mean(), 2), "ann_pct": round(ann, 2),
            "sharpe": round(ann / sd, 2) if sd else None, "t": round(newey_west_t(r.values), 2),
            "hit_pct": round((r > 0).mean() * 100, 1),
            "maxdd_pct": round(float((eq - eq.cummax()).min()), 2)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "Claude outputs" / "overnight_reversal_fh.json"))
    args = ap.parse_args()

    res: dict = {}
    for instr in INSTRUMENTS:
        d = build_days(load(instr))
        d = d.dropna(subset=["r_on", "r_fh"])
        out: dict = {"days": int(len(d)), "first": str(d.index[0].date()), "last": str(d.index[-1].date()),
                     "sd_r_on_pct": round(d["r_on"].std() / 100, 3)}

        # --- Tab. 1: Regressionen ---
        out["reg_full"] = {k: ols(d[k].values, d["r_on"].values / 100) for k in ("r_fh", "r_m", "r_lh")}
        ins, oos = d[d.index <= PAPER_END], d[d.index > PAPER_END]
        out["reg_fh_in_paper"] = ols(ins["r_fh"].values, ins["r_on"].values / 100)
        out["reg_fh_after_paper"] = ols(oos["r_fh"].values, oos["r_on"].values / 100)
        ex20 = d[d.index.year != 2020]
        out["reg_fh_ex2020"] = ols(ex20["r_fh"].values, ex20["r_on"].values / 100)
        # Tab. A4: Vorzeichen-Split
        out["reg_fh_on_pos"] = ols(d.loc[d.r_on > 0, "r_fh"].values, d.loc[d.r_on > 0, "r_on"].values / 100)
        out["reg_fh_on_neg"] = ols(d.loc[d.r_on < 0, "r_fh"].values, d.loc[d.r_on < 0, "r_on"].values / 100)

        # --- Jahresreihe ---
        out["by_year"] = {}
        for y, g in d.groupby(d.index.year):
            s = strat(g)
            out["by_year"][int(y)] = {**ols(g["r_fh"].values, g["r_on"].values / 100),
                                      "strat_ann_pct": round(s.mean() * TD / 100, 2),
                                      "strat_bps": round(s.mean(), 2)}

        # --- Strategie Gl. (6) ---
        out["strat"] = {}
        for c in COSTS_BPS:
            s = strat(d, cost=c)
            yrs = s.groupby(s.index.year).sum()
            best = int(yrs.idxmax())
            out["strat"][f"cost_{c}"] = {
                "full": perf(s), "ex2020": perf(s[s.index.year != 2020]),
                f"ex_best_year_{best}": perf(s[s.index.year != best]),
                "after_paper_2025+": perf(s[s.index > PAPER_END]),
                "since_2021": perf(s[s.index.year >= 2021]),
            }
        out["strat_lag_0935_cost_0"] = perf(strat(d, "r_fh_lag"))
        out["strat_lag_0935_cost_0_ex2020"] = perf(strat(d[d.index.year != 2020], "r_fh_lag"))

        # --- Konditionierung (nur ex-ante-Groessen) ---
        # Dukascopy-VIX beginnt erst 2022-10 -> stattdessen realisierte
        # 20-Tage-Vol der Close-zu-Close-Renditen, Stand VORTAG (ex ante).
        cc = d["p_c"].pct_change()
        v = cc.rolling(20, min_periods=15).std().shift(1)
        hi = v > v.expanding(250).median().shift(1)
        s0 = strat(d)
        out["cond_rv20_prev_hi"] = perf(s0[hi.reindex(s0.index).fillna(False)])
        out["cond_rv20_prev_lo"] = perf(s0[~hi.reindex(s0.index).fillna(True)])
        out["cond_rv20_prev_hi_ex2020"] = perf(s0[hi.reindex(s0.index).fillna(False) & (s0.index.year != 2020)])
        absr = d["r_on"].abs()
        big = absr > absr.expanding(250).quantile(2 / 3).shift(1)
        out["cond_big_on_top_tercile"] = perf(s0[big.reindex(s0.index).fillna(False)])
        out["cond_big_on_top_tercile_ex2020"] = perf(
            s0[big.reindex(s0.index).fillna(False) & (s0.index.year != 2020)])
        out["only_long_after_neg_on"] = perf(s0[d.loc[s0.index, "r_on"] < 0])
        out["only_short_after_pos_on"] = perf(s0[d.loc[s0.index, "r_on"] > 0])
        # --- Teilvariante "nur long nach negativem ON" (Tab. A4-Richtung) ---
        # Gegen "immer long in FH" stellen: sonst misst man nur die FH-Drift.
        neg = d[d["r_on"] < 0]
        out["always_long_fh"] = perf(d["r_fh"])
        out["always_long_fh_ex2020"] = perf(d.loc[d.index.year != 2020, "r_fh"])
        out["long_neg"] = {}
        for c in COSTS_BPS:
            s = neg["r_fh"] - c
            yrs = s.groupby(s.index.year).sum()
            best = int(yrs.idxmax())
            out["long_neg"][f"cost_{c}"] = {
                "full": perf(s), "ex2020": perf(s[s.index.year != 2020]),
                f"ex_best_year_{best}": perf(s[s.index.year != best]),
                "after_paper_2025+": perf(s[s.index > PAPER_END]),
                "since_2021": perf(s[s.index.year >= 2021])}
        out["long_neg_lag_0935"] = perf(neg["r_fh_lag"].dropna())
        out["long_neg_lag_0935_ex2020"] = perf(neg.loc[neg.index.year != 2020, "r_fh_lag"].dropna())
        out["long_neg_by_year_bps"] = {int(y): round(g["r_fh"].mean(), 2)
                                       for y, g in neg.groupby(neg.index.year)}
        out["long_pos_by_year_bps"] = {int(y): round(g["r_fh"].mean(), 2)
                                       for y, g in d[d.r_on > 0].groupby(d[d.r_on > 0].index.year)}
        # Gap-Groesse: kleine vs. grosse negative Gaps (Median-Split, ex post nur deskriptiv)
        med = neg["r_on"].median()
        out["long_neg_small_gap"] = perf(neg.loc[neg.r_on > med, "r_fh"])
        out["long_neg_big_gap"] = perf(neg.loc[neg.r_on <= med, "r_fh"])
        res[instr] = out

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
