"""Filter aus anderen Strategien im Projekt, als zusaetzliche Tages-
Ausschlusskriterien auf cls_practical getestet (User-Anfrage 2026-08-13).
Alle post-hoc auf die von simulate_cls_practical() bereits erzeugten Trades
angewendet (Ausschluss nach Datum), analog zu asian_range_breakout/
filters.py's attach_trend_bias-Muster -- kein Eingriff in engine.py noetig.

Getestet, alle NUR auf In-Sample (2018-12-01 bis 2022-06-01), OOS bleibt fuer
eine spaetere Verifikation eines etwaigen Fundes reserviert:

1. VIX > 20 (asian_range_breakout/vix.py) -- Vortages-Schluss, kein
   Lookahead (US-Cash-Close liegt lange vor dem Berliner Vormittag).
2. US/EUR-High-Impact-News-Tage (news_calendar/, gestern gebaut).
3. Notenbank-Event-Fenster FOMC/EZB +/-1 Tag (bond_yield_indicator/calendar.py).
4. FX-Liquiditaets-Proxy (bond_yield_indicator/friction.py, Corwin-Schultz) --
   schlechteste 20% Liquiditaets-Tage ausgeschlossen. ACHTUNG Lookahead-
   Falle: der Schaetzer selbst nutzt bereits [t, t+1]-Daten (siehe
   friction.py-Docstring), wird also erst an Tag t+1 vollstaendig bekannt --
   hier zusaetzlich um 2 Tage verschoben (nicht nur 1), damit der an Tag D
   verwendete Wert schon vor Handelsbeginn an Tag D feststand.
5. Asia-Range-Breite (asia_high-asia_low) -- oberste/unterste 20% ausgeschlossen
   (zu eng = evtl. Feiertag/duenner Handel, zu breit = evtl. bereits volatiler
   Ausreissertag)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from asian_range_breakout.vix import fetch_vix_daily
from bond_yield_indicator.calendar import event_window_dummy
from bond_yield_indicator.friction import fetch_fx_friction
from cls_practical.data import fetch_eurusd_entry_tf_berlin, fetch_major_m15_berlin, fetch_rate_instrument_m5_berlin
from cls_practical.engine import simulate_cls_practical
from news_calendar.filter import get_news_dates
from strategy.cls_advanced import PAIRS, compute_daily_features

START, SPLIT = "2018-12-01", "2022-06-01"
OTHER_MAJORS = [p for p in PAIRS if p != "EURUSD"]


def stats(trades: pd.DataFrame, label: str) -> dict:
    n = len(trades)
    if n == 0:
        print(f"  {label}: keine Trades")
        return {"label": label, "n_trades": 0}
    r = trades["pnl_usd"] / trades["risk_amount_usd"]
    wins = r[r > 0]
    row = {"label": label, "n_trades": n, "win_rate": len(wins) / n, "avg_r": r.mean(), "total_r": r.sum()}
    print(f"  {label}: n={n} WR={row['win_rate']*100:.1f}% avg_R={row['avg_r']:+.3f} total_R={row['total_r']:+.2f}")
    return row


def main():
    print("Lade Daten...")
    eurusd_m5 = fetch_eurusd_entry_tf_berlin("M5", START, SPLIT)
    other_majors_m15 = {p: fetch_major_m15_berlin(p, START, SPLIT) for p in OTHER_MAJORS}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, SPLIT)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, SPLIT)

    trades = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5)
    trades["date_ts"] = pd.to_datetime(trades["date"].astype(str))
    rows = [stats(trades, "Baseline (keine externen Filter)")]

    # --- 1) VIX > 20, Vortages-Schluss ---
    vix = fetch_vix_daily((pd.Timestamp(START) - pd.Timedelta(days=10)).date().isoformat(), SPLIT)
    vix_known = vix.copy()
    vix_known.index = vix_known.index + pd.Timedelta(days=1)
    daily_cal = pd.date_range(vix_known.index.min(), pd.Timestamp(SPLIT), freq="D")
    vix_daily = vix_known.reindex(daily_cal).ffill()
    high_vix_days = set(vix_daily[vix_daily > 20].index.normalize())
    t_novix = trades[~trades["date_ts"].isin(high_vix_days)]
    rows.append(stats(t_novix, "ohne VIX>20-Tage"))

    # --- 2) US/EUR High-Impact-News-Tage ---
    news_dates = set(get_news_dates(START, SPLIT).normalize())
    t_nonews = trades[~trades["date_ts"].isin(news_dates)]
    rows.append(stats(t_nonews, "ohne US/EUR-News-Tage"))

    # --- 3) Notenbank-Event-Fenster FOMC/EZB +/-1 Tag ---
    date_index = pd.DatetimeIndex(sorted(trades["date_ts"].unique()))
    fomc_dummy = event_window_dummy("FOMC", date_index, window_days=1)
    ecb_dummy = event_window_dummy("ECB", date_index, window_days=1)
    cb_days = set(date_index[(fomc_dummy == 1) | (ecb_dummy == 1)])
    t_nocb = trades[~trades["date_ts"].isin(cb_days)]
    rows.append(stats(t_nocb, "ohne FOMC/EZB-Fenster (+/-1 Tag)"))
    t_onlycb = trades[trades["date_ts"].isin(cb_days)]
    rows.append(stats(t_onlycb, "NUR FOMC/EZB-Fenster (Gegenprobe)"))

    # --- 4) FX-Liquiditaets-Proxy, schlechteste 20% ausgeschlossen ---
    friction = fetch_fx_friction("EURUSD", (pd.Timestamp(START) - pd.Timedelta(days=20)).date().isoformat(), SPLIT)
    friction_known = friction.shift(2)  # Schaetzer selbst braucht [t,t+1] -> +2 Tage Puffer
    friction_daily = friction_known.reindex(pd.date_range(friction_known.index.min(), pd.Timestamp(SPLIT), freq="D")).ffill()
    threshold = friction_daily.quantile(0.80)
    illiquid_days = set(friction_daily[friction_daily > threshold].index.normalize())
    t_noilliquid = trades[~trades["date_ts"].isin(illiquid_days)]
    rows.append(stats(t_noilliquid, "ohne schlechteste 20% Liquiditaets-Tage"))

    # --- 5) Asia-Range-Breite, oberste/unterste 20% ausgeschlossen ---
    daily = compute_daily_features(eurusd_m5)
    range_width = (daily["asia_high"] - daily["asia_low"])
    q20, q80 = range_width.quantile(0.20), range_width.quantile(0.80)
    normal_range_days = set(pd.DatetimeIndex(range_width[(range_width >= q20) & (range_width <= q80)].index))
    t_normalrange = trades[trades["date_ts"].isin(normal_range_days)]
    rows.append(stats(t_normalrange, "nur mittlere 60% Asia-Range-Breite"))

    out_path = Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "external_filters_in_sample.csv"
    pd.DataFrame(rows).to_csv(out_path, index=False)
    print(f"\nSaved {out_path}")


if __name__ == "__main__":
    main()
