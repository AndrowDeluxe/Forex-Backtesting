"""Paritaetstest: asian_range_breakout/pending.py::todays_setup (Live-Entscheidung
der ruhenden Stop-Order) gegen die Backtest-Engine mit denselben Parametern.

Fuer jeden Handelstag 2017-2026:
  - Live-Seite: todays_setup() um 01:00:30 NY auf Bars bis Range-Schluss, dann
    der Fill der ruhenden Order auf M15 bis CANCEL_TIME (zuerst eigenes Level
    -> Trade; zuerst Gegenseite -> kein Trade).
  - Engine-Seite: simulate_asian_breakout(stop_frac=STOP_FRAC) + Produktions-
    Filter (MAX_DELAY_BARS), ADX wie live an der 00:45-Bar (window_end - 1).
Verglichen werden Tag, Richtung, Level und Stop. Erwartete Abweichungen:
  (a) Ausbruch in der 01:00-Bar: die Engine sucht Fills erst ab 01:15.
  (b) Bars, die beide Seiten beruehren (Engine wartet, die Order fuellt).
Alles andere ist ein Fehler.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd

from asian_range_breakout import pending as P
from asian_range_breakout.engine import simulate_asian_breakout
from asian_range_breakout.filters import (
    apply_adx_filter, apply_entry_delay_filter, apply_gold_liquidity_filter_causal,
    apply_silver_alignment_filter, apply_trend_bias_filter,
)
from research_gold_asb_execution_costs import load_all
from strategy.indicators import compute_adx


def engine_trades(m15, dc, dcs, fr):
    t = simulate_asian_breakout(m15, stop_frac=P.STOP_FRAC, spread_price=0.0, slippage_price=0.0)
    adx = compute_adx(m15)["adx"]
    prev = adx.shift(1).reindex(t["window_end"]).to_numpy()   # 00:45-Bar wie live
    t["adx_at_entry"] = prev
    t = apply_adx_filter(t, adx_min=P.ADX_MIN)
    t = apply_trend_bias_filter(t, dc, sma_window=P.TREND_SMA_WINDOW)
    t = apply_entry_delay_filter(t, max_delay_bars=P.MAX_DELAY_BARS)
    t = apply_silver_alignment_filter(t, dcs, window=P.SILVER_ALIGNMENT_WINDOW)
    t = apply_gold_liquidity_filter_causal(t, fr, quantile=P.LIQUIDITY_QUANTILE, min_periods=P.LIQUIDITY_MIN_PERIODS)
    return t


def live_side(m15, inputs, day):
    t = P.session_times(day)
    now = t["range_end"] + pd.Timedelta(seconds=30)
    # wie live: ~30 Tage Broker-Historie fuer den ADX-Vorlauf
    ix = m15.index
    hist = m15.iloc[ix.searchsorted(t["range_end"] - pd.Timedelta(days=30)):ix.searchsorted(t["range_end"])]
    f = P.prior_day_filters(inputs, day)
    s = P.todays_setup(hist, now, f)
    if s["status"] != "setup":
        return s, None
    after = m15.iloc[ix.searchsorted(t["range_end"]):ix.searchsorted(t["cancel_at"])]
    d, lv, op = s["direction"], s["level"], s["opposite_level"]
    for ts, b in after.iterrows():
        own = b.high >= lv if d == 1 else b.low <= lv
        opp = b.low <= op if d == 1 else b.high >= op
        if opp and not own:
            return s, None
        if own:
            return s, {"fill_bar": ts, "both": bool(opp)}
    return s, None


if __name__ == "__main__":
    m15, m5, dc, dcs, fr = load_all()
    inputs = {"gold_m15": m15, "daily_close": dc, "daily_close_silver": dcs, "friction": fr}
    eng = engine_trades(m15, dc, dcs, fr)
    eng = eng[eng.entry_time >= pd.Timestamp("2017-01-01", tz=P.NY)]
    eng_by_day = {e.window_end.normalize().date(): e for e in eng.itertuples()}

    days = sorted({ts.normalize() for ts in m15.index[(m15.index.hour == 1) & (m15.index.minute == 0)]
                   if ts >= pd.Timestamp("2017-01-01", tz=P.NY)})
    rows = []
    for day in days:
        s, fill = live_side(m15, inputs, day)
        e = eng_by_day.get(day.date())
        rows.append({
            "day": day.date(), "status": s["status"], "live_trade": fill is not None,
            "live_dir": s.get("direction") if fill else None, "live_level": s.get("level") if fill else None,
            "live_stop": s.get("stop") if fill else None,
            "fill_0100": bool(fill and fill["fill_bar"].hour == 1 and fill["fill_bar"].minute == 0),
            "both": bool(fill and fill["both"]),
            "eng_trade": e is not None, "eng_dir": (1 if e.direction == "long" else -1) if e is not None else None,
            "eng_level": (e.range_high if e.direction == "long" else e.range_low) if e is not None else None,
            "eng_stop": e.sl if e is not None else None,
        })
    r = pd.DataFrame(rows)
    both = r[r.live_trade & r.eng_trade]
    print(f"Tage {len(r)} | live Trades {r.live_trade.sum()} | Engine Trades {r.eng_trade.sum()} | beide {len(both)}")
    print("Status-Verteilung:", r.status.value_counts().to_dict())
    print("Richtung gleich:", (both.live_dir == both.eng_dir).mean(),
          "| Level max |diff|:", np.abs(both.live_level - both.eng_level).max(),
          "| Stop max |diff|:", np.abs(both.live_stop - both.eng_stop).max())
    only_live = r[r.live_trade & ~r.eng_trade]
    only_eng = r[~r.live_trade & r.eng_trade]
    print(f"nur live: {len(only_live)} (davon Fill in 01:00-Bar {only_live.fill_0100.sum()}, beidseitige Bar {only_live.both.sum()})")
    print(f"nur Engine: {len(only_eng)} | Status dort:", only_eng.status.value_counts().to_dict())
    unexplained_live = only_live[~only_live.fill_0100 & ~only_live.both]
    print("UNERKLAERT nur live:", len(unexplained_live))
    if len(unexplained_live):
        print(unexplained_live.head(10).to_string())
    if len(only_eng):
        print(only_eng.head(10).to_string())
