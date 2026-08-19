"""Re-Test der zuvor ausgeschlossenen/nie getesteten Instrumente (User-Anfrage
2026-08-18: Mentor bestaetigt "stabile und logische Trades" in USD/CAD,
AUD/USD, EUR/JPY und Gold) mit zwei neuen Bausteinen:

1. Paar-spezifische Cross-Confirmation (cls_practical/currency_strength.py)
   statt der alten, rein USD-zentrischen compute_cross_confirmation - noetig
   ueberhaupt fuer EUR/JPY (kein USD-Bein). User-Entscheidung 2026-08-18:
   paar-spezifischer Referenz-Korb statt fixem 4er-Korb.
2. Realistische Spread-Kosten je Paar aus Hasbrouck & Levich (2019, SSRN
   2912976), Tabelle 5, 2016-Spalte (juengste verfuegbare CLS-Settlement-
   Studie) statt des pauschalen 0.3bp-Engine-Defaults. Gold ist FX-only im
   Paper nicht abgedeckt - hier der bereits im Repo etablierte 10bp-Retail-
   CFD-Wert (mt5_trend_pullback/app_pages -- MARKETS-Liste), disclosed als
   grobe, nicht papier-hergeleitete Annahme.

Fuer jedes Paar: ALT (wie im fruehreren Multi-Instrument-Test, Default-
Spread 0.3bp, alte/keine Cross-Confirmation) vs. NEU (realer Spread +
paar-spezifische Confirmation + gestufte/kontinuierliche Risiko-Skalierung),
jeweils mit echten Trades/R-Multiples aus der validierten Engine
(cls_practical/engine.py::simulate_cls_practical), IS/OOS wie ueberall sonst
in diesem Projekt (Split 2022-06-01)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import strategy.cls_advanced as cls_advanced
from combined_strategy.data import fetch_timeframe
from cls_practical.currency_strength import compute_pair_specific_confirmation, risk_multiplier as make_risk_multiplier
from cls_practical.data import fetch_rate_instrument_m5_berlin
from cls_practical.engine import simulate_cls_practical
from strategy.cls_advanced import compute_cross_confirmation, compute_daily_features

START, END = "2018-12-01", "2026-08-11"
SPLIT = "2022-06-01"
SPLIT_DATE = pd.Timestamp(SPLIT).date()

# Hasbrouck & Levich (2019), Table 5, "Relative Spread x 10^4 (bp)", 2016-Spalte.
PAPER_SPREAD_BPS_2016 = {
    "EURJPY": 0.732, "USDCAD": 0.854, "AUDUSD": 0.925,
}
GOLD_SPREAD_BPS = 10.0  # bestehende Repo-Konvention (mt5_trend_pullback), nicht aus dem Paper

REF_BASKETS = {
    "EURJPY": ["EURUSD", "EURGBP", "EURCHF", "EURCAD", "EURAUD",
               "USDJPY", "GBPJPY", "CHFJPY", "CADJPY", "AUDJPY"],
    "USDCAD": ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD",
               "EURCAD", "CADJPY", "GBPCAD", "AUDCAD", "CADCHF"],
    "AUDUSD": ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD",
               "EURAUD", "AUDJPY", "GBPAUD", "AUDCAD", "AUDCHF"],
}


def fetch_m5_berlin(key: str) -> pd.DataFrame:
    df = fetch_timeframe(key, "M5", START, END)
    df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    df.index = df.index.tz_convert("Europe/Berlin")
    return df


def fetch_m15_berlin(key: str) -> pd.DataFrame:
    df = fetch_timeframe(key, "M15", START, END)
    df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    df.index = df.index.tz_convert("Europe/Berlin")
    return df


def stats(trades: pd.DataFrame, label: str) -> dict:
    n = len(trades)
    if n == 0:
        print(f"    {label}: keine Trades")
        return {"label": label, "n": 0}
    r = trades["pnl_usd"] / trades["risk_amount_usd"]
    is_mask = trades["entry_time"].dt.tz_localize(None) < SPLIT
    is_r, oos_r = r[is_mask], r[~is_mask]
    row = {
        "label": label, "n": n, "win_rate": (r > 0).mean(), "avg_r": r.mean(), "total_r": r.sum(),
        "n_is": is_mask.sum(), "avg_r_is": is_r.mean() if len(is_r) else float("nan"),
        "n_oos": (~is_mask).sum(), "avg_r_oos": oos_r.mean() if len(oos_r) else float("nan"),
        "total_pnl": trades["pnl_usd"].sum(),
    }
    print(f"    {label}: n={n} WR={row['win_rate']*100:.1f}% avg_R={row['avg_r']:+.3f} "
          f"total_R={row['total_r']:+.2f} PnL=${row['total_pnl']:+,.0f} | "
          f"IS(n={row['n_is']}) avg_R={row['avg_r_is']:+.3f} | OOS(n={row['n_oos']}) avg_R={row['avg_r_oos']:+.3f}")
    return row


def run_fx_pair(primary: str) -> list[dict]:
    print(f"\n{'='*78}\n{primary}\n{'='*78}")
    print("Lade Daten...")
    primary_m5 = fetch_m5_berlin(primary)
    six_majors_m15 = {p: fetch_m15_berlin(p) for p in cls_advanced.PAIRS if p != primary}
    ref_m15 = {p: fetch_m15_berlin(p) for p in REF_BASKETS[primary]}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)

    rows = []

    # --- ALT: wie im fruehreren Multi-Instrument-Test (Default-Spread 0.3bp,
    # alte USD-zentrische Cross-Confirmation via Monkeypatch, falls primary
    # ueberhaupt ein USD-Bein hat -- EUR/JPY hat keins, daher dort schlicht
    # OHNE Cross-Filter, was der urspruengliche Test so auch nicht anders
    # haette machen koennen). ---
    if primary in cls_advanced.PAIRS:
        cls_advanced._USD_IS_QUOTE["EURUSD"] = cls_advanced._USD_IS_QUOTE[primary]
        try:
            old_trades = simulate_cls_practical(primary_m5, six_majors_m15, bund_m5, ustbond_m5)
        finally:
            cls_advanced._USD_IS_QUOTE["EURUSD"] = True
    else:
        old_trades = simulate_cls_practical(primary_m5, {}, bund_m5, ustbond_m5, use_cross_filter=False)
    rows.append({**stats(old_trades, f"{primary} ALT (0.3bp, alte/keine Confirmation)"), "pair": primary, "variant": "alt"})

    # --- NEU: paar-spezifische Confirmation + realistischer Spread + Risiko-Skalierung ---
    primary_daily = compute_daily_features(primary_m5)
    ref_daily = {p: compute_daily_features(df) for p, df in ref_m15.items()}
    conf = compute_pair_specific_confirmation(primary, primary_daily, ref_daily)

    gap_scale_is = conf.loc[conf.index.map(lambda d: d < SPLIT_DATE), "strength_gap"].abs().median()
    mult = make_risk_multiplier(conf, gap_scale=gap_scale_is)

    new_trades = simulate_cls_practical(
        primary_m5, six_majors_m15, bund_m5, ustbond_m5,
        spread_bps=PAPER_SPREAD_BPS_2016[primary],
        cross_confirm_override=conf["confirmed"],
        risk_multiplier=mult,
    )
    rows.append({**stats(new_trades, f"{primary} NEU (paper-spread + paar-spezifisch + Risiko-Skalierung)"),
                 "pair": primary, "variant": "neu"})

    # --- NEU, aber ohne Risiko-Skalierung (isoliert: bringt die bessere
    # Confirmation allein schon was, unabhaengig vom Sizing-Layer?) ---
    new_trades_flat = simulate_cls_practical(
        primary_m5, six_majors_m15, bund_m5, ustbond_m5,
        spread_bps=PAPER_SPREAD_BPS_2016[primary],
        cross_confirm_override=conf["confirmed"],
    )
    rows.append({**stats(new_trades_flat, f"{primary} NEU ohne Risiko-Skalierung (nur Confirmation+Spread)"),
                 "pair": primary, "variant": "neu_flat"})

    return rows


def run_gold() -> list[dict]:
    print(f"\n{'='*78}\nGOLD (XAUUSD)\n{'='*78}")
    print("Lade Daten...")
    gold_m5 = fetch_m5_berlin("GOLD")
    six_majors_m15 = {p: fetch_m15_berlin(p) for p in cls_advanced.PAIRS}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)

    rows = []

    old_trades = simulate_cls_practical(gold_m5, {}, bund_m5, ustbond_m5, use_cross_filter=False)
    rows.append({**stats(old_trades, "GOLD ALT (0.3bp, kein Cross-Filter)"), "pair": "GOLD", "variant": "alt"})

    # NEU: Gold hat kein "Gegenwaehrungspaar"-Set wie eine echte FX-Kreuzung,
    # aber die urspruengliche USD-Staerke-Logik passt konzeptionell direkt
    # (Gold ist USD-quotiert, "long Gold" ist strukturell wie "long ein
    # XXX/USD-Paar") -- also die ALTE, bereits validierte USD-zentrische
    # compute_cross_confirmation nutzen, Gold wie ein 7. "USD-ist-Quote"-Paar
    # behandelt, plus realistischer 10bp-Spread statt des 0.3bp-FX-Defaults.
    gold_daily = compute_daily_features(gold_m5)
    daily_by_pair = {"GOLD": gold_daily, **{p: compute_daily_features(df) for p, df in six_majors_m15.items()}}
    cls_advanced._USD_IS_QUOTE["GOLD"] = True  # Gold steigt bei USD-Schwaeche, wie EUR/USD etc.
    try:
        gold_confirm = compute_cross_confirmation(daily_by_pair)["GOLD"]
    finally:
        del cls_advanced._USD_IS_QUOTE["GOLD"]

    new_trades = simulate_cls_practical(
        gold_m5, six_majors_m15, bund_m5, ustbond_m5,
        spread_bps=GOLD_SPREAD_BPS,
        cross_confirm_override=gold_confirm,
    )
    rows.append({**stats(new_trades, "GOLD NEU (10bp Spread + USD-Staerke-Confirmation)"), "pair": "GOLD", "variant": "neu"})

    return rows


def main():
    all_rows = []
    for pair in ["EURJPY", "USDCAD", "AUDUSD"]:
        all_rows.extend(run_fx_pair(pair))
    all_rows.extend(run_gold())

    out = pd.DataFrame(all_rows)
    out_path = Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "pair_specific_cross_retest.csv"
    out.to_csv(out_path, index=False)
    print(f"\nGespeichert: {out_path}")
    print("\n" + "="*78 + "\nZUSAMMENFASSUNG\n" + "="*78)
    print(out[["pair", "variant", "n", "win_rate", "avg_r", "avg_r_is", "avg_r_oos", "total_pnl"]].to_string(index=False))


if __name__ == "__main__":
    main()
