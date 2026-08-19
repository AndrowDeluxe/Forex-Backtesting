"""G8/FX-Majors-Validierung des neuen Halte-Test-Checkpoints 09:00
(User-Entscheidung 2026-08-19: "nehmen wir 9:00 Uhr als neues Haltefenster",
danach "Machen wir weiter mit der G8 Validierung" - der zuvor zweimal
angekuendigte naechste Schritt: "Erstmal auf EU, danach auf Alle G8 Majors
testen!").

Testet ALT (Haltetest 09:15, der bisherige Live-Wert) gegen NEU (09:00, der
neue engine.py-Default seit heute) auf allen 6 in diesem Projekt als
"FX-Majors" gefuehrten Paaren (strategy.cls_advanced.PAIRS: EUR/USD, GBP/USD,
USD/JPY, USD/CHF, AUD/USD, USD/CAD - dieselben 6, die schon im urspruenglichen
Multi-Instrument-Test in app_pages/cls_practical_strategy.py aufgefuehrt
sind; das Projekt nutzt "G8 Majors" synonym fuer dieses 6er-Set, nicht
woertlich 8 Paare). Gold/S&P500/BTC bewusst NICHT hier - fuer die gilt die
CLS-Settlement-Hypothese ohnehin nur strukturell, nicht als Zeitfenster mit
oekonomischer Grundlage (siehe scripts/research_cls_practical_multi_instrument.py),
und sie waren nicht Teil des "G8 Majors"-Auftrags.

Uebernimmt denselben Bugfix wie research_cls_practical_multi_instrument.py:
engine.py labelt das Primaer-Paar intern immer als "EURUSD" (Parametername
eurusd_m5) und compute_cross_confirmation() liest dafuer
_USD_IS_QUOTE["EURUSD"] - fuer USD/JPY, USD/CHF, USD/CAD (USD = Basis, nicht
Quote) wird das nur fuer die Dauer jedes einzelnen Laufs auf den fuer dieses
Paar richtigen Wert umgesetzt, danach zurueckgesetzt.

Methodik wie ueberall: IS = 2018-12 bis 2022-06, OOS = 2022-06 bis 2026-08."""

import sys
from pathlib import Path

import dukascopy_python
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import strategy.cls_advanced as cls_advanced
from cls_practical.data import fetch_major_m15_berlin, fetch_rate_instrument_m5_berlin
from cls_practical.engine import simulate_cls_practical
from combined_strategy.data import INSTRUMENTS, OFFER_SIDE
from strategy.cls_advanced import PAIRS

START, END = "2018-12-01", "2026-08-11"
SPLIT = "2022-06-01"

CONFIGS = [("ALT (Haltetest 09:15)", 9.25), ("NEU (Haltetest 09:00)", 9.0)]


def fetch_m5_berlin_generic(key: str, start: str, end: str) -> pd.DataFrame:
    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    df = dukascopy_python.fetch(
        INSTRUMENTS[key], dukascopy_python.INTERVAL_MIN_5, OFFER_SIDE,
        start_ts.to_pydatetime(), end_ts.to_pydatetime(),
    )
    df = df.sort_index()
    df.index = df.index.tz_convert("Europe/Berlin")
    return df


def stats(trades: pd.DataFrame, pair: str, config_label: str) -> dict:
    n = len(trades)
    if n == 0:
        return {"pair": pair, "config": config_label, "n": 0}
    r = trades["pnl_usd"] / trades["risk_amount_usd"]
    win_rate = (trades["pnl_usd"] > 0).mean()
    gross_profit = trades.loc[trades["pnl_usd"] > 0, "pnl_usd"].sum()
    gross_loss = -trades.loc[trades["pnl_usd"] < 0, "pnl_usd"].sum()
    pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    is_mask = trades["entry_time"].dt.tz_localize(None) < SPLIT
    is_r, oos_r = r[is_mask], r[~is_mask]
    return {
        "pair": pair, "config": config_label, "n": n, "win_rate": win_rate * 100, "avg_r": r.mean(),
        "profit_factor": pf, "total_pnl": trades["pnl_usd"].sum(),
        "n_is": int(is_mask.sum()), "avg_r_is": is_r.mean() if len(is_r) else float("nan"),
        "n_oos": int((~is_mask).sum()), "avg_r_oos": oos_r.mean() if len(oos_r) else float("nan"),
    }


def main():
    print("Lade Rates + Majors M15 (fuer Cross-Confirmation)...")
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)
    majors_m15 = {p: fetch_major_m15_berlin(p, START, END) for p in PAIRS}

    rows = []
    for primary in PAIRS:
        print(f"\n{'='*100}\n{primary}\n{'='*100}")
        print(f"Lade {primary} M5...")
        primary_m5 = fetch_m5_berlin_generic(primary, START, END)
        other_majors = {p: df for p, df in majors_m15.items() if p != primary}

        cls_advanced._USD_IS_QUOTE["EURUSD"] = cls_advanced._USD_IS_QUOTE[primary]
        try:
            for cfg_label, test_hour in CONFIGS:
                trades = simulate_cls_practical(primary_m5, other_majors, bund_m5, ustbond_m5, test_hour=test_hour)
                st = stats(trades, primary, cfg_label)
                rows.append(st)
                if st["n"] == 0:
                    print(f"  {cfg_label:24s}: keine Trades")
                else:
                    print(f"  {cfg_label:24s}: n={st['n']:>3d} WR={st['win_rate']:5.1f}% avg_R={st['avg_r']:+.3f} "
                          f"PF={st['profit_factor']:.2f} PnL=${st['total_pnl']:+,.0f} | "
                          f"IS(n={st['n_is']:>3d}) avg_R={st['avg_r_is']:+.3f} | "
                          f"OOS(n={st['n_oos']:>3d}) avg_R={st['avg_r_oos']:+.3f}")
        finally:
            cls_advanced._USD_IS_QUOTE["EURUSD"] = True

    df = pd.DataFrame(rows)
    out_path = Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "g8_majors_point0900_verification.csv"
    df.to_csv(out_path, index=False)
    print(f"\nGespeichert: {out_path}")

    print("\n" + "=" * 100 + "\nZUSAMMENFASSUNG: ALT (09:15) vs. NEU (09:00) je Paar\n" + "=" * 100)
    for pair in PAIRS:
        sub = df[df["pair"] == pair]
        alt = sub[sub["config"].str.startswith("ALT")].iloc[0]
        neu = sub[sub["config"].str.startswith("NEU")].iloc[0]
        better_is = neu["avg_r_is"] > alt["avg_r_is"]
        better_oos = neu["avg_r_oos"] > alt["avg_r_oos"]
        flag = "BEIDE besser" if (better_is and better_oos) else ("gemischt" if (better_is or better_oos) else "BEIDE schlechter")
        print(f"  {pair}: avg_R  ALT={alt['avg_r']:+.3f} (IS={alt['avg_r_is']:+.3f}/OOS={alt['avg_r_oos']:+.3f})  "
              f"-> NEU={neu['avg_r']:+.3f} (IS={neu['avg_r_is']:+.3f}/OOS={neu['avg_r_oos']:+.3f})  [{flag}]")


if __name__ == "__main__":
    main()
