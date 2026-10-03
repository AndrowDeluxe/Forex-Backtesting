"""Reversal-Signal schon an der SIGNALBAR handelbar machen (2026-10-03).

Warum: `simulate_trades_concurrent()` laeuft nur bis `n-1` -- ein Trade
entsteht erst, wenn die FUELL-Bar (Signalbar+1) existiert. Der Lake fuehrt
nur geschlossene Bars, also taucht ein ctnl_reversal-Signal in der
Trade-Liste von Funded/FK erst auf, wenn die Fuell-Bar GESCHLOSSEN und
ingestet ist: eine M15-Bar spaeter als noetig. Gemessen an allen echten
Fills seit 2026-09-17: Funded/FK 28 Min. nach dem Backtest-Fill (open der
Bar Signalbar+1), EK 14 Min. -- EK liest das Signal direkt von der
Signalbar (live_signal.reversal_signal). Beispiel 2026-10-02: Signalbar
12:30 UTC, EK 12:59, Funded/FK 13:13.

Was: haengt fuer ein Signal auf der zuletzt GESCHLOSSENEN Bar genau die
Zeile an, die die Simulation beim naechsten Scan selbst erzeugen wird --
gleiche entry_time (= Signalbar+1, also derselbe State-Schluessel in den
Bridges), gleiche Richtung, exit_reason "data_end". Sobald die Fuell-Bar
im Lake liegt, liefert die Simulation die echte Zeile mit demselben
Schluessel und die Bridge sieht "bereits getrackt" -- keine Doppelorder.

Abweichungen der vorlaeufigen Zeile, bewusst:
  - entry_price = Schlusskurs der Signalbar (+ halbe Kosten) statt open der
    Fuell-Bar -- die Bridges fuellen ohnehin zum Live-Kurs.
  - Stop mit der ATR der Signalbar statt der Fuell-Bar (die gibt es noch
    nicht). Exakt EKs Rechnung (live_signal.reversal_signal()).
  - r_multiple 0.0 -- der Trade hat noch keinen Verlauf; der
    CTNL-Kill-Switch zaehlt ihn damit neutral.

Nur wenn die Fuell-Bar real kommen wird: liegt Signalbar+1 in der
taeglichen Handelspause (17:00-18:00 New York) oder im Wochenende, haette
die Simulation spaeter eine ANDERE entry_time und damit einen anderen
Schluessel -> Doppelorder-Gefahr. Dort wird nichts angehaengt, das Signal
kommt dann wie bisher ueber die Simulation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

BAR = pd.Timedelta(minutes=15)


def _utc_naive(ts: pd.Timestamp) -> pd.Timestamp:
    ts = pd.Timestamp(ts)
    return ts.tz_convert(None) if ts.tzinfo is not None else ts


def _fuell_bar_kommt(fill_label: pd.Timestamp) -> bool:
    """Wird es eine Bar mit diesem Label geben (Gold: So 18:00 - Fr 17:00 NY,
    taegliche Pause 17:00-18:00)?"""
    ts = pd.Timestamp(fill_label)
    ny = (ts if ts.tzinfo is not None else ts.tz_localize("UTC")).tz_convert("America/New_York")
    wd, h = ny.dayofweek, ny.hour
    if h == 17 or wd == 5:
        return False
    if wd == 4 and h >= 17:
        return False
    if wd == 6 and h < 18:
        return False
    return True


def append(trades: pd.DataFrame, sig: pd.DataFrame, cfg, now: pd.Timestamp) -> pd.DataFrame:
    """`sig` = Ausgabe von reversal_cascade.run_pipeline, bereits auf <= now
    gefiltert; `cfg` = dieselbe BacktestConfig wie fuer die Simulation;
    `now` = Scan-Zeitpunkt (beliebige Zeitzone, intern UTC-naiv)."""
    if sig is None or sig.empty:
        return trades
    last = sig.iloc[-1]
    direction = int(last["signal"])
    atr = float(last["atr"])
    if direction == 0 or np.isnan(atr) or atr < cfg.min_atr:
        return trades

    signal_label = sig.index[-1]
    fill_label = signal_label + BAR
    seit_schluss = _utc_naive(now) - _utc_naive(fill_label)
    # Bar muss GESCHLOSSEN sein (Live-Fallback kann eine laufende Bar
    # liefern). Dass die Fuell-Bar noch fehlt, ist schon dadurch garantiert,
    # dass die Signalbar die letzte Zeile ist. Obergrenze 2 Bars: so lange
    # braucht die Fuell-Bar real bis in den Lake (Schluss +15, Ingest ~+10);
    # bei 15 Min. verschwand die Zeile auf FKs 5-Min-Lane kurz. Haengt der
    # Lake laenger, greifen Alters- und Restlaufzeit-Gate der Bridges.
    if seit_schluss < pd.Timedelta(0) or seit_schluss >= 2 * BAR:
        return trades
    if not _fuell_bar_kommt(fill_label):
        return trades
    if not trades.empty:
        vorhanden = pd.to_datetime(trades["entry_time"])
        vorhanden = vorhanden.dt.tz_convert(None) if vorhanden.dt.tz is not None else vorhanden
        if (vorhanden == _utc_naive(fill_label)).any():
            return trades

    half_cost = cfg.spread_bps / 10_000 / 2
    close = float(last["close"])
    entry_price = close + direction * close * half_cost
    trigger = float(last["low"]) if direction == 1 else float(last["high"])
    stop = trigger - direction * cfg.stop_atr_mult * atr
    initial_risk = abs(entry_price - stop)
    if initial_risk <= 0:
        return trades

    row = {
        "entry_time": fill_label, "exit_time": fill_label, "direction": direction,
        "entry_price": entry_price, "exit_price": entry_price, "return_pct": 0.0,
        "exit_reason": "data_end", "hold_bars": 0,
        "adx_at_entry": last["adx"] if "adx" in sig.columns else np.nan,
        "atr_at_entry": atr, "moved_to_be": False, "be_time": None,
        "mfe_r": 0.0, "mae_r": 0.0, "initial_risk": initial_risk, "r_multiple": 0.0,
        "signal_bar": len(sig) - 1, "signal_bar_entry": True,
    }
    neu = pd.DataFrame([row])
    if trades.empty:
        return neu
    return pd.concat([trades, neu], ignore_index=True)
