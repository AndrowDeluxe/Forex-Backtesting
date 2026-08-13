"""CLS practical auf weiteren Instrumenten getestet (User-Anfrage 2026-08-13):
die 6 FX-Majors (jeweils als Primaer-Paar, Cross-Confirmation gegen die
jeweils anderen 5 -- exakt dieselbe Mechanik wie bei EUR/USD), sowie Gold,
S&P 500 und BTC.

BUGFIX 2026-08-14 (User-Anfrage: GBP/USD-Ergebnis nochmal sauber nachrechnen):
engine.py labelt das Primaer-Paar intern IMMER als "EURUSD" im
daily_by_pair-Dict (der Parametername ist eurusd_m5, unabhaengig davon, was
tatsaechlich uebergeben wird) und compute_cross_confirmation() liest dafuer
_USD_IS_QUOTE["EURUSD"] (=True, USD ist Quote-Waehrung). Fuer GBP/USD und
AUD/USD (ebenfalls USD-als-Quote) ist das zufaellig richtig -- fuer USD/JPY,
USD/CHF, USD/CAD (USD ist dort die BASIS-Waehrung, _USD_IS_QUOTE=False) kippt
dadurch das Vorzeichen der eigenen "USD-Staerke" in der Cross-Confirmation-
Berechnung. engine.py selbst bleibt unveraendert (das waere ein Eingriff in
den validierten Live-Pfad fuer einen Bug, der nur dieses Mehrinstrumenten-
Diagnose-Skript betrifft) -- stattdessen wird _USD_IS_QUOTE["EURUSD"] hier,
NUR fuer die Dauer jedes einzelnen Primaer-Paar-Laufs, per Monkeypatch auf den
tatsaechlich richtigen Wert fuer dieses Paar gesetzt (siehe
_run_fx_major_with_correct_quote_convention()) und danach wieder
zurueckgesetzt. GBP/USD selbst war NICHT betroffen (schon vorher korrekt),
nur USD/JPY, USD/CHF, USD/CAD aendern sich durch diesen Fix.

WICHTIGE EINSCHRAENKUNG (disclosed, nicht stillschweigend uebernommen): fuer
Gold/S&P/BTC ergibt der Cross-Confirmation-Filter (EUR/USD vs. die anderen 5
FX-Majors, "breiter Dollar-Move vs. isolierter Move") konzeptionell keinen
Sinn -- es gibt kein aequivalentes "die anderen 5"-Set. Fuer diese drei laeuft
die Strategie nur mit Trend+ADX (use_cross_filter=False), sonst identische
Konfiguration (Rates aus, min_adx=15, adr_mult=0.35, entry_cutoff=12:00, M5).
Das ist eine strukturelle Vereinfachung, kein Bug -- explizit hier
dokumentiert. Ausserdem gilt die eigentliche CLS-Settlement-Hypothese
(warum die Zeitfenster 06:00-09:00 Berlin ueberhaupt relevant sein sollten)
nur fuer FX -- fuer Gold/S&P/BTC wird hier lediglich die STRUKTURELLE
Mechanik (Range/Break/Retest/Fractal, Trend+ADX-Filter) uebertragen, ohne
den urspruenglichen oekonomischen Grund.

BTC: Binance-Daten (auction_playbook/data.py::fetch_klines), 24/7 Handel --
keine Wochenend-Luecke wie bei FX, aber die Zeitfenster-Logik (00-06/06-09/
09:15/09:30-12:00 Berlin) wird unveraendert angewendet."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import dukascopy_python
import pandas as pd

import strategy.cls_advanced as cls_advanced
from auction_playbook.data import fetch_klines
from cls_practical.data import fetch_major_m15_berlin, fetch_rate_instrument_m5_berlin
from cls_practical.engine import simulate_cls_practical
from combined_strategy.data import INSTRUMENTS, OFFER_SIDE
from strategy.cls_advanced import PAIRS

START, END = "2018-12-01", "2026-08-11"
SPLIT = "2022-06-01"


def fetch_m5_berlin_generic(key: str, start: str, end: str) -> pd.DataFrame:
    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    df = dukascopy_python.fetch(
        INSTRUMENTS[key], dukascopy_python.INTERVAL_MIN_5, OFFER_SIDE,
        start_ts.to_pydatetime(), end_ts.to_pydatetime(),
    )
    df = df.sort_index()
    df.index = df.index.tz_convert("Europe/Berlin")
    return df


def fetch_btc_m5_berlin(start: str, end: str) -> pd.DataFrame:
    df = fetch_klines("BTCUSDT", "5m", start, end)
    idx = df.index if df.index.tz is not None else df.index.tz_localize("UTC")
    df.index = idx.tz_convert("Europe/Berlin")
    return df[["open", "high", "low", "close"]]


def stats(trades: pd.DataFrame, label: str) -> dict:
    n = len(trades)
    if n == 0:
        print(f"  {label}: keine Trades")
        return {"label": label, "n_trades": 0}
    r = trades["pnl_usd"] / trades["risk_amount_usd"]
    wins = r[r > 0]
    is_r = trades.loc[trades["entry_time"] < SPLIT, "pnl_usd"] / trades.loc[trades["entry_time"] < SPLIT, "risk_amount_usd"]
    oos_r = trades.loc[trades["entry_time"] >= SPLIT, "pnl_usd"] / trades.loc[trades["entry_time"] >= SPLIT, "risk_amount_usd"]
    row = {
        "label": label, "n_trades": n, "win_rate": len(wins) / n, "avg_r": r.mean(), "total_r": r.sum(),
        "n_is": len(is_r), "avg_r_is": is_r.mean() if len(is_r) else float("nan"),
        "n_oos": len(oos_r), "avg_r_oos": oos_r.mean() if len(oos_r) else float("nan"),
    }
    print(f"  {label}: n={n} WR={row['win_rate']*100:.1f}% avg_R={row['avg_r']:+.3f} total_R={row['total_r']:+.2f} "
          f"| IS(n={row['n_is']}) avg_R={row['avg_r_is']:+.3f} | OOS(n={row['n_oos']}) avg_R={row['avg_r_oos']:+.3f}")
    return row


def main():
    print("Lade Rates (gemeinsam fuer alle Instrumente) + Majors M15 (fuer Cross-Confirmation)...")
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)
    majors_m15 = {p: fetch_major_m15_berlin(p, START, END) for p in PAIRS}

    rows = []

    print("\n=== 6 FX-Majors (voller CLS-Mechanismus, Cross-Confirmation aktiv) ===")
    for primary in PAIRS:
        print(f"Lade {primary} M5...")
        primary_m5 = fetch_m5_berlin_generic(primary, START, END)
        other_majors = {p: df for p, df in majors_m15.items() if p != primary}

        # Bugfix 2026-08-14 (siehe Modul-Docstring): engine.py labelt das
        # Primaer-Paar intern immer als "EURUSD" und liest dafuer
        # _USD_IS_QUOTE["EURUSD"] -- nur fuer die Dauer dieses einen Laufs auf
        # den fuer `primary` tatsaechlich richtigen Wert setzen, danach
        # zurueck auf den echten EUR/USD-Wert (True).
        cls_advanced._USD_IS_QUOTE["EURUSD"] = cls_advanced._USD_IS_QUOTE[primary]
        try:
            trades = simulate_cls_practical(primary_m5, other_majors, bund_m5, ustbond_m5)
        finally:
            cls_advanced._USD_IS_QUOTE["EURUSD"] = True

        rows.append({**stats(trades, primary), "group": "fx_major"})

    print("\n=== Gold / S&P 500 / BTC (Trend+ADX, kein Cross-Filter) ===")
    for key, fetcher in (("GOLD", lambda: fetch_m5_berlin_generic("GOLD", START, END)),
                          ("SP500", lambda: fetch_m5_berlin_generic("SP500", START, END)),
                          ("BTC", lambda: fetch_btc_m5_berlin(START, END))):
        print(f"Lade {key} M5...")
        primary_m5 = fetcher()
        print(f"  {len(primary_m5)} Bars.")
        trades = simulate_cls_practical(primary_m5, {}, bund_m5, ustbond_m5, use_cross_filter=False)
        rows.append({**stats(trades, key), "group": "other"})

    out_path = Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "multi_instrument.csv"
    pd.DataFrame(rows).to_csv(out_path, index=False)
    print(f"\nSaved {out_path}")


if __name__ == "__main__":
    main()
