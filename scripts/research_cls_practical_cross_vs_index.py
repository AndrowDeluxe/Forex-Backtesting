"""Isolierter Vergleich der zwei getrennten Bestaetigungs-Mechanismen
(User-Anfrage 2026-08-18, nach dem negativen Ergebnis der ersten,
06:00-09:00-Fenster-basierten Version): Cross-Filter (gleichgewichtete
Mehrheitsabstimmung einzelner Kreuze) vs. Index-Filter (liquiditaets-
gewichteter Waehrungsindex), beide mit Trend SEIT TAGESBEGINN (00:00
Berlin) statt nur dem Settle-Fenster.

Kosten werden bewusst bei 0.3bp (Engine-Default) GEHALTEN, nicht auf den
Paper-Spread umgestellt - damit der Filter-Effekt sauber isoliert bleibt
und nicht wieder mit einer gleichzeitigen Kostenaenderung konfundiert
(genau der Kritikpunkt am ersten Testlauf,
scripts/research_cls_practical_pair_specific_cross.py). Die ALT-Baseline-
Zahlen (0.3bp, alte/keine Cross-Confirmation) stammen aus genau jenem
frueheren Lauf, hier nicht neu berechnet."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import strategy.cls_advanced as cls_advanced
from combined_strategy.data import fetch_timeframe
from cls_practical.currency_strength import compute_cross_vote_confirmation, compute_currency_index_confirmation
from cls_practical.data import fetch_rate_instrument_m5_berlin
from cls_practical.engine import simulate_cls_practical
from strategy.cls_advanced import compute_daily_features

START, END = "2018-12-01", "2026-08-11"
SPLIT = "2022-06-01"

REF_BASKETS = {
    "EURJPY": ["EURUSD", "EURGBP", "EURCHF", "EURCAD", "EURAUD",
               "USDJPY", "GBPJPY", "CHFJPY", "CADJPY", "AUDJPY"],
    "USDCAD": ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD",
               "EURCAD", "CADJPY", "GBPCAD", "AUDCAD", "CADCHF"],
    "AUDUSD": ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD",
               "EURAUD", "AUDJPY", "GBPAUD", "AUDCAD", "AUDCHF"],
    "XAUUSD": ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD"],  # nur USD-Seite existiert
}

ALT_BASELINE = {  # aus scripts/research_cls_practical_pair_specific_cross.py, 2026-08-18
    "EURJPY": {"n": 286, "avg_r": 0.031871, "avg_r_is": 0.075153, "avg_r_oos": -0.004709, "total_pnl": 4557.58},
    "USDCAD": {"n": 167, "avg_r": -0.132205, "avg_r_is": -0.376617, "avg_r_oos": 0.027511, "total_pnl": -11039.09},
    "AUDUSD": {"n": 124, "avg_r": 0.052239, "avg_r_is": 0.228278, "avg_r_oos": -0.092735, "total_pnl": 3238.79},
    "GOLD": {"n": 313, "avg_r": 0.019103, "avg_r_is": -0.009549, "avg_r_oos": 0.040834, "total_pnl": 2989.62},
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
        "label": label, "n": n, "avg_r": r.mean(), "n_is": is_mask.sum(),
        "avg_r_is": is_r.mean() if len(is_r) else float("nan"),
        "n_oos": (~is_mask).sum(), "avg_r_oos": oos_r.mean() if len(oos_r) else float("nan"),
        "total_pnl": trades["pnl_usd"].sum(),
    }
    print(f"    {label}: n={n} avg_R={row['avg_r']:+.3f} PnL=${row['total_pnl']:+,.0f} | "
          f"IS(n={row['n_is']}) avg_R={row['avg_r_is']:+.3f} | OOS(n={row['n_oos']}) avg_R={row['avg_r_oos']:+.3f}")
    return row


def run_pair(primary: str, gold: bool = False) -> list[dict]:
    label = "GOLD" if gold else primary
    print(f"\n{'='*78}\n{label}\n{'='*78}")
    print("Lade Daten...")

    primary_key = "GOLD" if gold else primary
    primary_m5 = fetch_m5_berlin(primary_key)
    ref_pairs = REF_BASKETS["XAUUSD" if gold else primary]
    ref_m15 = {p: fetch_m15_berlin(p) for p in ref_pairs}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)

    traded_pair_code = "XAUUSD" if gold else primary
    daily = compute_daily_features(primary_m5)
    direction = daily["direction"]

    cross_conf = compute_cross_vote_confirmation(traded_pair_code, direction, ref_m15)
    index_conf = compute_currency_index_confirmation(traded_pair_code, direction, ref_m15)

    print(f"  Cross-Filter:  confirmed an {cross_conf['confirmed'].mean()*100:.1f}% der Tage "
          f"(n_total median={cross_conf['n_total'].median():.0f})")
    print(f"  Index-Filter:  confirmed an {index_conf['confirmed'].mean()*100:.1f}% der Tage")

    # other_majors_m15 fuer die Engine (Trend/Rates-Layer selbst braucht die
    # alten 5 Majors nicht mehr, aber simulate_cls_practical() erwartet den
    # Parameter fuer sein eigenes internes daily_by_pair -- fuer primary in
    # PAIRS die anderen 5 Majors (M15, schon geladen wo vorhanden), fuer
    # Gold ein leeres Dict (use_cross_filter wird ueber cross_confirm_override
    # ohnehin ersetzt).
    if not gold:
        other_majors_m15 = {p: ref_m15[p] if p in ref_m15 else fetch_m15_berlin(p)
                             for p in cls_advanced.PAIRS if p != primary}
    else:
        other_majors_m15 = {}

    rows = []
    alt = ALT_BASELINE[label]
    print(f"    {label} ALT (bekannt, 0.3bp, alte/keine Confirmation): n={alt['n']} avg_R={alt['avg_r']:+.3f} "
          f"PnL=${alt['total_pnl']:+,.0f} | IS avg_R={alt['avg_r_is']:+.3f} | OOS avg_R={alt['avg_r_oos']:+.3f}")
    rows.append({**alt, "label": f"{label} ALT", "pair": label, "variant": "alt"})

    cross_trades = simulate_cls_practical(primary_m5, other_majors_m15, bund_m5, ustbond_m5,
                                           cross_confirm_override=cross_conf["confirmed"])
    rows.append({**stats(cross_trades, f"{label} CROSS-FILTER (0.3bp, Mehrheitsvotum seit Tagesbeginn)"),
                 "pair": label, "variant": "cross"})

    index_trades = simulate_cls_practical(primary_m5, other_majors_m15, bund_m5, ustbond_m5,
                                           cross_confirm_override=index_conf["confirmed"])
    rows.append({**stats(index_trades, f"{label} INDEX-FILTER (0.3bp, liquiditaetsgewichtet seit Tagesbeginn)"),
                 "pair": label, "variant": "index"})

    return rows


def main():
    all_rows = []
    for pair in ["EURJPY", "USDCAD", "AUDUSD"]:
        all_rows.extend(run_pair(pair))
    all_rows.extend(run_pair("GOLD", gold=True))

    out = pd.DataFrame(all_rows)
    out_path = Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "cross_vs_index.csv"
    out.to_csv(out_path, index=False)
    print(f"\nGespeichert: {out_path}")
    print("\n" + "="*78 + "\nZUSAMMENFASSUNG\n" + "="*78)
    print(out[["pair", "variant", "n", "avg_r", "avg_r_is", "avg_r_oos", "total_pnl"]].to_string(index=False))


if __name__ == "__main__":
    main()
