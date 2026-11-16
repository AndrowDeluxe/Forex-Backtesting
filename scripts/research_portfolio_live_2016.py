"""Gesamtportfolio-Backtest je Konto und je Bein, seit 2016, reale Kosten, aktuelle Live-Risiken.

Nutzerauftrag 2026-11-16 (Plan: ~/.claude/plans/shimmering-stargazing-candy.md).
Konten: ek (Tickmill, EUR), fk (BeyondIQ 17764), ttp (504072729), iq (BeyondIQ 16054).

Trades je Bein aus den vorhandenen Generatoren (nur Startdaten auf 2016 gesetzt):
  ORB / Gold ASB / CLS          research_fk_gesamtportfolio_2026 (Kosten je Broker via research_live_legs)
  trend_pullback / gold_silver  research_live_legs (Engine-Replay, halbe Kosten je Seite)
  ou_modell / btc_ema_cross     research_live_legs (OU mit gemessenen Kosten + Swap, BTC Annahmen)
  ctnl_reversal                 research_ctnl_macro_live (Ribbon, Spike, Makro-Sperre, Kill-Switch, Swap),
                                Kosten von TTP 2,01 bps auf den Broker umgerechnet, EK max. 1 offen
Swap (Annahme, nicht gemessen) fuer mehrtaegige Beine: SWAP_BPS je Nacht (NY 17:00), Mittwoch 3x.

Konto-Simulation: Risiko je Trade = Live-% x realisierte Equity beim Einstieg, Deckel je Trade und
offenes Risiko je Konto, EK mit Mindestlot-Aufrundung. Kontogrenzen werden NICHT als Stopp simuliert,
sondern ausgewiesen (erster Bruchtag, P(Bruch) aus Monte Carlo).

Aufruf: python scripts/research_portfolio_live_2016.py ek|fk|ttp|iq|alle [--refresh]
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO), str(REPO / "scripts"), str(REPO / "ou_paper_backtest")]
import research_ctnl_macro_live as cm  # noqa: E402
import research_fk_gesamtportfolio_2026 as fk  # noqa: E402
import research_live_legs as L  # noqa: E402
from monte_carlo import run_monte_carlo  # noqa: E402

START, END = "2016-01-01", "2026-11-01"
OUT = REPO / "portfolio_construction" / "results" / "live_2016"
SWAP_BPS = 1.5
EURUSD = 1.08          # EK-Umrechnung USD -> EUR fuer die Mindestlot-Rechnung (Annahme, konstant)
CTNL_REF_BPS = 2.01    # Kosten, mit denen das CTNL-Live-Set gerechnet ist

# FK/BeyondIQ als vierter Broker (gemessene Werte aus research_fk_gesamtportfolio_2026)
L.BROKERS["fk"] = {"xau_bps": 0.79, "eurusd_rt_pips": 1.30, "idx_pts": {"SP500": 0.40, "US30": 3.20, "NASDAQ": 1.00},
                   "ou_cost": None, "ctnl_cap": 2, "legs": [], "tp_markets": []}
# Gold ausserhalb des ASB-Fensters: Tickmill ganztaegig gemessen 1,07 bps (ctnl-kostenvalidierung Befund 3)
GOLD_ALLDAY_BPS = {"ttp": 2.08, "iq": 0.86, "tickmill": 1.07, "fk": 0.79}

# --- Live-Konfiguration je Konto (Stand 16.11.2026, aus den Bridges gelesen) ---------------------
ACCOUNTS = {
    "ek": dict(broker="tickmill", ccy="EUR", equity=2_520.83, dd_limit=0.45, daily_limit=None, open_cap=0.30,
               trade_cap=0.05, minlot=True, cls_mult=False, tp_markets=["GOLD", "SILVER", "CHFJPY", "USDJPY"],
               risk={"gold_asb": 0.0352, "btc_ema_cross": 0.0352, "gold_silver": 0.0352, "trend_pullback": 0.0220,
                     "cls_practical": 0.0066, "ctnl_reversal": 0.15 / 100 / 8, "orb_sp500": 0.0036,
                     "orb_nasdaq": 0.0036, "ou_modell": 0.0037}),
    "fk": dict(broker="fk", ccy="USD", equity=99_648.87, dd_limit=0.05, daily_limit=None, open_cap=0.05,
               trade_cap_abs=500.0, minlot=False, cls_mult=False, tp_markets=[],
               risk={"orb_sp500": 0.00125, "orb_nasdaq": 0.00125, "gold_asb": 0.00121, "cls_practical": 0.00288,
                     "ctnl_reversal": 0.00038, "gold_silver": 0.0020}),
    "ttp": dict(broker="ttp", ccy="USD", equity=99_769.78, dd_limit=0.07, daily_limit=0.03, open_cap=0.035,
                trade_cap=0.01, minlot=False, cls_mult=True, tp_markets=["GOLD", "SILVER", "CHFJPY", "USDJPY"],
                risk={"gold_asb": 0.0060, "cls_practical": 0.0015, "trend_pullback": 0.0010, "ctnl_reversal": 0.0010,
                      "ou_modell": 0.0005, "orb_sp500": 0.00075, "orb_nasdaq": 0.0010}),
    "iq": dict(broker="iq", ccy="USD", equity=97_621.51, dd_limit=0.06, daily_limit=None, open_cap=0.03,
               trade_cap=0.01, minlot=False, cls_mult=True, tp_markets=["GOLD", "SILVER", "CHFJPY", "USDJPY"],
               risk={"gold_asb": 0.00667, "cls_practical": 0.00333, "trend_pullback": 0.00167,
                     "ctnl_reversal": 0.00154, "orb_sp500": 0.00111, "orb_nasdaq": 0.00111}),
}
MULTIDAY = {"gold_silver", "trend_pullback"}   # Swap hier ergaenzt (CTNL: im Live-Set, OU/BTC: im Generator)


# ================================================================== Trades je Bein
def _configure(broker: str) -> None:
    L.H0, L.DATA_START, L.END = START, START, END
    L._set_broker(broker)
    fk.ORB_M15_START = fk.ORB_M1_START = "2016-07-28"   # vorhandener M1-Cache-Anker
    fk.CLS_START = START


def _patch_engine_replay() -> None:
    """research_live_legs._engine_replay um den Einstiegskurs ergaenzen (fuer den Swap in R)."""
    orig = L._engine_replay

    def wrapped(trades, leg, bps, unit):
        out = orig(trades, leg, bps, unit)
        if not out.empty:
            d = trades["direction"].astype(int).to_numpy()
            e = trades["entry_price"].to_numpy(float) * (1 + d * bps / 2e4)
            sl = trades["entry_price"].to_numpy(float) - d * trades["initial_risk"].to_numpy(float)
            out["entry_px"] = e[d * (e - sl) > 0]
        return out
    L._engine_replay = wrapped


def _swap_nights(et: pd.Series, xt: pd.Series) -> np.ndarray:
    a = pd.to_datetime(et).dt.tz_localize("UTC").dt.tz_convert("America/New_York")
    b = pd.to_datetime(xt).dt.tz_localize("UTC").dt.tz_convert("America/New_York")
    out = []
    for x, y in zip(a, b):
        rolls = pd.date_range(x.normalize() + pd.Timedelta(hours=17), y, freq="D")
        rolls = rolls[(rolls > x) & (rolls.dayofweek < 5)]
        out.append(sum(3 if r.dayofweek == 2 else 1 for r in rolls))
    return np.array(out)


def _cls_rate_mult() -> pd.Series:
    from cls_practical.data import fetch_2y_yield_daily, fetch_eurusd_entry_tf_berlin, fetch_rate_instrument_m5_berlin
    from cls_practical.rates import compute_combined_rate_risk_multiplier
    from strategy.cls_advanced import compute_daily_features
    e = fetch_eurusd_entry_tf_berlin("M5", START, END)
    m = compute_combined_rate_risk_multiplier(fetch_rate_instrument_m5_berlin("BUND", START, END),
                                              fetch_rate_instrument_m5_berlin("USTBOND", START, END),
                                              fetch_2y_yield_daily("DE02Y"), fetch_2y_yield_daily("US02Y"),
                                              compute_daily_features(e)["direction"])
    m = pd.Series(m) if not isinstance(m, pd.Series) else m
    m.index = pd.to_datetime(m.index)
    if m.index.tz is not None:
        m.index = m.index.tz_localize(None)
    return m.groupby(m.index.normalize()).last()


def ctnl_for(acc: str) -> pd.DataFrame:
    d = cm.load()
    d["ks"] = cm.kill_switch_mask(d, cm.OUT / "ctnl_ks_shadow.pkl")
    d = d[~d.gesperrt & ~d.ks].copy()
    bps = GOLD_ALLDAY_BPS[ACCOUNTS[acc]["broker"]]
    d["r"] = d["r"] + (CTNL_REF_BPS - bps) / 1e4 * d["entry_live"] / d["effective_risk"] - cm.swap_r(d, SWAP_BPS)
    d = d.sort_values("et")
    if acc == "ek":   # Live-Deckel EK: max. 1 offene ctnl_reversal-Position
        keep, open_until = [], pd.Timestamp.min
        for et, xt in zip(d.et, d.xt):
            keep.append(et >= open_until)
            if keep[-1]:
                open_until = xt
        d = d[np.array(keep)]
    return pd.DataFrame({"leg": "ctnl_reversal", "entry_time": d.et.values, "exit_time": d.xt.values,
                         "r": d.r.values, "exit_reason": d.exit_reason.values, "stop_px": d.effective_risk.values,
                         "unit_usd": L.UNIT_USD["XAU"]})


def build_trades(acc: str, refresh: bool = False) -> pd.DataFrame:
    p = OUT / f"{acc}_trades.parquet"
    if p.exists() and not refresh:
        return pd.read_parquet(p)
    cfg = ACCOUNTS[acc]
    _configure(cfg["broker"])
    _patch_engine_replay()
    legs, parts = set(cfg["risk"]), []
    print(f"=== {acc}: Beine {sorted(legs)}", flush=True)
    if legs & {"orb_sp500", "orb_nasdaq"}:
        o = fk.orb_trades().assign(unit_usd=L.UNIT_USD["INDEX"])
        parts.append(o[o["leg"].isin(legs)].drop(columns=["spread_bps", "market"], errors="ignore"))
    if "gold_asb" in legs:
        parts.append(fk.gold_asb_trades("stoporder", liquidity="live").assign(unit_usd=L.UNIT_USD["XAU"]))
    if "cls_practical" in legs:
        c = fk.cls_trades().assign(unit_usd=L.UNIT_USD["EURUSD"])
        c["risk_mult"] = 1.0
        if cfg["cls_mult"]:
            m = _cls_rate_mult()
            c["risk_mult"] = pd.to_datetime(c["entry_time"]).dt.normalize().map(m).fillna(1.0).values
        parts.append(c)
    if "ctnl_reversal" in legs:
        parts.append(ctnl_for(acc))
    if "trend_pullback" in legs:
        L.BROKERS[cfg["broker"]]["tp_markets"] = cfg["tp_markets"]
        parts.append(L.trend_pullback_trades(cfg["broker"]))
    if "gold_silver" in legs:
        parts.append(L.gold_silver_trades(cfg["broker"]))
    if "btc_ema_cross" in legs:
        parts.append(L.btc_trades())
    if "ou_modell" in legs:
        parts.append(L.ou_trades(cfg["broker"]))
    t = pd.concat(parts, ignore_index=True)
    t["entry_time"], t["exit_time"] = fk._naive(t["entry_time"]), fk._naive(t["exit_time"])
    if "risk_mult" not in t:
        t["risk_mult"] = 1.0
    t["risk_mult"] = t["risk_mult"].fillna(1.0)
    md = t["leg"].isin(MULTIDAY) & t.get("entry_px", pd.Series(np.nan, index=t.index)).notna()
    if md.any():
        n = _swap_nights(t.loc[md, "entry_time"], t.loc[md, "exit_time"])
        t.loc[md, "r"] = t.loc[md, "r"] - n * SWAP_BPS / 1e4 * t.loc[md, "entry_px"] / t.loc[md, "stop_px"]
    t = t[(t["entry_time"] >= pd.Timestamp(START)) & t["r"].notna()].sort_values("entry_time").reset_index(drop=True)
    OUT.mkdir(parents=True, exist_ok=True)
    t.drop(columns=[c for c in t.columns if t[c].dtype == object and c not in ("leg", "exit_reason")]).to_parquet(p)
    return t


# ================================================================== Konto-Simulation
def simulate(acc: str, t: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Ereignisgetrieben: Risiko beim Einstieg aus realisierter Equity, PnL beim Ausstieg."""
    cfg = ACCOUNTS[acc]
    eq0 = cfg["equity"]
    ev = []
    for i, r in t.iterrows():
        ev.append((r.entry_time, 1, i))
        ev.append((max(r.exit_time, r.entry_time), 0, i))
    ev.sort(key=lambda x: (x[0], x[1]))          # Ausstiege vor Einstiegen zur gleichen Zeit
    eq, open_risk, taken = eq0, {}, {}
    blocked, bumped = 0, 0
    for ts, kind, i in ev:
        row = t.loc[i]
        if kind == 1:
            risk = cfg["risk"][row.leg] * eq * (row.risk_mult if cfg.get("cls_mult") else 1.0)
            if "trade_cap" in cfg:
                risk = min(risk, cfg["trade_cap"] * eq)
            if "trade_cap_abs" in cfg:
                risk = min(risk, cfg["trade_cap_abs"])
            if cfg["minlot"]:
                floor = row.stop_px * row.unit_usd / EURUSD
                if floor > risk:
                    if floor > cfg["trade_cap"] * eq:
                        blocked += 1
                        continue
                    risk, bumped = floor, bumped + 1
            if sum(open_risk.values()) + risk > cfg["open_cap"] * eq:
                blocked += 1
                continue
            open_risk[i] = risk
        elif i in open_risk:
            risk = open_risk.pop(i)
            pnl = risk * row.r
            eq += pnl
            taken[i] = (risk, pnl)
    tk = t.loc[list(taken)].copy()
    tk["risk_ccy"] = [taken[i][0] for i in tk.index]
    tk["pnl"] = [taken[i][1] for i in tk.index]
    return tk, {"blockiert_deckel": blocked, "mindestlot_angehoben": bumped}


