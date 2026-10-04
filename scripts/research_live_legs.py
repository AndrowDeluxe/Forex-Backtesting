"""Trade-Listen 2019-2026 mit echter Ausfuehrung je BROKER (TTP / IQ / Tickmill).

Teil der Neugewichtung Challenge + EK (Plan 2026-10-04,
scripts/research_challenge_ek_gewichtung_mc_wf.py). Verallgemeinert die
FK-Beinfunktionen aus research_fk_gesamtportfolio_2026.py auf andere
Kostensaetze und ergaenzt die vier Beine, die FK nicht faehrt:

  trend_pullback  Engine (mt5_trend_pullback) mit Spread 0, dann Einstieg zum
                  Open der Folgebar (= Engine-Konvention) + halbe Broker-Kosten je
                  Seite, absoluter SL. TP liegt nicht beim Broker -- Exit-Versatz
                  bei H1/H4 und 5-15-Min.-Scan vernachlaessigt.
  gold_silver     gleiches Muster (nur EK), Order auf XAUUSD.
  btc_ema_cross   btc_ema_cross/engine.simulate_risk_sized (nur EK, Binance-Daily
                  als Signalquelle wie live). ANNAHME: Kosten nie gemessen ->
                  Engine-Kommission 0,1 %/Seite + BTC_EXTRA_BPS + Swap BTC_SWAP_PA.
  ou_modell       Logik D (Stop 8 sigma, kein TP, MA20-Exit, k=2,25, max_hold 10)
                  ueber ou_paper_backtest.portfolio.simulate_bracket_portfolio,
                  dann research_ou_exit_logic.replay_exit(logic="mean_revert") mit
                  den gemessenen Kosten "FK (TTP)" bzw. "EK (Tickmill)". Nur TTP+EK.

Jede Zeile traegt `stop_px` (Preisabstand Fill->SL) und `unit_usd` (USD-Verlust
je Preiseinheit fuer das MINDESTLOT des Brokers) -- daraus rechnet der Optimierer
die Mindestlot-Anhebung (auf EK der dominante Effekt).

Aufruf: python research_live_legs.py ttp|iq|tickmill [--refresh]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))
import research_fk_gesamtportfolio_2026 as fk  # noqa: E402

H0 = "2019-01-01"
DATA_START = "2018-01-01"
END = fk.END
OUT_DIR = REPO / "portfolio_construction" / "results"

# --- Kosten je Broker (gemessen; Quellen im Plan / knowledge/_data) ----------
BROKERS = {
    "ttp": {"xau_bps": 2.08, "eurusd_rt_pips": 2.05,
            "idx_pts": {"SP500": 0.64, "US30": 2.50, "NASDAQ": 1.60}, "ou_cost": "FK (TTP)",
            "ctnl_cap": 2, "legs": ["orb", "gold_asb", "cls_practical", "ctnl_reversal", "trend_pullback", "ou_modell"],
            "tp_markets": ["GOLD", "SILVER", "PLATINUM", "CHFJPY", "USDJPY"]},
    "iq": {"xau_bps": 0.86, "eurusd_rt_pips": 1.30,
           "idx_pts": {"SP500": 0.40, "US30": 3.20, "NASDAQ": 1.00}, "ou_cost": None,
           "ctnl_cap": 2, "legs": ["orb", "gold_asb", "cls_practical", "ctnl_reversal", "trend_pullback"],
           "tp_markets": ["GOLD", "SILVER", "PLATINUM", "CHFJPY", "USDJPY"]},
    # Tickmill: EURUSD-Kommission nie gemessen -> ANNAHME 0,8 Pips RT (0,1 Spread + Rest)
    "tickmill": {"xau_bps": 0.38, "eurusd_rt_pips": 0.80,
                 "idx_pts": {"SP500": 0.30, "US30": 1.20, "NASDAQ": 0.80}, "ou_cost": "EK (Tickmill)",
                 "ctnl_cap": 1,
                 "legs": ["orb", "gold_asb", "cls_practical", "ctnl_reversal", "trend_pullback",
                          "ou_modell", "gold_silver", "btc_ema_cross"],
                 "tp_markets": ["GOLD", "SILVER", "CHFJPY", "USDJPY"]},
}
# Nicht gemessene Maerkte: Engine-Defaults aus dem Paper-Bot (ANNAHME)
OTHER_BPS = {"SILVER": 10.0, "PLATINUM": 10.0, "CHFJPY": 3.0, "USDJPY": 1.5}
TP_TF = {"GOLD": "H1", "SILVER": "H1", "PLATINUM": "H1", "CHFJPY": "H4", "USDJPY": "H4"}
BTC_EXTRA_BPS = 10.0     # ANNAHME, zusaetzlich zur Engine-Kommission 0,1 %/Seite
BTC_SWAP_PA = 0.15       # ANNAHME, Finanzierung BTC-CFD p.a. auf Nominal

# USD-Verlust je Preiseinheit beim Mindestlot (0,01 Lot bzw. 1 Aktie). ANNAHMEN zur
# Kontraktgroesse: XAU 100 oz, XAG 5000 oz, XPT 100 oz, FX 100k, Indizes 1/Pkt, BTC 1.
UNIT_USD = {"XAU": 1.0, "SILVER": 50.0, "PLATINUM": 1.0, "EURUSD": 1000.0, "INDEX": 0.01,
            "BTC": 0.01, "STOCK": 1.0}


def _set_broker(b: str) -> None:
    cfg = BROKERS[b]
    fk.Y0 = pd.Timestamp(H0)
    fk.END = END
    fk.ORB_M15_START = fk.ORB_M1_START = H0
    fk.CLS_START = fk.CTNL_START = DATA_START
    fk.XAU_BPS = cfg["xau_bps"]
    fk.EURUSD_RT_PIPS = cfg["eurusd_rt_pips"]
    fk.INDEX_SPREAD_PTS = dict(cfg["idx_pts"])
    fk.CTNL_LIVE_CAP = cfg["ctnl_cap"]


def _engine_replay(trades: pd.DataFrame, leg: str, bps: float, unit: float) -> pd.DataFrame:
    """Einstieg = Engine-Fill (Open der Folgebar, Spread 0) +/- halbe Kosten, SL
    absolut am Signal-Niveau, Exit = Engine-Exit -/+ halbe Kosten."""
    if trades.empty:
        return pd.DataFrame()
    half = bps / 2e4
    d = trades["direction"].astype(int).to_numpy()
    e = trades["entry_price"].to_numpy(float)
    sl = e - d * trades["initial_risk"].to_numpy(float)
    P = e * (1 + d * half)
    X = trades["exit_price"].to_numpy(float) * (1 - d * half)
    eff = d * (P - sl)
    ok = eff > 0
    return pd.DataFrame({"leg": leg, "entry_time": fk._naive(trades["entry_time"]).to_numpy()[ok],
                         "exit_time": fk._naive(trades["exit_time"]).to_numpy()[ok],
                         "r": (d * (X - P) / eff)[ok], "exit_reason": trades["exit_reason"].to_numpy()[ok],
                         "stop_px": eff[ok], "unit_usd": unit})


def trend_pullback_trades(b: str) -> pd.DataFrame:
    from combined_strategy.data import fetch_timeframe
    from mt5_trend_pullback.filters import alignment_filter
    from mt5_trend_pullback.pipeline import ATR_STOP_MULT, RR_RATIO, run_pipeline
    from strategy.backtest import BacktestConfig, simulate_trades

    ren = {"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
    gold_d1 = fetch_timeframe("GOLD", "D1", DATA_START, END)["Close"]
    if gold_d1.index.tz is not None:
        gold_d1.index = gold_d1.index.tz_localize(None)
    out = []
    for key in BROKERS[b]["tp_markets"]:
        df = fetch_timeframe(key, TP_TF[key], DATA_START, END).rename(columns=ren)
        if df.empty:
            print(f"    trend_pullback {key}: keine Daten")
            continue
        sig = run_pipeline(df, adx_min=25.0)
        tr = simulate_trades(sig, BacktestConfig(spread_bps=0.0, stop_atr_mult=ATR_STOP_MULT,
                                                  use_vwap_target=False, take_profit_r=RR_RATIO))
        if key == "SILVER" and not tr.empty:
            tr = alignment_filter(tr, gold_d1)
        bps = BROKERS[b]["xau_bps"] if key == "GOLD" else OTHER_BPS[key]
        unit = {"GOLD": UNIT_USD["XAU"], "SILVER": UNIT_USD["SILVER"], "PLATINUM": UNIT_USD["PLATINUM"]}.get(key)
        if unit is None:   # JPY-Paare: 1000 Einheiten x 1 JPY -> USD
            unit = 1000.0 / float(df["close"].median())
        rep = _engine_replay(tr, "trend_pullback", bps, unit)
        print(f"    trend_pullback {key}: {len(rep)} Trades, Ø R {rep['r'].mean() if len(rep) else 0:+.3f}")
        out.append(rep)
    t = pd.concat(out, ignore_index=True)
    return t[t["entry_time"] >= pd.Timestamp(H0)]


def gold_silver_trades(b: str) -> pd.DataFrame:
    from combined_strategy.data import fetch_timeframe
    from mt5_gold_silver_divergenz.pipeline import ATR_STOP_MULT, RR_RATIO, run_pipeline
    from strategy.backtest import BacktestConfig, simulate_trades

    ren = {"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
    xau = fetch_timeframe("GOLD", "H4", DATA_START, END).rename(columns=ren)
    xag = fetch_timeframe("SILVER", "H4", DATA_START, END).rename(columns=ren)
    sig = run_pipeline(xau, xag, ret_len=25, band_lookback=50, band_mult=1.75, confirm_len=10)
    tr = simulate_trades(sig, BacktestConfig(spread_bps=0.0, stop_atr_mult=ATR_STOP_MULT,
                                              use_vwap_target=False, take_profit_r=RR_RATIO))
    t = _engine_replay(tr, "gold_silver", BROKERS[b]["xau_bps"], UNIT_USD["XAU"])
    return t[t["entry_time"] >= pd.Timestamp(H0)]


def btc_trades() -> pd.DataFrame:
    from auction_playbook.data import fetch_klines
    from btc_ema_cross.engine import ATR_PERIOD, ATR_STOP_MULT, compute_atr, simulate_risk_sized

    df = fetch_klines("BTCUSDT", "1d", "2017-09-01", END)
    res = simulate_risk_sized(df, fast=9, slow=21, capital=100_000.0, risk_pct=0.01,
                              sim_from=pd.Timestamp(DATA_START, tz="UTC"), extra_cost_bps=BTC_EXTRA_BPS)
    t = pd.DataFrame(res["trades"])
    atr = compute_atr(df, ATR_PERIOD)
    rows = []
    for _, x in t.iterrows():
        i = df.index.get_loc(x["entry_date"])
        stop = float(atr.iloc[i - 1]) * ATR_STOP_MULT
        px = float(df["open"].iloc[i])
        days = max((x["exit_date"] - x["entry_date"]).days, 1)
        swap_r = BTC_SWAP_PA / 365 * days * px / stop      # Finanzierung in R
        rows.append({"leg": "btc_ema_cross", "entry_time": fk._naive(pd.Timestamp(x["entry_date"])),
                     "exit_time": fk._naive(pd.Timestamp(x["exit_date"])), "r": float(x["r"]) - swap_r,
                     "exit_reason": "stop" if x["stopped_out"] else "cross", "stop_px": stop,
                     "unit_usd": UNIT_USD["BTC"]})
    out = pd.DataFrame(rows)
    return out[out["entry_time"] >= pd.Timestamp(H0)]


def ou_trades(b: str) -> pd.DataFrame:
    import challenge_portfolio.paper_bot as cpb
    import research_ou_execution_costs as rx
    import research_ou_exit_logic as ex

    ou_config, ou_portfolio, uni = rx.load_universe()
    ohlc = rx.download([t for v in uni.values() for t in v])
    rows = []
    for mk, tick in uni.items():
        tick = [t for t in tick if t in ohlc]
        panel = pd.DataFrame({t: ohlc[t]["Close"] for t in tick}).sort_index()
        bench = rx.yf.download(ou_config.UNIVERSES[mk]["benchmark"], start=rx.DL_START, end=END,
                               auto_adjust=True, progress=False)["Close"]
        if isinstance(bench, pd.DataFrame):
            bench = bench.iloc[:, 0]
        regime = (bench > bench.ewm(span=200).mean()).reindex(panel.index).ffill().fillna(False)
        _, tl = ou_portfolio.simulate_bracket_portfolio(
            panel, list(panel.columns), "2018-06-01", str(panel.index.max().date()),
            stop_sigma=cpb.OU_MODELL_STOP_SIGMA, rr_ratio=None, be_trigger_r=cpb.OU_MODELL_BE_TRIGGER_R,
            allowed_directions=(1,), regime_filter=regime, risk_pct=cpb.OU_MODELL_RISK_PCT,
            max_total_risk_pct=cpb.OU_MODELL_MAX_TOTAL_RISK_PCT, ma_exit=True, k=cpb.OU_MODELL_BB_K)
        std20 = panel.rolling(ou_config.BB_LOOKBACK).std()
        ma20 = panel.rolling(ou_config.BB_LOOKBACK).mean()
        fam = "funded" if b == "ttp" else "ek"
        for t in tl:
            sd = std20.loc[t["entry_date"], t["ticker"]] * cpb.OU_MODELL_STOP_SIGMA
            if not np.isfinite(sd) or sd <= 0:
                continue
            tr = {"ticker": t["ticker"], "d0": t["entry_date"], "c0": t["entry_price"], "stop_dist": sd, "rr": None}
            bars = ohlc[t["ticker"]]
            r = ex.replay_exit(tr, bars, ma20[t["ticker"]], std20[t["ticker"]], logic="mean_revert",
                               family=fam, cost=ex.COSTS[BROKERS[b]["ou_cost"]], be_r=0.0, entry_mode="open_d1")
            if not r:
                continue
            after = bars[bars.index > t["entry_date"]]
            rows.append({"leg": "ou_modell", "entry_time": fk._naive(pd.Timestamp(after.index[0])),
                         "exit_time": fk._naive(pd.Timestamp(after.index[r["days"] - 1])) + pd.Timedelta(hours=20),
                         "r": float(r["R"]), "exit_reason": r["reason"], "stop_px": sd, "unit_usd": UNIT_USD["STOCK"]})
    out = pd.DataFrame(rows)
    return out[out["entry_time"] >= pd.Timestamp(H0)]


def build(b: str, refresh: bool = False) -> pd.DataFrame:
    path = OUT_DIR / f"live_trades_{b}_2019_2026.csv"
    if path.exists() and not refresh:
        return pd.read_csv(path, parse_dates=["entry_time", "exit_time"])
    _set_broker(b)
    legs = BROKERS[b]["legs"]
    parts = []
    print(f"Broker {b}:")
    if "orb" in legs:
        o = fk.orb_trades()
        o["unit_usd"] = UNIT_USD["INDEX"]
        parts.append(o.drop(columns=["spread_bps"], errors="ignore"))
    if "gold_asb" in legs:   # Funded + EK: ruhende Stop-Order 1,5x Range / Storno 03:00
        parts.append(fk.gold_asb_trades("stoporder").assign(unit_usd=UNIT_USD["XAU"]))
    if "cls_practical" in legs:
        parts.append(fk.cls_trades().assign(unit_usd=UNIT_USD["EURUSD"]))
    if "ctnl_reversal" in legs:
        parts.append(fk.ctnl_trades().assign(unit_usd=UNIT_USD["XAU"]))
    if "trend_pullback" in legs:
        parts.append(trend_pullback_trades(b))
    if "gold_silver" in legs:
        g = gold_silver_trades(b)
        print(f"  gold_silver: {len(g)} Trades, {fk._stats(g['r'])}")
        parts.append(g)
    if "btc_ema_cross" in legs:
        x = btc_trades()
        print(f"  btc_ema_cross: {len(x)} Trades, {fk._stats(x['r'])}")
        parts.append(x)
    if "ou_modell" in legs:
        u = ou_trades(b)
        print(f"  ou_modell: {len(u)} Trades, {fk._stats(u['r'])}")
        parts.append(u)
    t = pd.concat(parts, ignore_index=True).sort_values("entry_time").reset_index(drop=True)
    t.to_csv(path, index=False)
    print(t.groupby("leg")["r"].agg(["count", "mean", "sum"]).round(3).to_string())
    return t


if __name__ == "__main__":
    build(sys.argv[1], refresh="--refresh" in sys.argv)
