"""FK Instant Funding -- Gesamtportfolio-Backtest 2026 mit realer Ausfuehrung.

Nutzerauftrag 2026-10-03: "Backteste das neue Gesamtportfolio auf dem FK
Funded Konto mit den aktualisierten Kosten und Versatz sowie der neusten
Ausfuehrungslogik fuer das Jahr 2026."

PORTFOLIO = was FKInstantFunding-MT5-Bridge heute live faehrt (config.py::
LIVE_LEGS): orb_sp500/orb_us30/orb_nasdaq, gold_asb, cls_practical,
ctnl_reversal. ctnl_continuation ist seit 2026-09-30 stillgelegt,
trend_pullback/gold_silver laufen nur noch im Paper-Bot.

AUSFUEHRUNG JE BEIN (aus dem Bridge-Code gelesen, nicht angenommen):
  ORB        ruhende Stop-Order am Level (orb_pending), Teilausstieg + Ziel als
             Broker-TP-Slices, Long-Order SP500/US30 liegt bis 16:00 (KEIN
             Storno bei Bruch nach unten = Live-Semantik "none"). Auf M1
             simuliert, weil M5 den Stop in der Fuell-Bar nicht pruefen kann.
  Gold ASB   Market-Order beim naechsten Slow-Lauf: ~30 Min. nach dem Label der
             Fuell-Bar, absoluter Signal-SL, Restlaufzeit-Gate, 0,50R-Detektor,
             Zeit-Exit 30 Min. spaeter. Zusaetzlich Variante "Stop-Order 1,5x
             Range / Storno 03:00 NY" (gebaut, Deploy wartet auf den Nutzer).
  CLS        Market-Order beim naechsten 5-Min-Lauf (Lag 1 M5-Bar ab Signal-
             Bar-Schluss), absoluter SL, 5-Pip-Boden, Restlaufzeit-Gate,
             0,50R-Detektor. Ziel liegt NICHT beim Broker (target=None) -> TP-
             und Zeit-Exits ebenfalls einen Lauf spaeter zum Marktkurs.
             Der Tages-Zins-Multiplikator wirkt live NICHT auf die Groesse
             (risk_dollars ist fix) -- hier deshalb rohes R.
  CTNL rev.  Signal-Kappung 2 (Paper-Bot, auf der UNGEFILTERTEN Liste), dann
             Lag 1 M15-Bar, Restlaufzeit-Gate, 0,50R-Detektor, Ribbon-Gate,
             Spike-Filter >= 0,75 ATR, Live-Deckel 2 gegen offene Positionen.
             TP 5R/max_hold per Re-Scan -> Exit einen Bar spaeter zum Open.

SIZING (fk_instant_funding/paper_bot.py + Bridge-sizing.py):
  risk$ = CAPITAL_WEIGHT x LEG_RISK_PCT x Equity, gedeckelt auf 0,5 % des
  Startkapitals. XAUUSD-Beine mit echter Lot-Rundung (0,01 Lot, abrunden,
  Anhebung auf Mindestlot solange <= 500 $). EURUSD/Indizes: Rundung
  vernachlaessigbar (Risiko >> Lot-Schritt).

KOSTEN (BeyondIQCapital, gemessen -- knowledge/_data/broker_spreads_*.json):
  XAUUSD 33 Points RT = 0,79 bps | EURUSD 1,30 Pips RT | SPX500 0,40 /
  US30 3,20 / NAS100 1,00 Punkte Spread + Live-Slippage 0,45/0,30 bps.

REGELN: EOD-Trailing-Drawdown 5 % (Kill-Switch sperrt neue Entries, Freigabe
bei -2,5 %), Konsistenzregel 30 %, CTNL-Kill-Switch -6,6 % (stand-alone).

NICHT modelliert: Swap/Finanzierung (CTNL haelt bis 96 h), Requotes/Rejects,
Scan-Ausfaelle, Wochenend-/23-Uhr-Sperre (betrifft fast nur CTNL-Signale).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "ou_paper_backtest"))

import fk_instant_funding.paper_bot as pb  # noqa: E402

Y0 = pd.Timestamp("2026-01-01")
END = "2026-10-02"
# Datenstart je Bein (Vorlauf fuer Indikatoren). Ueberschreibbar, damit
# research_fk_gewichtung_mc_wf.py dieselben Funktionen ab 2019 nutzen kann.
ORB_M15_START, ORB_M1_START = "2024-06-01", "2025-12-15"
CLS_START = "2024-11-01"
CTNL_START = "2025-06-01"
START_EQUITY = 100_000.0
OUT = REPO / "knowledge" / "_data" / "fk_gesamtportfolio_2026.json"
TRADES_CSV = REPO / "portfolio_construction" / "results" / "fk_gesamtportfolio_2026_trades.csv"

# --- gemessene FK/BeyondIQ-Kosten -------------------------------------------
XAU_BPS = 0.79
EURUSD_RT_PIPS = 1.30
INDEX_SPREAD_PTS = {"SP500": 0.40, "US30": 3.20, "NASDAQ": 1.00}
ORB_ENTRY_SLIP_BPS, ORB_EXIT_SLIP_BPS = 0.45, 0.30   # Live-Fills Funded, siehe research_orb_exit_grid.py

LAG_GOLD_ASB_MIN = 30
LAG_CLS_BARS = 1
LAG_CTNL_BARS = 1
NASDAQ_RULE = "sl"        # vor 2026-10-04: "none"
CTNL_LIVE_CAP = 2          # Live-Deckel offener ctnl_reversal-Positionen (EK: 1)
GATE_R = 0.50
MIN_LOT_XAU = 0.01
OZ_PER_LOT = 100.0


def _naive(s):
    s = pd.to_datetime(s)
    if isinstance(s, pd.Series):
        return s.dt.tz_convert("UTC").dt.tz_localize(None) if s.dt.tz is not None else s
    return s.tz_convert("UTC").tz_localize(None) if s.tz is not None else s


def _stats(r: pd.Series) -> dict:
    r = pd.Series(r).dropna()
    if r.empty:
        return {"n": 0}
    w, l = r[r > 0].sum(), -r[r < 0].sum()
    return {"n": int(len(r)), "avg_r": float(r.mean()), "pf": float(w / l) if l > 0 else float("inf"),
            "win_pct": float((r > 0).mean() * 100), "sum_r": float(r.sum())}


# ============================================================ ORB (M1, Stop-Order)
def orb_trades(rule: str = "opposite") -> pd.DataFrame:
    # "opposite" seit 2026-10-03 live (Storno der SP500/US30-Long-Order bei Bruch nach unten).
    from ny_open_orb import regime
    from ny_open_orb.data import fetch_m1, fetch_m15
    from ny_open_orb.engine import build_frame, simulate
    from research_orb_cancel_at_sl_and_hold import find_live_entries

    out = []
    for inst in ("SP500", "US30", "NASDAQ"):
        m15 = pb._retry(lambda: fetch_m15(inst, ORB_M15_START, END), attempts=3, delay_seconds=5, timeout_seconds=600)
        m1 = pb._retry(lambda: fetch_m1(inst, ORB_M1_START, END), attempts=3, delay_seconds=5, timeout_seconds=1800)
        frame = build_frame(m15, m1, range_bars=1)
        sessions = pd.DatetimeIndex(frame["session"].dropna().unique())
        if inst == "NASDAQ":
            allowed = {s: ([] if s.day_name() == "Wednesday" else [1, -1]) for s in sessions}
        else:
            bias = regime.ema_trend_bias(m15, sessions)
            allowed = {s: ([1] if (not pd.isna(bias.get(s, np.nan)) and float(bias.get(s)) == 0.0) else [])
                       for s in sessions}
        cfg = pb.ORB_EXIT_CFG_BY_INSTRUMENT[inst]
        # NASDAQ: seit 2026-10-04 Storno am geplanten SL (ORB_CANCEL_AT_PLANNED_SL), OCO beidseitig
        ent = find_live_entries(frame, allowed, cfg["stop_atr_mult"], rule if inst != "NASDAQ" else NASDAQ_RULE)
        px = float(m1["close"].loc[m1.index >= m1.index.max() - pd.Timedelta(days=270)].median())
        spread_bps = INDEX_SPREAD_PTS[inst] / px * 1e4
        tr = simulate(frame, ent, spread_bps=spread_bps, entry_slippage_bps=ORB_ENTRY_SLIP_BPS,
                      slippage_bps=ORB_EXIT_SLIP_BPS, entry_fill_mode="level", **cfg)
        if tr.empty:
            continue
        tr = tr.assign(leg=f"orb_{inst.lower()}", market=inst)
        tr["entry_time"], tr["exit_time"] = _naive(tr["entry_time"]), _naive(tr["exit_time"])
        tr = tr[tr["entry_time"] >= Y0]
        out.append(pd.DataFrame({"leg": tr["leg"], "entry_time": tr["entry_time"], "exit_time": tr["exit_time"],
                                 "r": tr["r_multiple"], "exit_reason": tr["exit_reason"],
                                 "stop_px": tr["initial_risk"].to_numpy(), "spread_bps": spread_bps}))
        print(f"  ORB {inst} ({rule}): {len(tr)} Trades 2026, Spread {spread_bps:.2f} bps, {_stats(tr['r_multiple'])}")
    return pd.concat(out, ignore_index=True)


# ============================================================ Gold ASB
def gold_asb_trades(variant: str) -> pd.DataFrame:
    import research_gold_asb_execution_costs as ec
    m15, m5, dc, dcs, fr = ec.load_all()
    if variant == "live":
        from asian_range_breakout.engine import simulate_asian_breakout
        raw = simulate_asian_breakout(m15, spread_price=0.0, slippage_price=0.0)
        prod = ec.production_filters(raw, dc, dcs, fr)
        prod = prod[_naive(prod["entry_time"]) >= Y0 - pd.Timedelta(days=1)]
        sim = ec.simulate_live(prod, m5, lag_min=LAG_GOLD_ASB_MIN, mode="funded", gate_r=GATE_R,
                               bps=XAU_BPS, exit_lag_min=30)
        status = sim["status"].value_counts().to_dict()
        f = sim[sim["status"] == "filled"].copy()
        et = _naive(f["entry_time"]) + pd.Timedelta(minutes=LAG_GOLD_ASB_MIN)
        # Exit: Stop irgendwann vor 11:30 NY, sonst Zeit-Exit -- Zeitpunkt fuer die
        # Equity-Reihenfolge reicht auf den Tag genau (alle ASB-Exits vor 11:30 NY).
        xt = _naive(f["entry_time"].dt.normalize() + pd.Timedelta(hours=11, minutes=30))
        df = pd.DataFrame({"leg": "gold_asb", "entry_time": et.to_numpy(), "exit_time": xt.to_numpy(),
                           "r": f["R"].to_numpy(), "exit_reason": f["exit_reason"].to_numpy(),
                           "stop_px": (f["sd"] / f["leverage"]).to_numpy()})
    else:
        import research_gold_asb_optimization as opt
        days = opt.day_table(m15, m5, dc, dcs, fr)
        days = days[_naive(days["window_end"]) >= Y0 - pd.Timedelta(days=1)]
        t = opt.apply_filters(opt.simulate(days, m5, cancel="03:00", stop_frac=1.5, bps=XAU_BPS))
        status = {"filled": len(t)}
        et = _naive(t["window_end"] + pd.to_timedelta(t["entry_min"], unit="min"))
        xt = _naive(t["window_end"].dt.normalize() + pd.Timedelta(hours=11, minutes=15))
        df = pd.DataFrame({"leg": "gold_asb", "entry_time": et.to_numpy(), "exit_time": xt.to_numpy(),
                           "r": t["R"].to_numpy(), "exit_reason": t["why"].to_numpy(),
                           # tatsaechliche Distanz Fill->SL: sd = 1,5x Range ab Level, Fill am Level
                           "stop_px": t["sd"].to_numpy()})
    df = df[df["entry_time"] >= Y0].reset_index(drop=True)
    print(f"  Gold ASB ({variant}): {len(df)} Trades 2026, Status {status}, {_stats(df['r'])}")
    return df


# ============================================================ CLS Practical
def cls_trades(lag: int = LAG_CLS_BARS) -> pd.DataFrame:
    from cls_practical.data import (fetch_2y_yield_daily, fetch_eurusd_entry_tf_berlin, fetch_major_m15_berlin,
                                    fetch_rate_instrument_m5_berlin)
    from cls_practical.engine import simulate_cls_practical
    from cls_practical.rates import compute_combined_rate_risk_multiplier
    from strategy.cls_advanced import PAIRS, compute_daily_features

    start = CLS_START
    e = fetch_eurusd_entry_tf_berlin("M5", start, END)
    o = {p: fetch_major_m15_berlin(p, start, END) for p in PAIRS if p != "EURUSD"}
    b = fetch_rate_instrument_m5_berlin("BUND", start, END)
    u = fetch_rate_instrument_m5_berlin("USTBOND", start, END)
    de, us = fetch_2y_yield_daily("DE02Y"), fetch_2y_yield_daily("US02Y")
    daily = compute_daily_features(e)
    mult = compute_combined_rate_risk_multiplier(b, u, de, us, daily["direction"])
    tr = simulate_cls_practical(e, o, b, u, risk_multiplier=mult, min_sl_pips=5,
                                spread_bps=0.0, slippage_bps=0.0)
    tr = tr[_naive(tr["entry_time"]) >= Y0 - pd.Timedelta(days=2)]

    PIP = 0.0001
    half = EURUSD_RT_PIPS * PIP / 2
    idx = e.index
    pos = {t: i for i, t in enumerate(idx)}
    cl, hi, lo = e["close"].to_numpy(), e["high"].to_numpy(), e["low"].to_numpy()
    rows, miss = [], {"sl_touched": 0, "gate": 0}
    for _, t in tr.iterrows():
        i = pos.get(t["entry_time"])
        if i is None or i + lag >= len(cl):
            continue
        d = 1 if t["direction"] == "long" else -1
        sl, sd = float(t["sl"]), float(t["sl_distance"])
        seg = slice(i, i + lag + 1)
        if (lo[seg] <= sl).any() if d == 1 else (hi[seg] >= sl).any():
            miss["sl_touched"] += 1
            continue
        P = cl[i + lag] + d * half
        eff = d * (P - sl)
        if eff <= 0 or (sd - eff) / sd > GATE_R:
            miss["gate"] += 1
            continue
        X = float(t["exit_price"])
        reason = str(t.get("exit_reason", ""))
        if "sl" not in reason.lower() and "stop" not in reason.lower():
            # Ziel/Zeit-Exit: kein Broker-TP, die Bridge schliesst beim naechsten Lauf
            j = pos.get(t["exit_time"])
            if j is not None and j + lag < len(cl):
                X = cl[j + lag]
        X -= d * half
        rows.append({"leg": "cls_practical", "entry_time": _naive(pd.Timestamp(idx[i + lag])),
                     "exit_time": _naive(pd.Timestamp(t["exit_time"])), "r": d * (X - P) / eff,
                     "exit_reason": reason, "stop_px": eff})
    df = pd.DataFrame(rows)
    df = df[df["entry_time"] >= Y0].reset_index(drop=True)
    print(f"  CLS (Lag {lag}): {len(df)} Trades 2026, verworfen {miss}, Exit-Gruende "
          f"{df['exit_reason'].value_counts().to_dict()}, {_stats(df['r'])}")
    return df


# ============================================================ CTNL Reversal
def ctnl_trades() -> pd.DataFrame:
    from gold_smc_htf_ltf import ribbon_gate, spike_gate
    from gold_smc_htf_ltf.concurrent_backtest import simulate_trades_concurrent
    from gold_smc_htf_ltf.live_signal import REV_KWARGS, REV_MAX_CONCURRENT
    from gold_smc_htf_ltf.reversal_cascade import run_pipeline as run_reversal
    from research_ctnl_execution_costs import REV_CFG, _cap_concurrent, load_bars, replay_with_lag
    from strategy.backtest import BacktestConfig

    bars = load_bars(CTNL_START, END)
    sig = run_reversal(bars["h4"], bars["h1"], bars["m15"], **REV_KWARGS)
    cfg = dict(REV_CFG, spread_bps=XAU_BPS)
    tr = simulate_trades_concurrent(sig, BacktestConfig(**cfg))
    tr = spike_gate.annotate(tr, sig)
    tr = _cap_concurrent(tr, REV_MAX_CONCURRENT)            # Paper-Bot-Kappung (ungefilterte Liste)
    tr = tr[_naive(tr["entry_time"]) >= Y0 - pd.Timedelta(days=5)]
    rep = replay_with_lag(tr, bars["m15"], LAG_CTNL_BARS, XAU_BPS / 1e4)
    rep = rep.merge(tr[["entry_time", "direction", spike_gate.SPALTE]], on=["entry_time", "direction"], how="left")
    n0 = len(rep)
    rep = rep[(rep["effective_risk"] > 0) & (~rep["sl_touched"]) & (rep["consumed_r"] <= GATE_R)]
    n_gate = len(rep)
    rep, hinweis = ribbon_gate.filter_trades(rep, source="live", leg="ctnl_reversal")
    n_rib = len(rep)
    rep = rep[rep[spike_gate.SPALTE] >= spike_gate.SPIKE_MIN_ATR]
    n_spk = len(rep)

    # Exit per Re-Scan (TP/max_hold): einen M15-Bar spaeter zum Open
    m15 = bars["m15"]
    idx = _naive(m15.index)
    op = m15["open"].to_numpy()
    r_live = []
    for _, t in rep.iterrows():
        d, P, eff, X = int(t["direction"]), t["entry_live"], t["effective_risk"], t["exit_price"]
        # TP 5R liegt seit 2026-10-03 als Broker-TP (exakt am Ziel); nur max_hold per Re-Scan
        if str(t["exit_reason"]) == "max_hold":
            j = idx.searchsorted(_naive(pd.Timestamp(t["exit_time"])))
            if j + 1 < len(op):
                X = op[j + 1]
        X = X * (1 - d * XAU_BPS / 2e4)
        r_live.append(d * (X - P) / eff)
    rep = rep.assign(r_live=r_live)

    # Live-Deckel (CTNL_LIVE_CAP) gegen die (jetzt gefilterten) offenen Positionen
    rep = rep.assign(entry_time=_naive(rep["entry_time"]), exit_time=_naive(rep["exit_time"]))
    rep = _cap_concurrent(rep.sort_values("entry_time"), CTNL_LIVE_CAP)
    df = pd.DataFrame({"leg": "ctnl_reversal", "entry_time": rep["entry_time"].to_numpy(),
                       "exit_time": rep["exit_time"].to_numpy(), "r": rep["r_live"].to_numpy(),
                       "exit_reason": rep["exit_reason"].to_numpy(), "stop_px": rep["effective_risk"].to_numpy()})
    df = df[df["entry_time"] >= Y0].reset_index(drop=True)
    print(f"  CTNL rev: {n0} nach Kappung -> {n_gate} nach Gates -> {n_rib} nach Ribbon -> {n_spk} nach Spike "
          f"-> {len(df)} 2026 (Live-Deckel 2). Exit-Gruende {df['exit_reason'].value_counts().to_dict()}, {_stats(df['r'])}")
    return df


# ============================================================ Portfolio-Simulation
def run_portfolio(trades: pd.DataFrame) -> dict:
    """Ereignisgetrieben: Sizing mit realisierter Equity beim Entry, P&L beim Exit.
    EOD-Trailing-DD-Kill-Switch sperrt neue Entries (nicht bestehende)."""
    cap = pb.MAX_POSITION_LOSS_PCT * START_EQUITY
    ev = []
    for i, t in trades.iterrows():
        ev.append((t["entry_time"], 1, i))
        ev.append((t["exit_time"], 0, i))
    ev.sort(key=lambda x: (x[0], x[1]))

    equity, risk_of, pnl_of, bumped = START_EQUITY, {}, {}, 0
    eod, ks_active, ks_days, blocked = {}, False, 0, 0
    open_risk, max_open_risk = {}, 0.0
    last_day = None
    for ts, kind, i in ev:
        day = pd.Timestamp(ts).normalize()
        if last_day is not None and day != last_day:
            eod[last_day] = equity
            peak = max(eod.values())
            dd = equity / peak - 1
            if dd <= -pb.TRAILING_DD_PCT:
                ks_active = True
            elif ks_active and dd >= -pb.TRAILING_DD_PCT * 0.5:
                ks_active = False
        last_day = day
        t = trades.loc[i]
        if kind == 1:
            if ks_active:
                blocked += 1
                continue
            target = min(pb.CAPITAL_WEIGHT[t["leg"]] * pb.LEG_RISK_PCT[t["leg"]] * equity, cap)
            risk = target
            if t["leg"] in ("gold_asb", "ctnl_reversal") and pd.notna(t["stop_px"]) and t["stop_px"] > 0:
                per_min = t["stop_px"] * OZ_PER_LOT * MIN_LOT_XAU
                lots = math.floor(target / per_min + 1e-9) * MIN_LOT_XAU
                if lots < MIN_LOT_XAU:
                    if per_min > cap:
                        continue
                    lots, bumped = MIN_LOT_XAU, bumped + 1
                risk = lots / MIN_LOT_XAU * per_min
            risk_of[i] = risk
            open_risk[i] = risk
            max_open_risk = max(max_open_risk, sum(open_risk.values()) / equity)
        else:
            if i not in risk_of:
                continue
            pnl = risk_of[i] * t["r"]
            pnl_of[i] = pnl
            equity += pnl
            open_risk.pop(i, None)
    if last_day is not None:
        eod[last_day] = equity

    eq = pd.Series(eod).sort_index()
    peak = eq.cummax()
    dd = (eq / peak - 1)
    taken = trades.loc[list(pnl_of)].assign(pnl=pd.Series(pnl_of), risk=pd.Series(risk_of))
    daily_pnl = taken.groupby(taken["exit_time"].dt.normalize())["pnl"].sum()
    total = equity - START_EQUITY
    best_day = float(daily_pnl.max()) if len(daily_pnl) else 0.0
    return {
        "taken": taken, "eod": eq,
        "end_equity": equity, "return_pct": total / START_EQUITY * 100,
        "max_dd_eod_pct": float(dd.min() * 100), "max_dd_date": str(dd.idxmin().date()) if len(dd) else None,
        "trailing_floor_breached": bool((dd <= -pb.TRAILING_DD_PCT).any()),
        "entries_blocked_by_kill_switch": blocked, "min_lot_bumps": bumped,
        "max_open_risk_pct": max_open_risk * 100,
        "best_day_usd": best_day, "consistency_ratio": best_day / total if total > 0 else None,
    }


def monthly_table(taken: pd.DataFrame) -> pd.DataFrame:
    m = taken.assign(monat=taken["exit_time"].dt.to_period("M").astype(str))
    tab = m.pivot_table(index="monat", columns="leg", values="pnl", aggfunc="sum", fill_value=0.0)
    tab["Summe"] = tab.sum(axis=1)
    return tab


def block_bootstrap(daily: pd.Series, n=5000, block=10, seed=7) -> dict:
    rng = np.random.default_rng(seed)
    x = daily.to_numpy()
    L = len(x)
    dds, rets = [], []
    for _ in range(n):
        path = []
        while len(path) < L:
            s = rng.integers(0, L - block)
            path.extend(x[s:s + block])
        eq = START_EQUITY + np.cumsum(path[:L])
        pk = np.maximum.accumulate(np.concatenate([[START_EQUITY], eq]))[1:]
        dds.append(((eq - pk) / pk).min())
        rets.append(eq[-1] / START_EQUITY - 1)
    dds, rets = np.array(dds), np.array(rets)
    return {"median_maxdd_pct": float(np.median(dds) * 100), "p5_maxdd_pct": float(np.percentile(dds, 5) * 100),
            "p_dd_over_5pct": float((dds <= -0.05).mean()), "median_return_pct": float(np.median(rets) * 100),
            "p_return_negative": float((rets < 0).mean())}


def main() -> None:
    print("Trade-Listen 2026 mit FK-Ausfuehrung:")
    legs = {"orb": orb_trades(), "gold_asb": gold_asb_trades("live"), "cls_practical": cls_trades(),
            "ctnl_reversal": ctnl_trades()}
    asb_stop = gold_asb_trades("stoporder")
    cls_lag2 = cls_trades(lag=2)
    orb_opp = orb_trades("none")   # Variante D jetzt = alter Zustand (Order bis 16:00)

    result: dict = {"stand": END, "start_equity": START_EQUITY, "varianten": {}}
    base = pd.concat(legs.values(), ignore_index=True).sort_values("entry_time").reset_index(drop=True)
    TRADES_CSV.parent.mkdir(parents=True, exist_ok=True)

    varianten = {
        "A_live_heute": base,
        "B_mit_gold_asb_stoporder": pd.concat([base[base["leg"] != "gold_asb"], asb_stop], ignore_index=True)
        .sort_values("entry_time").reset_index(drop=True),
        "C_cls_lag2_sensitivitaet": pd.concat([base[base["leg"] != "cls_practical"], cls_lag2], ignore_index=True)
        .sort_values("entry_time").reset_index(drop=True),
        "D_orb_order_bis_1600_alt": pd.concat([base[~base["leg"].str.startswith("orb")], orb_opp], ignore_index=True)
        .sort_values("entry_time").reset_index(drop=True),
    }
    for name, tr in varianten.items():
        res = run_portfolio(tr)
        taken = res.pop("taken")
        eod = res.pop("eod")
        if name == "A_live_heute":
            taken.to_csv(TRADES_CSV, index=False)
            mt = monthly_table(taken)
            print("\nMonats-P&L je Bein (USD), Variante A:")
            print(mt.round(0).to_string())
            res["monate"] = mt.round(2).to_dict(orient="index")
        daily = taken.groupby(taken["exit_time"].dt.normalize())["pnl"].sum()
        daily = daily.reindex(pd.bdate_range(Y0, pd.Timestamp(END)), fill_value=0.0)
        res["bootstrap"] = block_bootstrap(daily)
        res["je_bein"] = {}
        for leg, g in taken.groupby("leg"):
            res["je_bein"][leg] = {**_stats(g["r"]), "pnl_usd": float(g["pnl"].sum()),
                                   "avg_risk_usd": float(g["risk"].mean())}
        res["eod_tiefpunkt"] = float(eod.min())
        result["varianten"][name] = res
        print(f"\n=== {name} ===")
        print(f"  Endkapital {res['end_equity']:,.0f} USD | Rendite {res['return_pct']:+.2f} % | "
              f"MaxDD (EOD) {res['max_dd_eod_pct']:.2f} % am {res['max_dd_date']} | "
              f"Trailing-5%-Bruch: {res['trailing_floor_breached']} | max. offenes Risiko {res['max_open_risk_pct']:.2f} %")
        print(f"  Bester Tag {res['best_day_usd']:,.0f} USD, Konsistenz {res['consistency_ratio']}, "
              f"Mindestlot-Anhebungen {res['min_lot_bumps']}, durch Kill-Switch gesperrt {res['entries_blocked_by_kill_switch']}")
        for leg, s in res["je_bein"].items():
            print(f"   {leg:15} n={s['n']:3d}  ØR={s.get('avg_r', 0):+.3f}  PF={s.get('pf', 0):.2f}  "
                  f"Treffer={s.get('win_pct', 0):.0f}%  P&L={s['pnl_usd']:+9,.0f} USD  Ø Risiko {s['avg_risk_usd']:.0f} USD")
        print(f"  Bootstrap (Tagesbloecke): {res['bootstrap']}")

    # CTNL-Kill-Switch: stand-alone-DD des gehandelten Satzes mit FK_RISK_REV
    from gold_smc_htf_ltf.live_signal import FK_RISK_REV
    c = legs["ctnl_reversal"].sort_values("exit_time")
    eq = START_EQUITY * np.cumprod(1 + FK_RISK_REV * c["r"].to_numpy())
    pk = np.maximum.accumulate(np.concatenate([[START_EQUITY], eq]))[1:]
    result["ctnl_kill_switch_min_dd_pct"] = float(((eq - pk) / pk).min() * 100) if len(eq) else 0.0
    print(f"\nCTNL-Kill-Switch (Schwelle -6,6 %): tiefster stand-alone-DD 2026 "
          f"{result['ctnl_kill_switch_min_dd_pct']:.2f} %")

    OUT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"\nGeschrieben: {OUT}\nTrades: {TRADES_CSV}")


if __name__ == "__main__":
    main()