def metrics(tk: pd.DataFrame, acc: str, extra: dict) -> tuple[dict, pd.Series, pd.DataFrame]:
    cfg = ACCOUNTS[acc]
    eq0 = cfg["equity"]
    pnl = tk.groupby(pd.to_datetime(tk["exit_time"]).dt.normalize())["pnl"].sum()
    idx = pd.bdate_range(pd.Timestamp(START), pd.Timestamp(END))
    pnl = pnl.reindex(idx, fill_value=0.0)
    eq = eq0 + pnl.cumsum()
    ret = pnl / eq.shift(1).fillna(eq0)
    dd = eq / eq.cummax() - 1
    yrs = len(idx) / 252
    cagr = (eq.iloc[-1] / eq0) ** (1 / yrs) - 1
    neg = ret[ret < 0]
    under = dd < 0
    runs = (under != under.shift()).cumsum()
    monthly = (1 + ret).resample("ME").prod() - 1
    yearly = (1 + ret).resample("YE").prod() - 1
    r = tk["r"]
    w, l = r[r > 0], r[r <= 0]
    mc = run_monte_carlo(ret, initial_equity=eq0, block_size=20, n_sims=2000, seed=42)
    s = mc["summary"] if isinstance(mc, dict) and "summary" in mc else mc
    mdd = np.abs(np.asarray(s["max_drawdown_pct"]))
    lim = cfg["dd_limit"] * 100
    # P(Bruch binnen 12 Monaten): 5.000 Block-Bootstrap-Pfade a 252 Tage (Block 20), Trailing vom Pfad-Hoch
    rng = np.random.default_rng(7)
    rv = ret.to_numpy()
    nb = 252 // 20 + 1
    hits = 0
    for _ in range(5000):
        st = rng.integers(0, len(rv) - 20, nb)
        path = np.concatenate([rv[s:s + 20] for s in st])[:252]
        e = np.cumprod(1 + path)
        hits += (e / np.maximum.accumulate(np.maximum(e, 1.0)) - 1).min() <= -cfg["dd_limit"]
    p12 = hits / 5000
    # ohne Zinseszins: festes Risiko auf das Startkapital
    fix = (tk["r"] * tk["leg"].map(cfg["risk"]) * (tk["risk_mult"] if cfg.get("cls_mult") else 1.0)).sum() / yrs * 100
    breach = dd[dd <= -cfg["dd_limit"]]
    daily_breach = ret[ret <= -cfg["daily_limit"]] if cfg["daily_limit"] else pd.Series(dtype=float)
    m = {
        "trades": len(tk), "trades_pro_jahr": round(len(tk) / yrs, 1), "trefferquote_%": round((r > 0).mean() * 100, 1),
        "avg_R": round(r.mean(), 3), "avg_gewinn_R": round(w.mean(), 2), "avg_verlust_R": round(l.mean(), 2),
        "profit_factor": round(w.sum() / -l.sum(), 2), "summe_R": round(r.sum(), 1),
        "t_wert": round(cm.tstat(r), 2), "startkapital": round(eq0, 0), "endkapital": round(eq.iloc[-1], 0),
        "rendite_gesamt_%": round((eq.iloc[-1] / eq0 - 1) * 100, 1), "CAGR_%": round(cagr * 100, 2),
        "sharpe": round(ret.mean() / ret.std() * np.sqrt(252), 2),
        "sortino": round(ret.mean() / np.sqrt((neg ** 2).sum() / len(ret)) * np.sqrt(252), 2),
        "max_DD_%": round(dd.min() * 100, 2), "calmar": round(cagr / -dd.min(), 2) if dd.min() < 0 else None,
        "laengste_DD_tage": int(under.groupby(runs).sum().max()),
        "schlechtester_tag_%": round(ret.min() * 100, 2),
        "schlechtester_monat_%": round(monthly.min() * 100, 2), "bester_monat_%": round(monthly.max() * 100, 2),
        "monate_positiv_%": round((monthly > 0).mean() * 100), "jahre_positiv": f"{int((yearly > 0).sum())}/{len(yearly)}",
        "MC_DD_median_%": round(float(np.median(mdd)), 2), "MC_DD_95_%": round(float(np.percentile(mdd, 95)), 2),
        "rendite_pa_ohne_zinseszins_%": round(fix, 2),
        "kontogrenze_DD_%": lim, "MC_P(Bruch_12M)": round(p12, 3),
        "MC_P(Bruch_ueber_11J)": round(float((mdd > lim).mean()), 3),
        "erster_Bruch_hist": str(breach.index[0].date()) if len(breach) else "nie",
        "Tageslimit_verletzt": (f"{len(daily_breach)}x, zuerst {daily_breach.index[0].date()}"
                                if len(daily_breach) else ("nie" if cfg["daily_limit"] else "-")),
        **extra,
    }
    # je Bein
    legs = []
    total = tk["pnl"].sum()
    for leg, g in tk.groupby("leg"):
        lp = g.groupby(pd.to_datetime(g["exit_time"]).dt.normalize())["pnl"].sum().reindex(idx, fill_value=0.0)
        lr = lp / eq.shift(1).fillna(eq0)
        legs.append({"bein": leg, "ab": str(pd.to_datetime(g.entry_time).min().date()),
                     "risiko_%": round(cfg["risk"][leg] * 100, 3), "trades": len(g),
                     "trefferquote_%": round((g.r > 0).mean() * 100, 1), "avg_R": round(g.r.mean(), 3),
                     "summe_R": round(g.r.sum(), 1), "pnl": round(g.pnl.sum(), 0),
                     "anteil_%": round(g.pnl.sum() / total * 100, 1) if total else None,
                     "sharpe_bein": round(lr.mean() / lr.std() * np.sqrt(252), 2) if lr.std() > 0 else None})
    legs = pd.DataFrame(legs).sort_values("pnl", ascending=False)
    yr = (yearly * 100).round(2)
    yr.index = yr.index.year
    corr = pd.DataFrame({leg: g.groupby(pd.to_datetime(g["exit_time"]).dt.normalize())["pnl"].sum()
                         .reindex(idx, fill_value=0.0) for leg, g in tk.groupby("leg")}).corr().round(2)
    return m, yr, legs, corr


