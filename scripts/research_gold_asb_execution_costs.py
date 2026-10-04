"""Gold ASB -- Realkosten- und Ausfuehrungs-Probe (p6_5-p6_8), 2026-10-01.

Dritter Durchlauf nach cls_practical (09-10) und CTNL (09-21), Methode aus
knowledge/areas/realkosten-und-ausfuehrungs-probe.md.

Kern der Sache: der Backtest (asian_range_breakout.engine) modelliert eine
RUHENDE Stop-Order am Range-Level -- Fill exakt am Level, im Moment der
Beruehrung. Live laeuft das Bein in allen drei Bridges als MARKET-Order beim
naechsten Scan, nachdem die Simulation den Fill "gesehen" hat:

  - Funded/FK: absoluter Signal-SL, Alters-Gate 60 Min., Restlaufzeit-Gate,
    0,50R-Detektor, Zeit-Exit wenn der Re-Scan "geschlossen" meldet.
  - EK: SL am Live-Kurs NEU VERANKERT (nur die Distanz), Signalalter bis 6 h,
    kein R-Gate (bei Neuverankerung gegenstandslos).

Gemessen an den echten Fills (bridge_state_*.json): Signal-Label 05:15 UTC
(M15-Bar 01:15 NY) -> Fill 05:43 UTC, also ~28 Min. nach dem LABEL der
Fill-Bar. Genau wie bei CTNL (Taktung, nicht Zufall).

Die Ausfuehrung wird deshalb auf M5 nachsimuliert: Signalsatz = exakt die
Produktions-Pipeline (M15-Engine + 5 Filter, Kosten 0), dann pro Trade der
echte Beruehrungszeitpunkt auf M5, Live-Entry zum Open der M5-Bar bei
Label+lag, Pfad bis Stop/Zeit-Exit auf M5.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from asian_range_breakout.engine import simulate_asian_breakout
from asian_range_breakout.filters import (
    apply_adx_filter, apply_entry_delay_filter, apply_gold_liquidity_filter_causal,
    apply_silver_alignment_filter, apply_trend_bias_filter,
)

CACHE = Path(__file__).resolve().parents[1] / "data_cache" / "combined"
NY = "America/New_York"

# Gemessene Round-Trip-Kosten XAUUSD in bps (knowledge/_data/broker_spreads_xauusd.json,
# Fenster 07-22 Berlin, siehe ctnl-kostenvalidierung.md Befund 3). Werden durch die
# ASB-Fenster-Messung ergaenzt, sobald die vorliegt.
# ASB-Fenster-Messung 2026-10-01 (07:00-08:15 + 16:45-17:30 Berlin, 30 Tage):
# Spread + Median-Slippage RT + Kommission in Points (0,01 USD), / ~4.200 USD Gold.
#   TTP 48+33,5+6=87,5 | IQ 26+5+5=36 | FK 26+2+5=33 | Tickmill 8+8+0=16
BROKER_BPS = {"Tickmill(EK)": 0.38, "FK": 0.79, "IQ": 0.86, "TTP": 2.08, "TTPx2": 4.16}


def load_ohlc(name: str) -> pd.DataFrame:
    df = pd.read_parquet(CACHE / name)
    df = df.rename(columns=str.lower)[["open", "high", "low", "close"]]
    df.index = df.index.tz_convert(NY)
    return df


def load_all():
    from bond_yield_indicator.friction import corwin_schultz_spread
    m15 = load_ohlc("GOLD_M15_2016-01-01_2026-10-01.parquet")
    m5 = load_ohlc("GOLD_M5_2016-01-01_2026-10-01.parquet")
    silver = pd.read_parquet(CACHE / "SILVER_M15_2016-01-01_2026-10-01.parquet")
    d1 = pd.read_parquet(CACHE / "GOLD_D1_2016-01-01_2026-10-01.parquet")
    friction = corwin_schultz_spread(d1["High"], d1["Low"])
    friction.index = friction.index.tz_localize(None)
    daily_close = m15["close"].tz_localize(None).resample("D").last().dropna()
    daily_close_silver = silver["Close"].tz_localize(None).resample("D").last().dropna()
    return m15, m5, daily_close, daily_close_silver, friction


def production_filters(trades, daily_close, daily_close_silver, friction, *, skip=()):
    """Exakt die Kette aus challenge_portfolio/paper_bot.py::_scan_gold_asb. `skip`
    fuer die Leave-one-out-Ablation."""
    if "adx" not in skip:
        trades = apply_adx_filter(trades, adx_min=15.0)
    if "trend" not in skip:
        trades = apply_trend_bias_filter(trades, daily_close, sma_window=200)
    if "delay" not in skip:
        trades = apply_entry_delay_filter(trades, max_delay_bars=3)
    if "silver" not in skip:
        trades = apply_silver_alignment_filter(trades, daily_close_silver, window=5)
    if "liquidity" not in skip:
        trades = apply_gold_liquidity_filter_causal(trades, friction, quantile=2 / 3, min_periods=250)
    return trades


def stats(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) == 0:
        return {"n": 0}
    wins, losses = r[r > 0].sum(), -r[r < 0].sum()
    eq = r.cumsum()
    return {
        "n": len(r), "avgR": r.mean(), "PF": wins / losses if losses > 0 else np.inf,
        "win%": (r > 0).mean() * 100, "sumR": r.sum(), "maxDD_R": (eq - eq.cummax()).min(),
    }


def fmt(d: dict) -> str:
    if d.get("n", 0) == 0:
        return "n=0"
    return (f"n={d['n']:4d}  avgR={d['avgR']:+.3f}  PF={d['PF']:.2f}  win={d['win%']:.1f}%  "
            f"sumR={d['sumR']:+.1f}  maxDD={d['maxDD_R']:.1f}R")



def simulate_live(prod: pd.DataFrame, m5: pd.DataFrame, *, lag_min: int | None, mode: str = "funded",
                  bps: float = 0.0, exit_lag_min: int = 15, gate_r: float | None = 0.50,
                  exit_hhmm: str = "11:00") -> pd.DataFrame:
    """Pro Produktions-Trade die Live-Ausfuehrung auf M5 nachspielen.

    lag_min=None  -> Backtest-Semantik: Fill exakt am Level im Moment der Beruehrung
                     (= ruhende Stop-Order), Zeit-Exit zum Close der 11:00-M15-Bar.
    lag_min=k     -> Market-Entry zum Open der M5-Bar mit Label (Fill-Bar-Label + k Min.).
                     Live gemessen: k ~ 28 -> 30.
    mode "funded" -> absoluter Signal-SL, Nenner |P - SL|, R-Gate gate_r.
    mode "ek"     -> SL am Live-Kurs neu verankert (P - d*sd), Nenner sd, kein Gate.
    exit_lag_min  -> Zeit-Exit zum Open der M5-Bar bei 11:00 + exit_lag_min (Live);
                     bei lag_min=None Close der 11:10-M5-Bar (= Close der 11:00-M15-Bar).
    R wird gegen das GEPLANTE Risiko gerechnet (Risikobetrag konstant), Kosten = bps x P.
    """
    o, h, l, c = (m5[x].to_numpy() for x in ("open", "high", "low", "close"))
    idx = m5.index
    ex_h, ex_m = map(int, exit_hhmm.split(":"))
    rows = []
    for t in prod.itertuples():
        d = 1 if t.direction == "long" else -1
        L = t.range_high if d == 1 else t.range_low
        sd = t.stop_distance
        sl = L - d * sd
        T = t.entry_time
        i0 = idx.searchsorted(T)
        i1 = idx.searchsorted(T + pd.Timedelta(minutes=15))
        # echte Beruehrung innerhalb der M15-Fill-Bar
        touch = None
        for i in range(i0, i1):
            if (h[i] >= L) if d == 1 else (l[i] <= L):
                touch = i
                break
        if touch is None:
            rows.append({"status": "no_touch_m5"})
            continue
        day = T.normalize()
        t_exit = day + pd.Timedelta(hours=ex_h, minutes=ex_m)
        rec = {"entry_time": T, "direction": t.direction, "sd": sd, "L": L}
        if lag_min is None:
            P, j0, sl_live, denom = max(L, o[touch]) if d == 1 else min(L, o[touch]), touch, sl, sd
            exit_i = idx.searchsorted(t_exit + pd.Timedelta(minutes=10))  # Close der 11:10-Bar
            exit_px_fn = lambda k: c[k]
        else:
            j0 = idx.searchsorted(T + pd.Timedelta(minutes=lag_min))
            if j0 >= len(idx):
                rows.append({"status": "data_end"}); continue
            # Restlaufzeit-Gate: SL zwischen Beruehrung und Live-Entry schon getroffen?
            pre = slice(touch, j0)
            if ((l[pre] <= sl).any() if d == 1 else (h[pre] >= sl).any()):
                rec["status"] = "missed_stopped"; rows.append(rec); continue
            if idx[j0] >= t_exit:
                rec["status"] = "missed_expired"; rows.append(rec); continue
            P = o[j0]
            consumed = d * (L - P) / sd
            rec["consumed_r"] = consumed
            if mode == "funded":
                sl_live = sl
                denom = d * (P - sl)
                if denom <= 0:
                    rec["status"] = "missed_stopped"; rows.append(rec); continue
                if gate_r is not None and consumed > gate_r:
                    rec["status"] = "missed_gate"; rows.append(rec); continue
            else:
                sl_live, denom = P - d * sd, sd
            exit_i = idx.searchsorted(t_exit + pd.Timedelta(minutes=exit_lag_min))
            exit_px_fn = lambda k: o[k]
        X, reason = None, None
        for k in range(j0, min(exit_i, len(idx))):
            if (l[k] <= sl_live) if d == 1 else (h[k] >= sl_live):
                X, reason = sl_live, "stop"; break
        if X is None:
            k = min(exit_i, len(idx) - 1)
            X, reason = exit_px_fn(k), "time_exit"
        cost = bps / 1e4 * P
        pnl = d * (X - P) - cost
        rec.update(status="filled", P=P, X=X, exit_reason=reason, leverage=sd / denom,
                   R=pnl / denom,
                   cost_over_sd=cost / sd)
        rows.append(rec)
    return pd.DataFrame(rows)

if __name__ == "__main__":
    m15, m5, dc, dcs, fr = load_all()
    print("M15", m15.index.min(), m15.index.max(), "M5", m5.index.min(), m5.index.max())
    raw = simulate_asian_breakout(m15, spread_price=0.0, slippage_price=0.0)
    prod = production_filters(raw, dc, dcs, fr)
    prod = prod.assign(R=lambda t: np.where(t.direction == "long", 1, -1) * (t.exit_price - t.entry_price) / t.stop_distance)
    print("raw", len(raw), "prod", len(prod))
    print("prod zero-cost:", fmt(stats(prod["R"])))
    print(prod.exit_reason.value_counts())
    print(prod.groupby(prod.entry_time.dt.year)["R"].agg(["count", "mean", "sum"]))

    # Plausibilitaet: M5-Nachbau mit Backtest-Semantik muss die M15-Engine reproduzieren
    bt = simulate_live(prod, m5, lag_min=None)
    f = bt[bt.status == "filled"]
    print("\nM5-Nachbau Backtest-Semantik:", fmt(stats(f["R"])), "| status:", bt.status.value_counts().to_dict())
    print("M15-Engine                   :", fmt(stats(prod["R"])))

    print("\n=== Probe 1: Kosten (Backtest-Semantik, ruhende Stop-Order) ===")
    for name, b in [("0", 0.0)] + list(BROKER_BPS.items()):
        f = simulate_live(prod, m5, lag_min=None, bps=b)
        f = f[f.status == "filled"]
        print(f"  {name:13s} {b:4.2f}bps  cost/sd median {f.cost_over_sd.median():.3f}  {fmt(stats(f['R']))}")

    print("\n=== Probe 2/3: Lag x Modus (TTP-Kosten) ===")
    for mode, gate in [("funded", 0.50), ("funded", None), ("ek", None)]:
        for lag in [None, 15, 20, 25, 30, 45, 60]:
            sim = simulate_live(prod, m5, lag_min=lag, mode=mode, gate_r=gate, bps=BROKER_BPS["TTP"],
                                exit_lag_min=30 if mode == "funded" else 15)
            f = sim[sim.status == "filled"]
            miss = sim.status.value_counts().to_dict()
            lev = f.leverage
            print(f"  {mode:6s} gate={str(gate):4s} lag={str(lag):4s} {fmt(stats(f['R']))}  "
                  f"lev med/p95/max {lev.median():.2f}/{lev.quantile(.95):.2f}/{lev.max():.2f}  "
                  f"miss={ {k: v for k, v in miss.items() if k != 'filled'} }")
    sim = simulate_live(prod, m5, lag_min=30, mode="funded", gate_r=None, bps=BROKER_BPS["TTP"], exit_lag_min=30)
    f = sim[sim.status == "filled"]
    print("\n  consumed_r bei lag 30 (ohne Gate):", f.consumed_r.describe(percentiles=[.1,.25,.5,.75,.9]).round(3).to_dict())
    for lo, hi in [(-9, 0), (0, .25), (.25, .5), (.5, .75), (.75, 1)]:
        sub = f[(f.consumed_r > lo) & (f.consumed_r <= hi)]
        print(f"   consumed ({lo},{hi}] {fmt(stats(sub['R']))}")

    print("\n=== Probe 4: Stopdistanz gegen Kosten (TTP) ===")
    f = simulate_live(prod, m5, lag_min=None, bps=BROKER_BPS["TTP"])
    f = f[f.status == "filled"]
    rt = BROKER_BPS["TTP"] / 1e4 * f.P
    ratio = f.sd / rt
    print("  sd / Round-Trip-Kosten:", ratio.describe(percentiles=[.05,.1,.25,.5]).round(1).to_dict())
    for lo, hi in [(0, 3), (3, 10), (10, 20), (20, 1e9)]:
        sub = f[(ratio > lo) & (ratio <= hi)]
        print(f"   ratio ({lo},{hi}] {fmt(stats(sub['R']))}")
