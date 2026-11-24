"""Dennis' Volumen-Bausteine als FILTER auf die Live-Beine mit eigenem Edge -- Test 25.11.2026 (Nutzerauftrag).

    python -m scripts.research_volumen_kontext_beine            # Trades laden (Cache), Kontext, IS/OOS-Vergleich

Folgetest zu scripts/research_volumen_kontext_h4.py (H4-Manipulation: Bausteine brutto bis +0,08 R, zu wenig gegen
Kosten). Hier: Beine, die netto schon positiv sind -- Gold ASB, CTNL-Reversal, ORB S&P/NASDAQ, CLS Practical,
Trend-Pullback (Gold/Silber/JPY). Trades aus denselben Generatoren wie der Gesamtportfolio-Backtest 2016
(scripts/research_portfolio_live_2016.py, Kosten TTP), nur zusaetzlich mit Richtung/Markt. NICHTS an den Beinen geaendert.

Kontext zum Einstieg (nur Kerzen mit Start < Einstieg, M15-Tick-Volumen Dukascopy, CME-Tag, VA 70 %), je Trade-Richtung:
  trend_mit     POC und VA-Mitte von T-1 gegenueber T-2 in Trade-Richtung verschoben
  wert_gegen    laufender POC des Tages liegt GEGEN die Trade-Richtung vom POC(T-1) (Dennis' „Inducement“)
  guenstig      Einstieg ausserhalb VA(T-1) auf der guenstigen Seite (Long unter VAL, Short ueber VAH)
  stop_in_va2   Stop reicht in die VA(T-2) (Long: Stop <= VAH(T-2); Short: Stop >= VAL(T-2)) -- H4-Befund
  delta_mit     Delta-Naeherung der letzten 4 h in Trade-Richtung
  vol_stark     Tick-Volumen der letzten 4 h > Ø der 6 Vier-Stunden-Bloecke davor -- H4-Befund (umgekehrt zu Dennis)
  dennis        trend_mit & wert_gegen & stop_in_va2
7 Merkmale x 6 Beine = 42 gezaehlte Varianten. Sperre `volumen_kontext_beine`: IS 2016-2021, OOS bis 2026-04-30,
Tresor bis 2026-10-31 (zu). WICHTIG: Die Beine sind live -- nach Overfitting-Sperre Regel 5 kann ein Befund hier nur
ein Forward-Kandidat sein, keine Aenderung am Live-Bein.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO), str(REPO / "scripts"), str(REPO / "ou_paper_backtest")]

from fusion_lab.patterns.volume_profile import VA_PCT, Histogram, cme_day, day_profiles  # noqa: E402
from research_lock import Lock  # noqa: E402

LOCK = Lock("volumen_kontext_beine")
CACHE = REPO / "data_cache/smh/volumen_kontext_beine_trades.parquet"
OUT = "scripts/research_volumen_kontext_beine"
SRC = {  # Markt: (Datei, Preisraster)
    "GOLD": ("GOLD_M15_2009-06-01_2026-11-01", 0.50),
    "SILVER": ("SILVER_M15_2016-01-01_2026-05-28", 0.01),
    "EURUSD": ("EURUSD_M15_2016-01-01_2026-07-29", 0.0001),
    "USDJPY": ("USDJPY_M15_2016-01-01_2026-11-01", 0.01),
    "SP500": ("SP500_M15_2016-07-28_2026-11-01", 1.0),
    "NASDAQ": ("NASDAQ_M15_2016-07-28_2026-11-18", 2.0),
}
FEATS = ["trend_mit", "wert_gegen", "guenstig", "stop_in_va2", "delta_mit", "vol_stark", "dennis"]


# ------------------------------------------------------------------ Trades je Bein (mit Richtung)
def load_trades() -> pd.DataFrame:
    if CACHE.exists():
        return pd.read_parquet(CACHE)
    import research_ctnl_macro_live as cm
    import research_fk_gesamtportfolio_2026 as fk
    import research_live_legs as L
    import research_portfolio_live_2016 as P

    P._configure("ttp")
    parts = []

    # Gold ASB (stoporder, Live-Friktion) -- wie fk.gold_asb_trades, aber mit dir/P/sd
    import research_gold_asb_execution_costs as ec
    import research_gold_asb_optimization as opt
    from asian_range_breakout.pending import live_state_friction
    m15, m5, dc, dcs, fr = ec.load_all()
    fv = live_state_friction(m15, pd.read_parquet(ec.CACHE / "GOLD_D1_2016-01-01_2026-10-01.parquet"))
    days = opt.day_table(m15, m5, dc, dcs, fr, friction_value=fv)
    t = opt.apply_filters(opt.simulate(days, m5, cancel="03:00", stop_frac=1.5, bps=fk.XAU_BPS))
    et = fk._naive(t["window_end"] + pd.to_timedelta(t["entry_min"], unit="min"))
    parts.append(pd.DataFrame({"leg": "gold_asb", "markt": "GOLD", "entry_time": et.to_numpy(), "d": t["dir"].to_numpy(),
                               "entry_px": t["P"].to_numpy(), "stop_dist": t["sd"].to_numpy(), "r": t["R"].to_numpy()}))
    print("ASB", len(t))

    # CTNL-Reversal (Live-Set: Ribbon, Spike, Makro-Sperre, Kill-Switch), Kosten TTP
    d = cm.load()
    d["ks"] = cm.kill_switch_mask(d, cm.OUT / "ctnl_ks_shadow.pkl")
    d = d[~d.gesperrt & ~d.ks].copy()
    d["r"] = d["r"] + (P.CTNL_REF_BPS - P.GOLD_ALLDAY_BPS["ttp"]) / 1e4 * d["entry_live"] / d["effective_risk"] \
        - cm.swap_r(d, P.SWAP_BPS)
    parts.append(pd.DataFrame({"leg": "ctnl_reversal", "markt": "GOLD", "entry_time": d.et.values, "d": d.direction.values,
                               "entry_px": d.entry_live.values, "stop_dist": d.effective_risk.values, "r": d.r.values}))
    print("CTNL", len(d))

    # ORB S&P / NASDAQ (Einstiegskurs aus Kerzen, Stop-Distanz stop_px)
    o = fk.orb_trades()
    o = o[o["leg"].isin(["orb_sp500", "orb_nasdaq"])]
    parts.append(pd.DataFrame({"leg": o["leg"].values, "markt": np.where(o["leg"] == "orb_sp500", "SP500", "NASDAQ"),
                               "entry_time": fk._naive(o["entry_time"]).values, "d": o["direction"].values,
                               "entry_px": np.nan, "stop_dist": o["stop_px"].values, "r": o["r"].values}))
    print("ORB", len(o))

    # CLS Practical: fk.cls_trades + Richtung aus der Engine (Einstieg = Engine-Einstieg + Lag)
    c = fk.cls_trades()
    from cls_practical.data import fetch_eurusd_entry_tf_berlin, fetch_major_m15_berlin, fetch_rate_instrument_m5_berlin, fetch_2y_yield_daily
    from cls_practical.engine import simulate_cls_practical
    from cls_practical.rates import compute_combined_rate_risk_multiplier
    from strategy.cls_advanced import PAIRS, compute_daily_features
    e = fetch_eurusd_entry_tf_berlin("M5", fk.CLS_START, fk.END)
    oth = {p: fetch_major_m15_berlin(p, fk.CLS_START, fk.END) for p in PAIRS if p != "EURUSD"}
    b, u = fetch_rate_instrument_m5_berlin("BUND", fk.CLS_START, fk.END), fetch_rate_instrument_m5_berlin("USTBOND", fk.CLS_START, fk.END)
    mult = compute_combined_rate_risk_multiplier(b, u, fetch_2y_yield_daily("DE02Y"), fetch_2y_yield_daily("US02Y"),
                                                 compute_daily_features(e)["direction"])
    raw = simulate_cls_practical(e, oth, b, u, risk_multiplier=mult, min_sl_pips=5, spread_bps=0.0, slippage_bps=0.0)
    pos = {tt: i for i, tt in enumerate(e.index)}
    raw["t_lag"] = [fk._naive(pd.Timestamp(e.index[pos[x] + fk.LAG_CLS_BARS])) if x in pos and pos[x] + fk.LAG_CLS_BARS < len(e)
                    else pd.NaT for x in raw["entry_time"]]
    dmap = dict(zip(raw["t_lag"], np.where(raw["direction"] == "long", 1, -1)))
    c["d"] = c["entry_time"].map(dmap)
    c = c[c["d"].notna()]
    parts.append(pd.DataFrame({"leg": "cls_practical", "markt": "EURUSD", "entry_time": c["entry_time"].values,
                               "d": c["d"].astype(int).values, "entry_px": np.nan, "stop_dist": c["stop_px"].values,
                               "r": c["r"].values}))
    print("CLS", len(c))

    # Trend-Pullback (GOLD, SILVER, USDJPY -- Maerkte mit M15-Volumen) wie L.trend_pullback_trades + Richtung
    from combined_strategy.data import fetch_timeframe
    from mt5_trend_pullback.filters import alignment_filter
    from mt5_trend_pullback.pipeline import ATR_STOP_MULT, RR_RATIO, run_pipeline
    from strategy.backtest import BacktestConfig, simulate_trades
    ren = {"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
    gold_d1 = fetch_timeframe("GOLD", "D1", L.DATA_START, L.END)["Close"]
    if gold_d1.index.tz is not None:
        gold_d1.index = gold_d1.index.tz_localize(None)
    for key in ("GOLD", "SILVER", "USDJPY"):
        df = fetch_timeframe(key, L.TP_TF[key], L.DATA_START, L.END).rename(columns=ren)
        tr = simulate_trades(run_pipeline(df, adx_min=25.0), BacktestConfig(spread_bps=0.0, stop_atr_mult=ATR_STOP_MULT,
                                                                             use_vwap_target=False, take_profit_r=RR_RATIO))
        if key == "SILVER" and not tr.empty:
            tr = alignment_filter(tr, gold_d1)
        bps = L.BROKERS["ttp"]["xau_bps"] if key == "GOLD" else L.OTHER_BPS[key]
        half = bps / 2e4
        dd = tr["direction"].astype(int).to_numpy()
        ep = tr["entry_price"].to_numpy(float)
        sl = ep - dd * tr["initial_risk"].to_numpy(float)
        Pp = ep * (1 + dd * half)
        X = tr["exit_price"].to_numpy(float) * (1 - dd * half)
        eff = dd * (Pp - sl)
        ok = eff > 0
        parts.append(pd.DataFrame({"leg": "trend_pullback", "markt": key, "entry_time": fk._naive(tr["entry_time"]).to_numpy()[ok],
                                   "d": dd[ok], "entry_px": Pp[ok], "stop_dist": eff[ok], "r": (dd * (X - Pp) / eff)[ok]}))
        print("TP", key, ok.sum())

    out = pd.concat(parts, ignore_index=True)
    out["entry_time"] = pd.to_datetime(out["entry_time"])
    out = out[out["entry_time"] >= "2016-01-01"].reset_index(drop=True)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(CACHE)
    return out


# ------------------------------------------------------------------ Volumenkontext
def annotate(m: str, tr: pd.DataFrame) -> pd.DataFrame:
    f, step = SRC[m]
    bars = pd.read_parquet(f"data_cache/combined/{f}.parquet")[["Open", "High", "Low", "Close", "Volume"]]
    bars = bars[~bars.index.duplicated(keep="last")].sort_index()
    prof = day_profiles(bars, step)
    prof["vam"] = (prof["val"] + prof["vah"]) / 2
    pdays = prof.index.to_numpy()
    days = cme_day(bars.index)
    t = bars.index
    o, h, l, c, v = (bars[k].to_numpy() for k in ("Open", "High", "Low", "Close", "Volume"))
    delta = np.sign(c - o) * v
    rows = []
    for idx, s in tr.iterrows():
        # nur Kerzen, die VOR dem Einstieg schliessen (Start + 15 min <= Einstieg; ORB/ASB/CLS fuellen mitten in M15)
        cut = int(t.searchsorted(pd.Timestamp(s["entry_time"]).tz_localize("UTC") - pd.Timedelta(minutes=15), side="right"))
        if cut < 16 * 7 or cut >= len(t):
            continue
        d = days[cut - 1]
        pi = int(np.searchsorted(pdays, d))
        if pi < 2 or pi >= len(pdays) or pdays[pi] != d:
            continue
        p1, p2 = prof.iloc[pi - 1], prof.iloc[pi - 2]
        a = int(np.searchsorted(days, d))
        if cut - a >= 1:
            hist = Histogram(l[a:cut].min(), h[a:cut].max(), step)
            for i in range(a, cut):
                hist.add(l[i], h[i], v[i])
            poc = hist.poc_va(VA_PCT)[1]
        else:
            poc = np.nan                                   # Einstieg in der ersten Kerze des Tages
        dr = int(s["d"])
        px = s["entry_px"] if np.isfinite(s["entry_px"]) else c[cut - 1]   # ORB/CLS: letzter Schluss vor Einstieg
        stop = px - dr * s["stop_dist"]
        vol4 = v[cut - 16:cut].sum()
        prev = np.mean([v[cut - 16 * (j + 2):cut - 16 * (j + 1)].sum() for j in range(6)])
        rows.append({"_i": idx,
                     "trend_mit": dr * (p1["poc"] - p2["poc"]) > 0 and dr * (p1["vam"] - p2["vam"]) > 0,
                     "wert_gegen": bool(np.isfinite(poc) and dr * (poc - p1["poc"]) < 0),
                     "guenstig": (px < p1["val"]) if dr == 1 else (px > p1["vah"]),
                     "stop_in_va2": (stop <= p2["vah"]) if dr == 1 else (stop >= p2["val"]),
                     "delta_mit": dr * delta[cut - 16:cut].sum() > 0,
                     "vol_stark": vol4 > prev})
    ann = pd.DataFrame(rows).set_index("_i")
    res = tr.loc[ann.index].join(ann)
    res["dennis"] = res["trend_mit"] & res["wert_gegen"] & res["stop_in_va2"]
    return res


def compare(x: pd.DataFrame) -> pd.DataFrame:
    x = x.copy()
    x["sq"] = x.groupby("leg")["stop_dist"].transform(lambda s: pd.qcut(s.rank(method="first"), 2, labels=False))
    rows = {}
    for leg, g in x.groupby("leg"):
        for f in FEATS:
            a, b = g[g[f]], g[~g[f]]
            cell = g.groupby(["markt", "sq", f])["r"].agg(["mean", "size"]).unstack(f).dropna()
            matched = np.average(cell[("mean", True)] - cell[("mean", False)], weights=cell[("size", True)]) \
                if len(cell) and cell[("size", True)].sum() > 0 else np.nan
            rows[(leg, f)] = {"n": len(g), "n_mit": len(a), "R_mit": a["r"].mean(), "R_ohne": b["r"].mean(),
                              "diff": a["r"].mean() - b["r"].mean(), "diff_gleiche_zelle": matched,
                              "sum_R_mit": a["r"].sum(), "sum_R_alle": g["r"].sum()}
    return pd.DataFrame(rows).T


def main() -> None:
    LOCK.register_split("2016-01-01", "2021-12-31", "2026-04-30", "2026-10-31")
    tr = load_trades()
    parts = [annotate(m, g) for m, g in tr.groupby("markt") if m in SRC]
    res = pd.concat(parts)
    for f in FEATS:
        res[f] = res[f].astype(bool)
    print(res.groupby("leg").size().to_string())
    res = res.set_index(res["entry_time"].dt.tz_localize("UTC")).sort_index()
    n = LOCK._load()["trials"] or LOCK.log_trials(len(FEATS) * res["leg"].nunique(), "7 Volumen-Merkmale als Filter je Live-Bein")
    pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_rows", 200)
    is_, oos = LOCK.is_only(res), LOCK.oos_only(res)
    tabs = {}
    for name, x in (("IS", is_), ("OOS", oos)):
        tabs[name] = compare(x)
        tabs[name].to_csv(f"{OUT}_{name.lower()}.csv")
    both = tabs["IS"][["n", "n_mit", "R_mit", "R_ohne", "diff", "diff_gleiche_zelle"]].join(
        tabs["OOS"][["n", "n_mit", "R_mit", "R_ohne", "diff", "diff_gleiche_zelle"]], lsuffix="_IS", rsuffix="_OOS")
    both["gleiche_richtung"] = np.sign(both["diff_IS"]) == np.sign(both["diff_OOS"])
    print(f"\n===== Versuche {n} =====\n{both.round(3).to_string()}")


if __name__ == "__main__":
    main()
