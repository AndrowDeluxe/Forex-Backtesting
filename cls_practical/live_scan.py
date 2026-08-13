"""Live-Scan fuer cls_practical (Forward-Test-Vorbereitung, 2026-08-13) --
kein eigener Bot noch, nur ein Punkt-in-Zeit-Snapshot: laedt frische Daten
bis "jetzt" (kurzes Trailing-Fenster, nicht die volle 8-Jahre-Historie --
schnell genug fuer einen stuendlichen/taeglichen Scan), laesst
simulate_cls_practical() darueber laufen (exakt dieselbe Logik wie im
Backtest, keine Duplizierung der Entry/Exit-Regeln) und meldet:
- ist heute ein Continuation-/Reversal-/Kein-Signal-Tag (Tagesfilter-Status)?
- hat der Fractal/CHOCH-Trigger heute bereits gefuellt (falls ja: Entry/SL/TP)?

Trailing-Fenster 400 Kalendertage (gleiche Konvention wie
ou_paper_backtest/scanner.py) -- genug Vorlauf fuer SMA(100)/ADX(14)/ADR(14)-
Warmup, ohne die volle Historie neu laden zu muessen."""

import datetime as dt

import pandas as pd

from .data import fetch_eurusd_entry_tf_berlin, fetch_major_m15_berlin, fetch_rate_instrument_m5_berlin
from .engine import simulate_cls_practical
from strategy.cls_advanced import PAIRS, compute_cross_confirmation, compute_daily_features, to_berlin

OTHER_MAJORS = [p for p in PAIRS if p != "EURUSD"]
LOOKBACK_DAYS = 400


def scan_today() -> dict:
    today = dt.date.today()
    start = (today - dt.timedelta(days=LOOKBACK_DAYS)).isoformat()
    end = today.isoformat()

    eurusd_m5 = fetch_eurusd_entry_tf_berlin("M5", start, end, force_refresh=True)
    other_majors_m15 = {p: fetch_major_m15_berlin(p, start, end, force_refresh=True) for p in OTHER_MAJORS}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", start, end, force_refresh=True)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", start, end, force_refresh=True)

    if eurusd_m5.empty:
        return {"date": today.isoformat(), "status": "keine Daten (Wochenende/Feiertag/Fehler)"}

    # 1) Tagesfilter-Status fuer heute (unabhaengig davon, ob schon ein Trigger
    # gefeuert hat) -- dieselben Bausteine wie die Funnel-Diagnose.
    daily = compute_daily_features(eurusd_m5)
    daily_by_pair = {"EURUSD": daily}
    for pair, df in other_majors_m15.items():
        if not df.empty:
            daily_by_pair[pair] = compute_daily_features(df)
    cross_confirm = compute_cross_confirmation(daily_by_pair)["EURUSD"]

    berlin_today = pd.Timestamp(today)
    if berlin_today.date() not in daily.index:
        row = {"date": today.isoformat(), "status": "heute noch keine vollstaendige Settle-Range (vor 09:00 Berlin?)"}
    else:
        d = daily.loc[berlin_today.date()]
        direction = d["direction"]
        holds = d["holds_0915"]
        c_val = cross_confirm.get(berlin_today.date(), None)
        row = {
            "date": today.isoformat(),
            "break_direction": {1: "long", -1: "short", 0: "kein Break"}.get(direction, "n/a"),
            "holds_0915": bool(holds) if pd.notna(holds) else None,
            "cross_confirmed": bool(c_val) if c_val is not None else None,
        }

    # 2) Tatsaechlicher Trigger heute? -- simulate_cls_practical() auf dem
    # Trailing-Fenster laufen lassen (identische Regeln wie Backtest), dann
    # prüfen ob ein Trade HEUTE entered hat.
    trades = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5)
    if not trades.empty:
        today_trades = trades[trades["entry_time"].dt.date == today]
    else:
        today_trades = trades

    if len(today_trades) > 0:
        t = today_trades.iloc[0]
        row.update({
            "triggered": True, "setup": t["setup"], "direction": t["direction"],
            "entry_time": str(t["entry_time"]), "entry_price": round(t["entry_price"], 5),
            "sl": round(t["sl"], 5), "tp": round(t["tp"], 5),
        })
    else:
        row["triggered"] = False

    return row