def run(acc: str, refresh: bool) -> dict:
    t = build_trades(acc, refresh)
    tk, extra = simulate(acc, t)
    m, yr, legs, corr = metrics(tk, acc, extra)
    print(f"\n######## Konto {acc.upper()} ({ACCOUNTS[acc]['ccy']}) ########")
    print(pd.Series(m).to_string())
    print("\nJe Bein:\n", legs.to_string(index=False))
    print("\nJahresrendite %:\n", yr.to_string())
    print("\nKorrelation Tages-PnL:\n", corr.to_string())
    legs.to_csv(OUT / f"{acc}_beine.csv", index=False)
    yr.to_csv(OUT / f"{acc}_jahre.csv")
    corr.to_csv(OUT / f"{acc}_korrelation.csv")
    return {"m": m, "yr": yr}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("konto", choices=[*ACCOUNTS, "alle"])
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()
    L._chunked_dukascopy_fetch()
    accs = list(ACCOUNTS) if a.konto == "alle" else [a.konto]
    res = {acc: run(acc, a.refresh) for acc in accs}
    OUT.mkdir(parents=True, exist_ok=True)
    if len(res) > 1:
        tab = pd.DataFrame({k.upper(): v["m"] for k, v in res.items()})
        yr = pd.DataFrame({k.upper(): v["yr"] for k, v in res.items()})
        print("\n######## Alle Konten ########\n", tab.to_string(), "\n\nJahresrendite %:\n", yr.to_string())
        tab.to_csv(OUT / "alle_konten.csv")
        yr.to_csv(OUT / "alle_konten_jahre.csv")


if __name__ == "__main__":
    main()
