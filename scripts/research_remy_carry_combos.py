"""Carry-Baustein (Remy-King A2) kombiniert mit vier Zusammenhaengen.

    python -m scripts.research_remy_carry_combos

Basis: Carry k=1 mit VIX-Risk-off (bester IS-Wert, research_remy_a2_carry.py).
K1 Daily-Edge Typ R (E2 S1 alle X4) nur in Carry-Richtung des Paars.
K2 Regimekarte: US-Wachstum faellt (g_up False, First Prints) -> halbe Groesse / flat.
K3 COT (Legacy, Non-Commercials, 156-Wochen-Index): Carry-Long-Waehrung > 80 oder
   Carry-Short-Waehrung < 20 (Trade ueberfuellt) -> halbe Groesse / flat.
K4 Zinskurven-Regime (US 2s10s, bestaetigt): Deflation (Bull Steepener) -> halb / flat.

Overfitting-Sperre `remy_a2_carry`, Regel seit 2026-11-10: auf IS bauen, OOS frei
ansehen (`oos_only`), Tresor (ab 10.05.2026) bleibt zu. Varianten werden gezaehlt.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from fusion_lab.filters.zinskurve_regime import confirmed, regime_series
from fusion_lab.macro_data.sources import cot_index
from htf_daily_trade import backtest_r as tr
from research_lock import deflated_sharpe
from scripts.remy_common import CURRENCIES, ccy_returns, fx_closes, rates, stats, vix
from scripts.research_remy_a2_carry import LOCK, daily_weights, pnl

COT_CODES = {"099741": "EA", "096742": "GB", "097741": "JP", "092741": "CH", "232741": "AU",
             "090741": "CA", "112741": "NZ"}
TYPR_FX = {"EURUSD": ("EA", "US"), "GBPUSD": ("GB", "US"), "AUDUSD": ("AU", "US"), "USDJPY": ("US", "JP")}
TYPR_VAR = ("E2", "S1", "alle", "X4")
MIN_GAP = 0.25


def on_days(s: pd.Series, index: pd.DatetimeIndex) -> pd.Series:
    """Wert je Handelstag aus dem letzten bekannten Stand VOR dem Tag."""
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s.reindex(s.index.union(index)).ffill().reindex(index).shift(1)


def growth_scale(index, off: float) -> pd.Series:
    lab = pd.read_parquet("fusion_lab/data/macro_regime/labels.parquet")["g_up"].astype(float)
    g = on_days(lab, index)
    return pd.Series(np.where(g == 0.0, off, 1.0), index=index)


def cot_indices(index) -> pd.DataFrame:
    d = pd.read_parquet("data_cache/remy/cot_legacy.parquet")
    d["date"] = pd.to_datetime(d["report_date_as_yyyy_mm_dd"]) + pd.Timedelta(days=3)  # Freitag veroeffentlicht
    d["net"] = pd.to_numeric(d["noncomm_positions_long_all"]) - pd.to_numeric(d["noncomm_positions_short_all"])
    out = {}
    for code, ccy in COT_CODES.items():
        net = d[d["cftc_contract_market_code"] == code].set_index("date")["net"].sort_index()
        out[ccy] = on_days(cot_index(net, 156), index)
    return pd.DataFrame(out)


def cot_scale(w: pd.DataFrame, idx: pd.DataFrame, off: float, hi: float = 80, lo: float = 20) -> pd.Series:
    crowded = pd.Series(False, index=w.index)
    for c in idx.columns:
        crowded |= ((w[c] > 0) & (idx[c] > hi)) | ((w[c] < 0) & (idx[c] < lo))
    return pd.Series(np.where(crowded, off, 1.0), index=w.index)


def curve_scale(index, off: float) -> pd.Series:
    reg = on_days(confirmed(regime_series(20), 5), index)
    return pd.Series(np.where(reg == "Deflation", off, 1.0), index=index)


def typr_trades() -> pd.DataFrame:
    data = {}
    for name in TYPR_FX:
        _, grid, cost = tr.MARKETS[name]
        x = tr.features(tr.load_market(name), grid)
        data[name] = (x, tr.signals(x), cost)
    return tr.run_variant(data, TYPR_VAR, pd.Timestamp("2026-10-09"), pd.Timestamp("2004-01-01"))


def carry_dir(trades: pd.DataFrame, pr: pd.DataFrame) -> pd.Series:
    """+1 = Trade in Carry-Richtung, -1 dagegen, 0 = Zinsabstand < MIN_GAP. Stand: Vormonatsende."""
    ends = pr.groupby(pr.index.to_period("M")).tail(1)
    out = []
    for t in trades.itertuples():
        d = pd.Timestamp(t.datum)
        prev = ends[ends.index < d.to_period("M").start_time]
        base, quote = TYPR_FX[t.markt]
        gap = prev[base].iloc[-1] - prev[quote].iloc[-1] if len(prev) else np.nan
        side = 1 if t.seite == "long" else -1
        out.append(0 if not abs(gap) >= MIN_GAP else int(np.sign(gap)) * side)
    return pd.Series(out, index=trades.index)


def r_stats(r: pd.Series) -> dict:
    n = len(r)
    m, sd = r.mean(), r.std(ddof=1)
    return {"n": n, "mean_r": m, "t": m / sd * np.sqrt(n) if n > 1 and sd > 0 else np.nan, "summe_r": r.sum()}


def main() -> None:
    pd.set_option("display.width", 200)
    closes = fx_closes()
    ret = ccy_returns(closes)
    pr = rates(ret.index, "policy_rate")
    vx = vix(ret.index)
    vix_cut = float(LOCK.is_only(vx).quantile(0.75))
    w = daily_weights(ret, pr, vx, 1, True, vix_cut)
    cot = cot_indices(ret.index)

    variants = {"Carry Basis": pd.Series(1.0, index=ret.index)}
    for off, lab in ((0.5, "halb"), (0.0, "flat")):
        variants[f"K2 Wachstum faellt -> {lab}"] = growth_scale(ret.index, off)
        variants[f"K3 COT ueberfuellt -> {lab}"] = cot_scale(w, cot, off)
        variants[f"K4 Deflation -> {lab}"] = curve_scale(ret.index, off)
    LOCK.log_trials(6, "Carry-Kombis K2-K4 je halb/flat (Regel 10.11.: OOS frei)")

    rows = {}
    for name, scale in variants.items():
        s = pnl(w.mul(scale.fillna(1.0), axis=0), ret, pr)
        a, b = stats(LOCK.is_only(s).iloc[1:]), stats(LOCK.oos_only(s))
        rows[name] = {"IS Sharpe": a["sharpe"], "IS t": a["t"], "IS MaxDD": a["maxdd"], "IS Rend.": a["ret_pa"],
                      "OOS Sharpe": b["sharpe"], "OOS t": b["t"], "OOS MaxDD": b["maxdd"], "OOS Rend.": b["ret_pa"],
                      "sr_d": a["sr_d"], "n": a["n"], "skew": a["skew"], "kurt": a["kurt"],
                      "aktiv %": float((scale.reindex(LOCK.is_only(s).index) == 1.0).mean() * 100)}
    tab = pd.DataFrame(rows).T
    var_sr = float(tab["sr_d"].astype(float).var())
    tab["IS DSR"] = [deflated_sharpe(r["sr_d"], int(r["n"]), LOCK.trials, r["skew"], r["kurt"], var_sr)
                     for _, r in tab.iterrows()]
    split = LOCK.split
    print(f"IS {split['is_start']}..{split['is_end']} | OOS bis {split['oos_end']} | Tresor zu | "
          f"Versuche gesamt {LOCK.trials}")
    cols = ["aktiv %", "IS Rend.", "IS Sharpe", "IS t", "IS MaxDD", "IS DSR", "OOS Rend.", "OOS Sharpe", "OOS t", "OOS MaxDD"]
    print(tab[cols].astype(float).round(2).to_string())

    print("\nOOS je Jahr (Summe log-Rendite), Basis vs. Kombis:")
    yearly = {}
    for name, scale in variants.items():
        s = LOCK.oos_only(pnl(w.mul(scale.fillna(1.0), axis=0), ret, pr))
        yearly[name[:24]] = s.groupby(s.index.year).sum()
    print(pd.DataFrame(yearly).round(3).to_string())

    # K1: Typ R in Carry-Richtung
    t = typr_trades()
    LOCK.log_trials(2, "K1 Typ R nur Carry-Richtung / ohne Gegen-Carry")
    t["dir"] = carry_dir(t, pr)
    t["datum"] = pd.to_datetime(t["datum"])
    t = t.set_index("datum").sort_index()
    t_is, t_oos = LOCK.is_only(t), LOCK.oos_only(t)
    rows = {}
    for name, f in (("Typ R alle FX", lambda d: d), ("K1 nur Carry-Richtung", lambda d: d[d["dir"] == 1]),
                    ("K1 ohne Gegen-Carry", lambda d: d[d["dir"] >= 0]), ("(nur Gegen-Carry)", lambda d: d[d["dir"] == -1])):
        a, b = r_stats(f(t_is)["r"]), r_stats(f(t_oos)["r"])
        rows[name] = {"IS n": a["n"], "IS Ø R": a["mean_r"], "IS t": a["t"], "OOS n": b["n"], "OOS Ø R": b["mean_r"],
                      "OOS t": b["t"]}
    print("\nK1 Daily-Edge Typ R (EURUSD, GBPUSD, AUDUSD, USDJPY; R je Trade):")
    print(pd.DataFrame(rows).T.astype(float).round(3).to_string())
    print(f"\nVersuche im Lock jetzt: {LOCK.trials}")


if __name__ == "__main__":
    main()
